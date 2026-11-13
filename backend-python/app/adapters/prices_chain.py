"""broker_then_nse_eod composition: broker candles first, exchange end-of-day files as fallback."""
from __future__ import annotations

from typing import Optional

from ..errors import ApiError
from .base import PriceAdapter, PriceSeries
from .prices_broker import BrokerPrices
from .prices_nse_eod import NseEodPrices


class ChainPrices:
    mode = "broker_then_nse_eod"

    def __init__(self, primary: PriceAdapter, fallback: PriceAdapter):
        self._chain = [primary, fallback]

    def _first(self, method: str, key: str) -> Optional[PriceSeries]:
        last_err: ApiError | None = None
        for a in self._chain:
            try:
                s = getattr(a, method)(key)
            except ApiError as e:
                last_err = e
                continue
            if s is not None and s.points:
                return s
        if last_err is not None and last_err.code not in ("BROKER_NOT_CONNECTED",):
            raise last_err
        return None

    def stock_series(self, symbol: str) -> Optional[PriceSeries]:
        return self._first("stock_series", symbol)

    def index_series(self, index_id: str) -> Optional[PriceSeries]:
        return self._first("index_series", index_id)


def build(config: dict, deps: dict) -> ChainPrices:
    return ChainPrices(BrokerPrices(config, deps.get("broker")), NseEodPrices(config))
