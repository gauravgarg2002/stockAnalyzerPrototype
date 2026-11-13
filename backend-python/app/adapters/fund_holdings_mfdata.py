"""Fund portfolio holdings adapter: MFData.in (base URL from config) with fallback to the bundled starter set.

Importing performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: endpoint path (GET {base}/schemes/{code}/holdings) and response field names are
assumptions isolated in parse_mfdata_holdings. When the live call fails or returns nothing, the bundled starter
set (app/data/sample/funds.json, source label "Sample data") is used if it knows the scheme; otherwise None.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import requests

from .base import FundPortfolio
from .http_util import DEFAULT_TIMEOUT, DiskCache, make_session

SOURCE = "Fund factsheet"
SAMPLE_FUNDS = Path(__file__).resolve().parents[1] / "data" / "sample" / "funds.json"


def _f(v: Any) -> float | None:
    try:
        return None if v is None else float(str(v).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def parse_mfdata_holdings(obj: Any, scheme_code: str) -> Optional[FundPortfolio]:
    """UNVERIFIED AGAINST LIVE SERVICE. Expected:
    {"data": {"as_of": "2026-09-30", "holdings": [{"name", "isin", "symbol", "sector", "weight"|"percentage"}],
              "asset_allocation": {"equity": 96.5, "debt": 0, "cash": 3.5, "other": 0}}}
    Only equity constituents (those with an INE-prefixed ISIN or a symbol) are kept as holdings."""
    d = obj.get("data") if isinstance(obj, dict) and isinstance(obj.get("data"), dict) else obj
    if not isinstance(d, dict):
        return None
    rows = d.get("holdings") or d.get("portfolio") or []
    holdings = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        w = _f(r.get("weight") if r.get("weight") is not None else r.get("percentage", r.get("pct_nav")))
        isin = (r.get("isin") or "") or None
        if w is None or w <= 0 or not (r.get("symbol") or (isin and str(isin).upper().startswith("INE"))):
            continue
        holdings.append({"symbol": (r.get("symbol") or None) and str(r["symbol"]).upper(), "isin": isin,
                         "name": str(r.get("name") or r.get("company") or ""), "sector": str(r.get("sector") or "") or None,
                         "sizeBand": None, "weightPct": round(w, 2)})
    if not holdings:
        return None
    aa = d.get("asset_allocation") or {}
    eq = _f(aa.get("equity"))
    debt, cash, other = _f(aa.get("debt")) or 0.0, _f(aa.get("cash")) or 0.0, _f(aa.get("other")) or 0.0
    total_w = round(sum(h["weightPct"] for h in holdings), 2)
    if eq is None:
        eq = total_w
    other = round(max(0.0, 100.0 - eq - debt - cash), 2) if not aa else other
    mix = {"equityPct": eq, "debtPct": debt, "cashPct": cash, "otherPct": other}
    as_of = str(d.get("as_of") or d.get("date") or "")[:10]
    return FundPortfolio(schemeCode=scheme_code, portfolioDate=as_of, assetMix=mix, holdings=holdings,
                         previousTop10=[], events=[], source=SOURCE)


def load_starter(scheme_code: str, path: Path = SAMPLE_FUNDS) -> Optional[FundPortfolio]:
    try:
        funds = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for f in funds if isinstance(funds, list) else []:
        if str(f.get("schemeCode")) == scheme_code:
            return FundPortfolio(
                schemeCode=scheme_code, portfolioDate=f.get("portfolioDate", ""), assetMix=f["assetMix"],
                holdings=f.get("holdings", []), previousTop10=f.get("previousTop10", []),
                events=f.get("events", []), source="Sample data")
    return None


class MfdataHoldings:
    mode = "mfdata"

    def __init__(self, config: dict, session: requests.Session | None = None):
        self._base = str((config.get("mfdata", {}) or {}).get("baseUrl") or "https://mfdata.in/api/v1").rstrip("/")
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "mfdata", float(c.get("fundDataHours", 24)))
        self._session = session or make_session()

    def _live(self, code: str) -> Optional[FundPortfolio]:
        cached = self._cache.get(f"hold:{code}")
        if cached is not None:
            return FundPortfolio(**cached)
        try:
            r = self._session.get(f"{self._base}/schemes/{code}/holdings", timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                return None
            fp = parse_mfdata_holdings(r.json(), code)
        except (requests.RequestException, ValueError):
            return None
        if fp is not None:
            self._cache.set(f"hold:{code}", fp.__dict__)
        return fp

    def portfolio(self, scheme_code: str) -> Optional[FundPortfolio]:
        code = str(scheme_code or "").strip()
        if not re.fullmatch(r"\d{3,8}", code):
            return None
        return self._live(code) or load_starter(code)


def build(config: dict, deps: dict) -> MfdataHoldings:
    return MfdataHoldings(config)
