import pytest

from app import handlers
from app.adapters import broker_mock
from app.context import AppContext
from app import config as cfgmod
from app.errors import ApiError


def fresh():
    return AppContext(cfgmod.load("/nonexistent/x.yaml"))


def test_status_before_and_after_connect():
    c = fresh()
    assert handlers.broker_login_status(c, {})["status"] == "NOT_CONNECTED"
    s = handlers.broker_login_start(c, {})
    assert s == {"sampleData": True, "brokerMode": "mock", "status": "CONNECTED", "loginUrl": None, "message": "Sample account connected."}
    st = handlers.broker_login_status(c, {})
    assert st["status"] == "CONNECTED" and st["accountLabel"] == "Your Zerodha account (sample)" and st["brokerMode"] == "mock"


def test_portfolio_requires_connection():
    c = fresh()
    with pytest.raises(ApiError) as e:
        handlers.broker_portfolio(c, {})
    assert e.value.status == 409 and e.value.code == "BROKER_NOT_CONNECTED"


def test_portfolio_content():
    c = fresh()
    handlers.broker_login_start(c, {})
    p = handlers.broker_portfolio(c, {})
    assert p["sampleData"] is True and p["source"] == "Your Zerodha account" and p["asOf"] == "2026-10-30"
    assert len(p["stocks"]) == 6 and len(p["funds"]) == 4 and p["idleCashInr"] == 42350.75 and p["unmatched"] == []
    tcs = next(s for s in p["stocks"] if s["symbol"] == "TCS")
    assert tcs == {"symbol": "TCS", "isin": tcs["isin"], "quantity": 15, "avgPrice": 3410.0, "lastPrice": tcs["lastPrice"], "firstBuyDate": "2023-06-05"}
    assert tcs["isin"] == "INESMP000002" and tcs["lastPrice"] > 0
    f = next(x for x in p["funds"] if x["schemeCode"] == "900101")
    assert f["units"] == 1850.234 and f["avgNav"] == 62.4 and f["lastNav"] == 62.4012 and f["isin"] == "INFSMP900101"
    assert all(x["firstBuyDate"] for x in p["funds"])


def test_logout_and_complete():
    c = fresh()
    handlers.broker_login_start(c, {})
    out = handlers.broker_logout(c, {})
    assert out["status"] == "NOT_CONNECTED" and out["loginUrl"] is None
    with pytest.raises(ApiError) as e:
        handlers.broker_login_complete(c, {"body": {"requestToken": "abc"}})
    assert e.value.status == 400
    with pytest.raises(ApiError) as e:
        handlers.broker_login_complete(c, {"body": {}})
    assert e.value.status == 400


def test_mock_mode_never_imports_live_modules():
    import subprocess, sys, json
    code = ("import sys; from app import config, handlers; from app.context import AppContext; c=AppContext(config.load('/nonexistent'));"
            "handlers.health(c,{}); handlers.stock_check(c,{'symbol':'TCS'}); handlers.fund_check(c,{'schemeCode':'900101','body':{'amountInr':1000}});"
            "handlers.broker_login_start(c,{}); handlers.broker_portfolio(c,{}); handlers.search(c,{'q':'a'});"
            "live=['broker_kite_mcp','broker_kite_connect','fundamentals_screener','prices_broker','prices_nse_eod','prices_chain','surveillance_nse',"
            "'fund_nav_mfapi','fund_meta_amfi','fund_holdings_mfdata','http_util','screener_parse'];"
            "print(json.dumps([m for m in live if 'app.adapters.'+m in sys.modules]))")
    import os
    root = os.path.dirname(os.path.dirname(__file__))
    out = subprocess.run([sys.executable, "-c", "import json;" + code], cwd=root, capture_output=True, text=True, env={**os.environ, "APP_CONFIG": "/nonexistent"})
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []
