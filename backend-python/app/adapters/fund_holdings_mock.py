from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import FundPortfolio


class MockFundHoldings:
    mode = "mock"

    def portfolio(self, scheme_code: str) -> Optional[FundPortfolio]:
        return ss.fund_portfolio(scheme_code)


def build(config: dict, deps: dict) -> MockFundHoldings:
    return MockFundHoldings()
