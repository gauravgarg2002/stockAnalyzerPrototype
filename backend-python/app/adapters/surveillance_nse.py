"""Surveillance adapter: NSE ASM / GSM / ESM CSV files (download + parse), cached.

Importing performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: the column names of the published CSVs and the need for cookie warm-up.
parse_surveillance_csv is tolerant: it finds the header row (first row containing a "symbol" cell) and maps
columns by keyword; it is unit-tested on inline CSV text only.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from .base import SurveillanceEntry
from .http_util import DEFAULT_TIMEOUT, DiskCache, RateLimiter, make_session, unavailable

LISTS = (("ASM", "asmCsvUrl"), ("GSM", "gsmCsvUrl"), ("ESM", "esmCsvUrl"))
_DATE_FMTS = ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%b %d, %Y")


def _iso(s: str) -> str:
    t = (s or "").strip()
    for f in _DATE_FMTS:
        try:
            return datetime.strptime(t, f).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_surveillance_csv(text: str, list_name: str) -> list[SurveillanceEntry]:
    rows = list(csv.reader(io.StringIO((text or "").lstrip("﻿"))))
    hdr_i = next((i for i, r in enumerate(rows) if any(c.strip().lower() in ("symbol", "scrip symbol", "security symbol")
                                                       for c in r)), None)
    if hdr_i is None:
        return []
    hdr = [c.strip().lower() for c in rows[hdr_i]]

    def col(*keys: str, exclude: tuple[str, ...] = ()) -> int | None:
        for i, h in enumerate(hdr):
            if any(k in h for k in keys) and not any(x in h for x in exclude):
                return i
        return None

    c_sym = col("symbol")
    c_name = col("security name", "company name", "name", exclude=("symbol",))
    c_stage = col("stage", "framework", "indicator")
    c_since = col("since", "effective", "inclusion", "date", "w.e.f")
    if c_sym is None:
        return []
    out: list[SurveillanceEntry] = []
    seen: set[str] = set()
    for r in rows[hdr_i + 1:]:
        if len(r) <= c_sym or not r[c_sym].strip():
            continue
        sym = r[c_sym].strip().upper()
        if sym in seen:
            continue
        seen.add(sym)
        stage = r[c_stage].strip() if c_stage is not None and c_stage < len(r) else ""
        since = _iso(r[c_since]) if c_since is not None and c_since < len(r) else ""
        name = r[c_name].strip() if c_name is not None and c_name < len(r) else ""
        out.append(SurveillanceEntry(symbol=sym, list=list_name, stage=stage, since=since, name=name))
    return out


class NseSurveillance:
    mode = "nse"

    def __init__(self, config: dict, session: requests.Session | None = None, limiter: RateLimiter | None = None):
        n = config.get("nse", {}) or {}
        self._base = str(n.get("baseUrl") or "https://www.nseindia.com").rstrip("/")
        self._urls = {name: str(n.get(key) or "") for name, key in LISTS}
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "surveillance", float(c.get("surveillanceHours", 24)))
        self._limiter = limiter or RateLimiter(float(n.get("minIntervalSeconds", 2)))
        self._session = session or make_session(headers={"Referer": self._base + "/"})

    def _load(self, name: str) -> Optional[list[SurveillanceEntry]]:
        key = f"list:{name}"
        cached = self._cache.get(key)
        if cached is not None:
            return [SurveillanceEntry(**d) for d in cached]
        url = self._urls.get(name)
        if not url:
            return None
        self._limiter.wait()
        try:
            r = self._session.get(url, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException:
            return None
        if r.status_code != 200:
            return None
        entries = parse_surveillance_csv(r.text, name)
        self._cache.set(key, [e.__dict__ for e in entries])
        return entries

    def lookup(self, symbol: str) -> Optional[list[SurveillanceEntry]]:
        sym = (symbol or "").strip().upper()
        found: list[SurveillanceEntry] = []
        failed = False
        for name, _ in LISTS:
            entries = self._load(name)
            if entries is None:
                failed = True
                continue
            found.extend(e for e in entries if e.symbol == sym)
        if found:
            return found
        return None if failed else []


def build(config: dict, deps: dict) -> NseSurveillance:
    return NseSurveillance(config)
