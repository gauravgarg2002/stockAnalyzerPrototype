"""Plain input containers passed from handlers to the (framework-free) engines."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..adapters.base import (FundMeta, FundPortfolio, NavSeries, PriceSeries, StockFundamentals, SurveillanceEntry)


@dataclass
class StockInputs:
    f: StockFundamentals
    prices: Optional[PriceSeries]
    benchmark: Optional[PriceSeries]  # NIFTY50
    surveillance: Optional[list[SurveillanceEntry]]  # None = source unavailable
    as_of: date
    size_bands: dict = field(default_factory=lambda: {"largeMinCrore": 100000, "midMinCrore": 33000, "smallMinCrore": 6000})
    benchmark_name: str = "Nifty 50"
    checkable_symbols: frozenset = frozenset()


@dataclass
class FundInputs:
    meta: FundMeta
    nav: Optional[NavSeries]
    portfolio: Optional[FundPortfolio]
    benchmark: Optional[PriceSeries]
    benchmark_name: str
    category: Optional[dict]
    twin: Optional[FundMeta]
    twin_category_note: Optional[str]
    as_of: date
    amount_inr: float
    amount_basis: str  # HOLDING | ILLUSTRATIVE | USER_INPUT
    user_funds: list[dict] = field(default_factory=list)
    stock_symbols: frozenset = frozenset()
