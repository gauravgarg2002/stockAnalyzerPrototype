"""broker_then_nse_eod composition: broker candles first, exchange end-of-day files as fallback."""
from __future__ import annotations

import sys
import time
from typing import Optional

from ..errors import ApiError
from .base import PriceAdapter, PriceSeries
from .prices_broker import BrokerPrices
from .prices_nse_eod import NseEodPrices


class ChainPrices:
    mode = "broker_then_nse_eod"

    def __init__(self, primary: PriceAdapter, fallback: PriceAdapter, fail_ttl_s: float = 600.0):
        self._chain = [primary, fallback]
        self._fail_ttl_s = fail_ttl_s
        self._down: dict[int, float] = {}  # adapter position -> time until which it is skipped

    def _first(self, method: str, key: str) -> Optional[PriceSeries]:
        """First non-empty series. An adapter that errors is skipped for a while, so a blocked source
        is not hit once per stock per page. None means prices are unavailable; pages still load."""
        for i, a in enumerate(self._chain):
            if time.monotonic() < self._down.get(i, 0.0):
                continue
            try:
                s = getattr(a, method)(key)
            except ApiError as e:
                if e.code != "BROKER_NOT_CONNECTED":
                    self._down[i] = time.monotonic() + self._fail_ttl_s
                    print(f"[prices] {method} {key}: {e.code}: {e} (source paused for {int(self._fail_ttl_s)}s)",
                          file=sys.stderr, flush=True)
                continue
            if s is not None and s.points:
                return s
        return None

    def stock_series(self, symbol: str) -> Optional[PriceSeries]:
        return self._first("stock_series", symbol)

    def index_series(self, index_id: str) -> Optional[PriceSeries]:
        return self._first("index_series", index_id)


def build(config: dict, deps: dict) -> ChainPrices:
    return ChainPrices(BrokerPrices(config, deps.get("broker")), NseEodPrices(config))
