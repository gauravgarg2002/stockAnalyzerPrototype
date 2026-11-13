from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import PriceSeries


class MockPrices:
    mode = "mock"

    def stock_series(self, symbol: str) -> Optional[PriceSeries]:
        return ss.stock_prices(symbol)

    def index_series(self, index_id: str) -> Optional[PriceSeries]:
        return ss.index_prices(index_id)


def build(config: dict, deps: dict) -> MockPrices:
    return MockPrices()
