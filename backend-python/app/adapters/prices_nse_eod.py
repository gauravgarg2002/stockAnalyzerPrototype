"""Price adapter: NSE end-of-day history (cookie warm-up, yearly chunks, disk cache, rate limit).

Importing performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: endpoints (/api/historical/cm/equity, /api/historical/indicesHistory), the
cookie warm-up requirement, the 1-year window limit and the response field names are taken from public behaviour
of the exchange website and are isolated in parse_equity_history / parse_index_history. Only the NIFTY50 price
index is available this way; TRI and other indices return None (callers then show "not available").
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

from .base import PricePoint, PriceSeries
from .http_util import DEFAULT_TIMEOUT, DiskCache, RateLimiter, make_session, today_ist, unavailable

SOURCE = "NSE"
CHUNK_DAYS = 360
STOCK_YEARS = 5
INDEX_YEARS = 10
INDEX_TYPES = {"NIFTY50": "NIFTY 50"}


def _d(s: Any) -> date | None:
    if not s:
        return None
    t = str(s).strip()
    for fmt, n in (("%Y-%m-%d", 10), ("%d-%b-%Y", 11), ("%d-%m-%Y", 10)):
        try:
            return datetime.strptime(t[:n], fmt).date()
        except ValueError:
            continue
    return None


def _num(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_equity_history(obj: Any) -> list[PricePoint]:
    """UNVERIFIED AGAINST LIVE SERVICE. {'data': [{'CH_TIMESTAMP': '2025-12-31', 'CH_CLOSING_PRICE': 3925.4,
    'CH_TOT_TRADED_QTY': 1234567, ...}]} -> [(date, close, volume)] ascending."""
    rows = obj.get("data") if isinstance(obj, dict) else None
    out: dict[date, PricePoint] = {}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        d0 = _d(r.get("CH_TIMESTAMP") or r.get("mTIMESTAMP"))
        close = _num(r.get("CH_CLOSING_PRICE"))
        if d0 is None or close is None:
            continue
        vol = _num(r.get("CH_TOT_TRADED_QTY"))
        out[d0] = (d0, close, int(vol) if vol is not None else None)
    return [out[k] for k in sorted(out)]


def parse_index_history(obj: Any) -> list[PricePoint]:
    """UNVERIFIED AGAINST LIVE SERVICE. {'data': {'indexCloseOnlineRecords': [{'EOD_TIMESTAMP': '31-Dec-2025',
    'EOD_CLOSE_INDEX_VAL': 26000.5}]}} -> [(date, close, None)] ascending."""
    data = obj.get("data") if isinstance(obj, dict) else None
    rows = data.get("indexCloseOnlineRecords") if isinstance(data, dict) else None
    out: dict[date, PricePoint] = {}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        d0 = _d(r.get("EOD_TIMESTAMP"))
        close = _num(r.get("EOD_CLOSE_INDEX_VAL"))
        if d0 is not None and close is not None:
            out[d0] = (d0, close, None)
    return [out[k] for k in sorted(out)]


def chunks(start: date, end: date, days: int = CHUNK_DAYS) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def to_cache(points: list[PricePoint]) -> list[list]:
    return [[p[0].isoformat(), p[1], p[2]] for p in points]


def from_cache(rows: list[list]) -> list[PricePoint]:
    return [(date.fromisoformat(r[0]), float(r[1]), r[2]) for r in rows]


class NseEodPrices:
    mode = "nse_eod"

    def __init__(self, config: dict, session: requests.Session | None = None, limiter: RateLimiter | None = None):
        n = config.get("nse", {}) or {}
        self._base = str(n.get("baseUrl") or "https://www.nseindia.com").rstrip("/")
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "prices", float(c.get("pricesHours", 12)))
        self._limiter = limiter or RateLimiter(float(n.get("minIntervalSeconds", 2)))
        self._session = session or make_session(headers={
            "Accept": "application/json, text/plain, */*", "Referer": self._base + "/"})
        self._warm = False

    def _warmup(self) -> None:
        if self._warm:
            return
        self._limiter.wait()
        try:
            self._session.get(self._base + "/", timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise unavailable("Exchange price data could not be reached. Please try again later.",
                              reason=type(e).__name__)
        self._warm = True

    def _get_json(self, path: str, params: dict) -> Any:
        self._warmup()
        self._limiter.wait()
        try:
            r = self._session.get(self._base + path, params=params, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise unavailable("Exchange price data could not be reached. Please try again later.",
                              reason=type(e).__name__)
        if r.status_code == 401 or r.status_code == 403:
            self._warm = False  # cookies expired: warm up again next time
            raise unavailable("Exchange price data is temporarily limited. Please try again later.",
                              httpStatus=r.status_code)
        if r.status_code != 200:
            raise unavailable("Exchange price data returned an error.", httpStatus=r.status_code)
        try:
            return r.json()
        except ValueError:
            raise unavailable("Exchange price data was in an unexpected format.")

    def _history(self, key: str, years: int, fetch_chunk) -> Optional[list[PricePoint]]:
        cached = self._cache.get(key)
        if cached is not None:
            return from_cache(cached)
        end = today_ist()
        start = date(end.year - years, end.month, min(end.day, 28))
        pts: dict[date, PricePoint] = {}
        for a, b in chunks(start, end):
            for p in fetch_chunk(a, b):
                pts[p[0]] = p
        out = [pts[k] for k in sorted(pts)]
        if out:
            self._cache.set(key, to_cache(out))
        return out or None

    def stock_series(self, symbol: str) -> Optional[PriceSeries]:
        sym = (symbol or "").strip().upper()
        if not sym:
            return None

        def fetch(a: date, b: date) -> list[PricePoint]:
            obj = self._get_json("/api/historical/cm/equity", {
                "symbol": sym, "series": '["EQ"]', "from": a.strftime("%d-%m-%Y"), "to": b.strftime("%d-%m-%Y")})
            return parse_equity_history(obj)

        pts = self._history(f"eq:{sym}", STOCK_YEARS, fetch)
        return PriceSeries(sym, pts, SOURCE, pts[-1][0].isoformat()) if pts else None

    def index_series(self, index_id: str) -> Optional[PriceSeries]:
        itype = INDEX_TYPES.get(index_id)
        if itype is None:
            return None

        def fetch(a: date, b: date) -> list[PricePoint]:
            obj = self._get_json("/api/historical/indicesHistory", {
                "indexType": itype, "from": a.strftime("%d-%m-%Y"), "to": b.strftime("%d-%m-%Y")})
            return parse_index_history(obj)

        pts = self._history(f"ix:{index_id}", INDEX_YEARS, fetch)
        return PriceSeries(index_id, pts, SOURCE, pts[-1][0].isoformat()) if pts else None


def build(config: dict, deps: dict) -> NseEodPrices:
    return NseEodPrices(config)
