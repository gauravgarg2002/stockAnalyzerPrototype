"""Fund metadata adapter: AMFI NAVAll.txt (semicolon-separated with category and fund-house header lines).

From this file we can know: scheme code, ISINs, name, fund house (amc), category, plan type, the regular/direct
twin (matched by normalised name). Fields NAVAll.txt does not carry (launch date, AUM, expense ratio, exit load,
lock-in, benchmark, managers) are None and the engines show "not available". Importing performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: exact header-line wording; parse_navall is tested on inline text that mimics it.
"""
from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from .base import FundMeta
from .http_util import DEFAULT_TIMEOUT, DiskCache, make_session, today_ist, unavailable

SOURCE = "AMFI"
_CAT_RE = re.compile(r"^(?:Open|Close|Closed|Interval)\s*(?:Ended)?\s*Schemes?\s*\((.+)\)\s*$", re.I)
_PLAN_WORDS = re.compile(r"\b(direct|regular|plan|growth|option|idcw|dividend|payout|reinvestment|bonus|"
                         r"income distribution cum capital withdrawal|cum|capital|withdrawal|distribution|"
                         r"annual|monthly|weekly|daily|quarterly|half yearly|yearly|fortnightly)\b", re.I)


def _norm_key(name: str) -> str:
    s = _PLAN_WORDS.sub(" ", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _group(group_text: str, category: str) -> str:
    g = group_text.lower()
    if "debt" in g:
        return "DEBT"
    if "hybrid" in g:
        return "HYBRID"
    if any(w in category.lower() for w in ("gilt", "liquid", "bond", "overnight", "money market", "duration")):
        return "DEBT"
    return "EQUITY"


def parse_navall(text: str) -> list[dict]:
    """-> list of dicts {code, isin, isin2, name, amc, categoryGroupText, category, nav, navDate}."""
    rows: list[dict] = []
    amc = ""
    group_text = category = ""
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line or line.lower().startswith("scheme code"):
            continue
        if ";" not in line:
            m = _CAT_RE.match(line)
            if m:
                inner = m.group(1)
                if " - " in inner:
                    group_text, category = [x.strip() for x in inner.split(" - ", 1)]
                else:
                    group_text, category = inner.strip(), inner.strip()
            else:
                amc = line
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        isin = parts[1] if parts[1] not in ("", "-") else (parts[2] if parts[2] not in ("", "-") else None)
        rows.append({"code": parts[0], "isin": isin, "isin2": parts[2] if parts[2] not in ("", "-") else None,
                     "name": parts[3], "amc": amc, "groupText": group_text, "category": category,
                     "nav": parts[4], "navDate": parts[5]})
    return rows


def _is_growth(name: str) -> bool:
    n = name.lower()
    return not any(w in n for w in ("idcw", "dividend", "payout", "bonus"))


def build_index(rows: list[dict], as_of: str) -> dict[str, FundMeta]:
    metas: dict[str, FundMeta] = {}
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        name = r["name"]
        plan = "DIRECT" if "direct" in name.lower() else "REGULAR"
        cat = r["category"]
        lock = 3.0 if "elss" in (cat + " " + name).lower() or "tax saver" in name.lower() else None
        short = re.split(r"\s+-\s+", name)[0].strip()
        metas[r["code"]] = FundMeta(
            schemeCode=r["code"], isin=r["isin"], name=name, shortName=short, amc=r["amc"], category=cat,
            categoryGroup=_group(r["groupText"], cat), planType=plan, twinSchemeCode=None, launchDate=None,
            aumInr=None, aumInr1yAgo=None, terPct=None, terAsOf=None, exitLoad=None, lockInYears=lock,
            benchmarkId=None, managers=[], source=SOURCE, asOf=as_of)
        if _is_growth(name):
            by_key.setdefault((r["amc"], _norm_key(name)), {})[plan] = r["code"]
    for pair in by_key.values():
        if "DIRECT" in pair and "REGULAR" in pair:
            metas[pair["DIRECT"]].twinSchemeCode = pair["REGULAR"]
            metas[pair["REGULAR"]].twinSchemeCode = pair["DIRECT"]
    return metas


def search_metas(metas: dict[str, FundMeta], query: str, limit: int) -> list[FundMeta]:
    toks = [t for t in re.split(r"\W+", (query or "").lower()) if t]
    if not toks:
        return []
    hits = [m for m in metas.values() if _is_growth(m.name) and all(t in m.name.lower() for t in toks)]
    hits.sort(key=lambda m: (len(m.name), m.name))
    return hits[: max(0, int(limit))]


class AmfiFundMeta:
    mode = "amfi"

    def __init__(self, config: dict, session: requests.Session | None = None):
        self._url = str((config.get("amfi", {}) or {}).get("navAllUrl") or "https://www.amfiindia.com/spages/NAVAll.txt")
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._ttl_s = float(c.get("fundDataHours", 24)) * 3600
        self._cache = DiskCache(root / "amfi", float(c.get("fundDataHours", 24)))
        self._session = session or make_session()
        self._metas: dict[str, FundMeta] | None = None
        self._by_isin: dict[str, str] = {}
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def _load(self) -> dict[str, FundMeta]:
        with self._lock:
            if self._metas is not None and time.monotonic() - self._loaded_at < self._ttl_s:
                return self._metas
            text = self._cache.get("navall")
            if text is None:
                try:
                    r = self._session.get(self._url, timeout=(5.0, 60.0))
                except requests.RequestException as e:
                    if self._metas is not None:
                        return self._metas  # keep serving stale data
                    raise unavailable("Fund list could not be reached. Please try again in a moment.",
                                      reason=type(e).__name__)
                if r.status_code != 200:
                    if self._metas is not None:
                        return self._metas
                    raise unavailable("Fund list returned an error.", httpStatus=r.status_code)
                text = r.text
                if "Scheme Code" not in text[:5000]:
                    raise unavailable("Fund list was in an unexpected format.")
                self._cache.set("navall", text)
            rows = parse_navall(text)
            if not rows:
                raise unavailable("Fund list was in an unexpected format.")
            self._metas = build_index(rows, today_ist().isoformat())
            self._by_isin = {}
            for r in rows:
                for key in ("isin", "isin2"):
                    if r[key]:
                        self._by_isin.setdefault(r[key].upper(), r["code"])
            self._loaded_at = time.monotonic()
            return self._metas

    def get(self, scheme_code: str) -> Optional[FundMeta]:
        return self._load().get(str(scheme_code).strip())

    def find_by_isin(self, isin: str) -> Optional[FundMeta]:
        metas = self._load()
        code = self._by_isin.get((isin or "").strip().upper())
        return metas.get(code) if code else None

    def search(self, query: str, limit: int) -> list[FundMeta]:
        return search_metas(self._load(), query, limit)

    def category(self, category_name: str) -> Optional[dict]:
        return None  # category medians are not part of NAVAll.txt

    def all_codes(self) -> list[str]:
        return list(self._load().keys())


def build(config: dict, deps: dict) -> AmfiFundMeta:
    return AmfiFundMeta(config)
