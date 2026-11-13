from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import SurveillanceEntry


class MockSurveillance:
    mode = "mock"

    def lookup(self, symbol: str) -> Optional[list[SurveillanceEntry]]:
        return [e for e in ss.surveillance_entries() if e.symbol == symbol.upper()]


def build(config: dict, deps: dict) -> MockSurveillance:
    return MockSurveillance()
