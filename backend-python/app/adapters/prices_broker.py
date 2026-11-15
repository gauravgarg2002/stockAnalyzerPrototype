"""Price adapter backed by the active broker adapter's historical candles (stocks only)."""
from __future__ import annotations

import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from ..errors import ApiError
from .base import PriceSeries
from .http_util import DiskCache, today_ist
from .prices_nse_eod import from_cache, to_cache

SOURCE = "NSE"  # market prices; the broker is only the transport
YEARS = 5


class BrokerPrices:
    mode = "broker"

    def __init__(self, config: dict, broker: Any):
        self._broker = broker
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "prices_broker", float(c.get("pricesHours", 12)))
        self._fetch_lock = threading.Lock()  # one history fetch at a time; waiters then read the cache

    def _series(self, key: str, fetch, years: int) -> list | None:
        def cached():
            c = self._cache.get(key)
            return from_cache(c) if c is not None else None

        pts = cached()
        if pts is None:
            with self._fetch_lock:
                pts = cached()  # another request may have filled it while we waited
                if pts is None:
                    end = today_ist()
                    start = date(end.year - years, end.month, min(end.day, 28))
                    try:
                        pts = fetch(start, end)
                    except ApiError:
                        return None
                    if pts:
                        self._cache.set(key, to_cache(pts))
        return pts or None

    def stock_series(self, symbol: str) -> Optional[PriceSeries]:
        sym = (symbol or "").strip().upper()
        if not sym or self._broker is None or getattr(self._broker, "mode", "mock") == "mock":
            return None
        pts = self._series(f"bk:{sym}", lambda s, e: self._broker.historical(sym, s, e), YEARS)
        return PriceSeries(sym, pts, SOURCE, pts[-1][0].isoformat()) if pts else None

    def index_series(self, index_id: str) -> Optional[PriceSeries]:
        """Nifty 50 history from the broker's index candles; other indices come from the exchange adapter."""
        iid = (index_id or "").strip().upper()
        fetch = getattr(self._broker, "index_history", None)
        if iid != "NIFTY50" or fetch is None or getattr(self._broker, "mode", "mock") == "mock":
            return None
        pts = self._series(f"ix:{iid}", lambda s, e: fetch(iid, s, e), 10)
        return PriceSeries(iid, pts, SOURCE, pts[-1][0].isoformat()) if pts else None


def build(config: dict, deps: dict) -> BrokerPrices:
    return BrokerPrices(config, deps.get("broker"))
