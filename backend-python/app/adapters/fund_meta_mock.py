from __future__ import annotations

from typing import Optional

from . import sample_store as ss
from .base import FundMeta


class MockFundMeta:
    mode = "mock"

    def get(self, scheme_code: str) -> Optional[FundMeta]:
        return ss.fund_meta(scheme_code)

    def find_by_isin(self, isin: str) -> Optional[FundMeta]:
        for code, r in ss.fund_records().items():
            if r["isin"] == isin:
                return ss.fund_meta(code)
        return None

    def search(self, query: str, limit: int) -> list[FundMeta]:
        q = query.strip().lower()
        out = []
        for code, r in ss.fund_records().items():
            if q in r["name"].lower() or q in r["amc"].lower() or q in r["shortName"].lower() or q in code:
                out.append(ss.fund_meta(code))
        return out[:limit] if limit else out

    def category(self, category_name: str) -> Optional[dict]:
        return ss.categories().get(category_name)

    def all_codes(self) -> list[str]:
        return list(ss.fund_records().keys())


def build(config: dict, deps: dict) -> MockFundMeta:
    return MockFundMeta()
