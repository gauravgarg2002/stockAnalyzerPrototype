import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_CONFIG", str(ROOT / "nonexistent-config.yaml"))

from app import config as cfgmod  # noqa: E402
from app import handlers  # noqa: E402
from app.context import AppContext  # noqa: E402

SAMPLE_FUND_OVERLAPS = [{"schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "overlapPct": 41.37, "commonCount": 27}]
ALL_STOCKS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC", "LT", "SUNPHARMA", "MARUTI", "ASIANPAINT", "TATASTEEL", "BHARTIARTL", "VOLTAS", "FEDERALBNK", "DECCANINF", "SHIVAGRO"]
ALL_FUNDS = ["900101", "900102", "900201", "900301", "900401", "900501", "900601", "900701", "900801"]


@pytest.fixture(scope="session")
def ctx():
    return AppContext(cfgmod.load("/nonexistent/app-config.yaml"))


@pytest.fixture(scope="session")
def stock(ctx):
    cache = {}

    def get(sym):
        if sym not in cache:
            cache[sym] = handlers.stock_check(ctx, {"symbol": sym})
        return cache[sym]
    return get


@pytest.fixture(scope="session")
def fund(ctx):
    cache = {}

    def get(code, amount=115448.0, basis="HOLDING", user_funds=None):
        key = (code, amount, basis, repr(user_funds))
        if key not in cache:
            cache[key] = handlers.fund_check(ctx, {"schemeCode": code, "body": {"amountInr": amount, "amountBasis": basis, "userFunds": user_funds or []}})
        return cache[key]
    return get


def by_id(items, id):
    return next(i for i in items if i["id"] == id)


def fig(block, id):
    return next(f for f in block["figures"] if f["id"] == id)
