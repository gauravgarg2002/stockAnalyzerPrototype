from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import StockFundamentals


class MockFundamentals:
    mode = "mock"

    def get(self, symbol: str) -> Optional[StockFundamentals]:
        return ss.stock(symbol)

    def universe(self) -> list[dict]:
        return [{"symbol": r["symbol"], "name": r["name"], "sector": r["sector"], "sizeBand": r["sizeBand"]} for r in ss.stock_records().values()]

    def search_stocks(self, query: str, limit: int) -> list[dict]:
        q = query.strip().lower()
        out = []
        for r in ss.stock_records().values():
            if q in r["symbol"].lower() or q in r["name"].lower():
                out.append({"symbol": r["symbol"], "name": r["name"], "sector": r["sector"], "sizeBand": r["sizeBand"], "checkAvailable": True})
        return out[:limit] if limit else out


def build(config: dict, deps: dict) -> MockFundamentals:
    return MockFundamentals()
