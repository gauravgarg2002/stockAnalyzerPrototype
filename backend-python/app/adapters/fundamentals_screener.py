"""Fundamentals adapter: server-side fetch of public company pages, parsed by screener_parse.

User-facing source label is "Company filings"; the fetch site's name never appears in any user-facing string
(this module's logs/errors use neutral wording). 24 h DiskCache, RateLimiter between requests, optional session
cookie from config. Importing performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: URL scheme (/company/{SYMBOL}/consolidated/ then /company/{SYMBOL}/), the page
layout assumed by screener_parse, the search endpoint shape (parse_search_json), and the mapping of the page's
tables (values in crore) to the contract's annual/quarterly/shareholding rows. Fields the page does not carry in
its HTML are left empty/None: revenueSegments, valuationHistory, events, quarterly.resultsDate, isin,
marketCapRank, most peerGroup.medians keys.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

from . import screener_parse as sp
from .base import StockFundamentals
from .http_util import DEFAULT_TIMEOUT, DiskCache, RateLimiter, make_session, today_ist, unavailable

CRORE = 1e7
LABEL = "Company filings"
_FIN_WORDS = ("bank", "finance", "financial", "insurance", "nbfc", "broking", "asset management", "housing finance")
_SYM_RE = re.compile(r"^[A-Z0-9&\-]{1,20}$")


# ---------- pure mapping helpers ----------

def size_band(market_cap_crore: float | None, bands: dict) -> str:
    if market_cap_crore is None:
        return "MICRO"
    if market_cap_crore >= float(bands.get("largeMinCrore", 100000)):
        return "LARGE"
    if market_cap_crore >= float(bands.get("midMinCrore", 33000)):
        return "MID"
    if market_cap_crore >= float(bands.get("smallMinCrore", 6000)):
        return "SMALL"
    return "MICRO"


def is_financial(sector: str | None, industry: str | None) -> bool:
    t = f"{sector or ''} {industry or ''}".lower()
    return any(w in t for w in _FIN_WORDS)


def _end_date(label: str) -> date | None:
    iso = sp.period_to_date(label)
    return date.fromisoformat(iso) if iso else None


def _cr(v: float | None) -> float | None:
    return None if v is None else round(v * CRORE, 2)


def _row(series: dict, *names: str) -> list[float | None]:
    for n in names:
        if n in series["rows"]:
            return series["rows"][n]
    # tolerate label variants, e.g. "Net Profit +" / "Other Liabilities"
    for key, vals in series["rows"].items():
        for n in names:
            if key.lower().startswith(n.lower()):
                return vals
    return [None] * len(series["periods"])


def _at(vals: list, i: int) -> float | None:
    return vals[i] if 0 <= i < len(vals) else None


def map_annual(pl: dict, bs: dict, limit: int = 5) -> list[dict]:
    """Annual rows (values converted from crore to rupees). Latest last in the page; returned oldest first."""
    sales, op = _row(pl, "Sales", "Revenue"), _row(pl, "Operating Profit")
    interest, np_, eps = _row(pl, "Interest"), _row(pl, "Net Profit"), _row(pl, "EPS in Rs")
    eq, res = _row(bs, "Equity Capital"), _row(bs, "Reserves")
    debt, cash = _row(bs, "Borrowings"), _row(bs, "Cash Equivalents", "Cash")
    bs_idx = {p: i for i, p in enumerate(bs["periods"])}
    rows = []
    for i, p in enumerate(pl["periods"]):
        end = _end_date(p)
        if end is None:  # TTM column
            continue
        j = bs_idx.get(p)
        start = date(end.year - 1, end.month, calendar.monthrange(end.year - 1, end.month)[1]) + timedelta(days=1)
        e_cap, e_res = (_at(eq, j), _at(res, j)) if j is not None else (None, None)
        networth = (e_cap or 0) + (e_res or 0) if (e_cap is not None or e_res is not None) else None
        rows.append({
            "fy": f"FY{end.year}", "periodStart": start.isoformat(), "periodEnd": end.isoformat(),
            "revenueInr": _cr(_at(sales, i)), "operatingProfitInr": _cr(_at(op, i)), "netProfitInr": _cr(_at(np_, i)),
            "totalDebtInr": _cr(_at(debt, j)) if j is not None else None,
            "cashInr": _cr(_at(cash, j)) if j is not None else None,
            "netWorthInr": _cr(networth), "interestInr": _cr(_at(interest, i)), "eps": _at(eps, i),
        })
    return rows[-limit:]


_MONTH_NAMES = [calendar.month_name[i] for i in range(1, 13)]


def map_quarterly(q: dict, limit: int = 8) -> list[dict]:
    """Latest first. resultsDate is not in the page tables -> None."""
    sales, np_ = _row(q, "Sales", "Revenue"), _row(q, "Net Profit")
    out = []
    for i, p in enumerate(q["periods"]):
        end = _end_date(p)
        if end is None:
            continue
        sm = (end.month - 3) % 12 + 1  # first month of the quarter
        label = f"{_MONTH_NAMES[sm - 1]}–{_MONTH_NAMES[end.month - 1]} {end.year}"
        out.append({"label": label, "periodEnd": end.isoformat(), "resultsDate": None,
                    "revenueInr": _cr(_at(sales, i)), "netProfitInr": _cr(_at(np_, i))})
    out.sort(key=lambda r: r["periodEnd"], reverse=True)
    return out[:limit]


def map_shareholding(s: dict, pledged_latest: float | None, limit: int = 5) -> list[dict]:
    pro, fii, dii, pub = (_row(s, "Promoters"), _row(s, "FIIs"), _row(s, "DIIs"), _row(s, "Public"))
    out = []
    for i, p in enumerate(s["periods"]):
        end = _end_date(p)
        if end is None:
            continue
        out.append({"quarterEnd": end.isoformat(), "promoterPct": _at(pro, i), "pledgedPctOfPromoter": None,
                    "fiiPct": _at(fii, i), "diiPct": _at(dii, i), "publicPct": _at(pub, i)})
    out.sort(key=lambda r: r["quarterEnd"], reverse=True)
    out = out[:limit]
    if out:
        out[0]["pledgedPctOfPromoter"] = pledged_latest  # the page shows only the latest pledge figure
    return out


def map_peers(parsed: dict) -> dict:
    p = parsed["peers"]
    members = []
    for r in p["rows"]:
        name = r.get("Name") or ""
        if not name or name == parsed.get("name"):
            continue
        members.append({"name": name, "symbol": None})
    medians: dict[str, float] = {}
    if p.get("median"):
        pe = sp.parse_number(p["median"].get("P/E"))
        if pe is not None:
            medians["pe"] = pe
    return {"name": parsed.get("industry") or parsed.get("sector") or "Peers", "members": members[:5],
            "medians": medians}


def map_fundamentals(parsed: dict, symbol: str, size_bands: dict, as_of: str) -> StockFundamentals:
    top = parsed["topRatios"]
    mcap = top.get("Market Cap")
    price = top.get("Current Price")
    shares = round(mcap * CRORE / price) if mcap and price else None
    sector, industry = parsed.get("sector") or "", parsed.get("industry") or ""
    return StockFundamentals(
        symbol=symbol, name=parsed.get("name") or symbol, isin=None,
        sector=sector, industry=industry, sizeBand=size_band(mcap, size_bands), marketCapRank=None,
        isFinancial=is_financial(sector, industry), sharesOutstanding=shares,
        about=parsed.get("about") or "", revenueSegments=[], peerGroup=map_peers(parsed),
        annual=map_annual(parsed["annual"], parsed["balanceSheet"]), quarterly=map_quarterly(parsed["quarterly"]),
        shareholding=map_shareholding(parsed["shareholding"], top.get("Pledged percentage")),
        valuationHistory=[], dividendYieldPct=top.get("Dividend Yield"), events=[],
        source=LABEL, asOf=as_of, exchange="NSE", fictional=False, lastPrice=price)


def parse_search_json(obj: Any) -> list[dict]:
    """UNVERIFIED AGAINST LIVE SERVICE. Expected: [{"id": 1, "name": "Tata Consultancy Services Ltd",
    "url": "/company/TCS/consolidated/"}, ...] -> [{symbol, name}]."""
    out = []
    if isinstance(obj, list):
        for r in obj:
            if not isinstance(r, dict):
                continue
            m = re.search(r"/company/([A-Za-z0-9&\-]+)/", str(r.get("url") or ""))
            if m and r.get("name"):
                out.append({"symbol": m.group(1).upper(), "name": str(r["name"])})
    return out


# ---------- adapter ----------

class ScreenerFundamentals:
    mode = "screener"

    def __init__(self, config: dict, session: requests.Session | None = None, limiter: RateLimiter | None = None):
        sc = config.get("screener", {}) or {}
        self._base = str(sc.get("baseUrl") or "https://www.screener.in").rstrip("/")
        self._cookie = str(sc.get("sessionCookie") or "").strip()
        self._bands = config.get("sizeBands", {}) or {}
        cache_cfg = config.get("cache", {}) or {}
        root = Path(str(cache_cfg.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "fundamentals", float(cache_cfg.get("fundamentalsHours", 24)))
        self._limiter = limiter or RateLimiter(float(sc.get("minIntervalSeconds", 3)))
        self._session = session or make_session()

    def _fetch(self, path: str) -> requests.Response:
        headers = {}
        if self._cookie:
            headers["Cookie"] = self._cookie if "=" in self._cookie else f"sessionid={self._cookie}"
        self._limiter.wait()
        try:
            return self._session.get(self._base + path, headers=headers, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise unavailable("Company data could not be reached. Please try again in a moment.",
                              reason=type(e).__name__)

    def _page(self, symbol: str) -> Optional[str]:
        fallback: Optional[str] = None
        for path in (f"/company/{symbol}/consolidated/", f"/company/{symbol}/"):
            r = self._fetch(path)
            if r.status_code == 404:
                continue
            if r.status_code in (401, 403, 429) or r.status_code >= 500:
                raise unavailable("Company data is temporarily limited. Please try again later.",
                                  httpStatus=r.status_code)
            if r.status_code == 200:
                parsed = sp.parse_company_page(r.text)
                if parsed["name"] and parsed["annual"]["rows"]:
                    return r.text
                if parsed["name"] and fallback is None:  # empty consolidated shell: try standalone first
                    fallback = r.text
        return fallback

    def get(self, symbol: str) -> Optional[StockFundamentals]:
        sym = (symbol or "").strip().upper()
        if not _SYM_RE.match(sym):
            return None
        key = f"parsed:{sym}"
        parsed = self._cache.get(key)
        if parsed is None:
            html = self._page(sym)
            if html is None:
                return None
            parsed = sp.parse_company_page(html)
            if not parsed["name"]:
                raise unavailable("Company data was in an unexpected format.", reason="unrecognised layout")
            self._cache.set(key, parsed)
        return map_fundamentals(parsed, sym, self._bands, today_ist().isoformat())

    def search_stocks(self, query: str, limit: int) -> list[dict]:
        q = (query or "").strip()
        if len(q) < 2:
            return []
        key = f"search:{q.lower()}"
        hits = self._cache.get(key)
        if hits is None:
            self._limiter.wait()
            try:
                r = self._session.get(self._base + "/api/company/search/", params={"q": q, "v": 3, "fts": 1},
                                      timeout=DEFAULT_TIMEOUT)
                hits = parse_search_json(r.json()) if r.status_code == 200 else []
            except (requests.RequestException, ValueError):
                return []
            self._cache.set(key, hits)
        return [{"symbol": h["symbol"], "name": h["name"], "sector": "", "sizeBand": None, "checkAvailable": True}
                for h in hits[: max(0, int(limit))]]

    def universe(self) -> list[dict]:
        return []  # live mode has no bundled universe; companies are looked up on demand


def build(config: dict, deps: dict) -> ScreenerFundamentals:
    return ScreenerFundamentals(config)
