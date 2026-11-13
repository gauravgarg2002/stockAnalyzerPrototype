from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import NavSeries


class MockFundNav:
    mode = "mock"

    def nav_series(self, scheme_code: str) -> Optional[NavSeries]:
        return ss.navs(scheme_code)


def build(config: dict, deps: dict) -> MockFundNav:
    return MockFundNav()
