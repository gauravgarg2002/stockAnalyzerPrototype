"""Kite adapters: pure mapping, fake REST transport, and a loopback MCP server (127.0.0.1 only; no external hosts)."""
import hashlib
import json
import socket
import threading
import time
from datetime import date

import pytest

from app.adapters import broker_kite_connect as kc
from app.adapters import broker_kite_mcp as km
from app.adapters.base import FundMeta
from app.errors import ApiError


class Meta:
    mode = "mock"

    def find_by_isin(self, isin):
        if isin == "INF179K01YV8":
            return FundMeta(schemeCode="900301", isin=isin, name="Godavari Midcap Fund - Direct Plan - Growth", shortName="G",
                            amc="G", category="Mid Cap Fund", categoryGroup="EQUITY", planType="DIRECT", twinSchemeCode=None,
                            launchDate=None, aumInr=None, aumInr1yAgo=None, terPct=None, terAsOf=None, exitLoad=None,
                            lockInYears=None, benchmarkId=None)
        return None


HOLDINGS = {"status": "success", "data": [
    {"tradingsymbol": "TCS", "exchange": "NSE", "isin": "INE467B01029", "quantity": 15, "t1_quantity": 0,
     "average_price": 3410.0, "last_price": 3925.4},
    {"tradingsymbol": "GONE", "exchange": "NSE", "isin": "INE000000002", "quantity": 0, "t1_quantity": 0,
     "average_price": 10, "last_price": 11},
    {"tradingsymbol": "NEWBUY", "exchange": "NSE", "isin": "INE000000003", "quantity": 0, "t1_quantity": 5,
     "average_price": 100, "last_price": 101},
    {"tradingsymbol": "ITC-BE", "exchange": "NSE", "isin": "INE154A01025", "quantity": 100, "t1_quantity": 0,
     "average_price": 395.5, "last_price": 410.0}]}
MF = {"status": "success", "data": [
    {"folio": "1", "fund": "Godavari Midcap Fund - Direct Plan - Growth", "tradingsymbol": "INF179K01YV8",
     "average_price": 98.3, "last_price": 101.2, "quantity": 410.112},
    {"folio": "2", "fund": "Example Gilt Fund - Direct Growth", "tradingsymbol": "INF000X01ABC",
     "average_price": 19, "last_price": 20, "quantity": 10}]}
MARGINS = {"status": "success", "data": {"equity": {"enabled": True, "net": 5000, "available": {"cash": 1, "live_balance": 42350.75}}}}


def test_map_stock_holdings():
    s = kc.map_stock_holdings(kc.unwrap_rows(HOLDINGS))
    assert [x["symbol"] for x in s] == ["TCS", "NEWBUY", "ITC"]
    assert s[0] == {"symbol": "TCS", "isin": "INE467B01029", "quantity": 15, "avgPrice": 3410.0, "lastPrice": 3925.4,
                    "firstBuyDate": None}
    assert s[1]["quantity"] == 5


def test_map_mf_and_margins():
    funds, un = kc.map_mf_holdings(kc.unwrap_rows(MF), Meta())
    assert funds == [{"schemeCode": "900301", "isin": "INF179K01YV8", "name": "Godavari Midcap Fund - Direct Plan - Growth",
                      "units": 410.112, "avgNav": 98.3, "lastNav": 101.2, "firstBuyDate": None}]
    assert un == [{"name": "Example Gilt Fund - Direct Growth", "isin": "INF000X01ABC", "reason": "Fund not found in fund list."}]
    assert kc.margins_cash(MARGINS) == 42350.75 and kc.margins_cash({}) is None and kc.margins_cash(None) is None


def test_candles_and_instruments():
    c = {"status": "success", "data": {"candles": [["2026-10-29T00:00:00+0530", 1, 2, 0.5, 1.5, 100],
                                                   ["2026-10-30T00:00:00+0530", 1, 2, 0.5, 1.75, 200], ["bad"]]}}
    assert kc.parse_candles(c) == [(date(2026, 10, 29), 1.5, 100), (date(2026, 10, 30), 1.75, 200)]
    csv_text = ("instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,"
                "instrument_type,segment,exchange\n738561,2885,RELIANCE,RELIANCE INDUSTRIES,0,,0,0.05,1,EQ,NSE,NSE\n"
                "1,1,RELIANCE24OCTFUT,x,0,,0,0.05,1,FUT,NFO-FUT,NFO\n")
    assert kc.parse_instruments_csv(csv_text) == {"RELIANCE": 738561}


def test_checksum():
    assert kc.checksum("k", "rt", "s") == hashlib.sha256(b"krts").hexdigest()


class FResp:
    def __init__(self, status=200, js=None, text=""):
        self.status_code, self._js, self.text = status, js, text

    def json(self):
        if self._js is None:
            raise ValueError
        return self._js


class FSession:
    def __init__(self, handler):
        self.handler, self.calls, self.headers = handler, [], {}

    def request(self, method, url, params=None, data=None, headers=None, timeout=None):
        self.calls.append((method, url, params, data, headers))
        return self.handler(method, url, params, data, headers)


def kite_handler(method, url, params, data, headers):
    path = url.replace("https://api.kite.trade", "")
    if (method, path) == ("POST", "/session/token"):
        return FResp(js={"status": "success", "data": {"access_token": "AT", "user_id": "AB1234"}})
    assert headers.get("Authorization") == "token KEY:AT"
    if path == "/user/profile":
        return FResp(js={"status": "success", "data": {"user_id": "AB1234"}})
    if path == "/portfolio/holdings":
        return FResp(js=HOLDINGS)
    if path == "/mf/holdings":
        return FResp(js=MF)
    if path == "/user/margins":
        return FResp(js=MARGINS)
    if path == "/instruments/NSE":
        return FResp(text="instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,"
                          "instrument_type,segment,exchange\n738561,2885,TCS,TCS,0,,0,0.05,1,EQ,NSE,NSE\n")
    if path == "/instruments/historical/738561/day":
        return FResp(js={"status": "success", "data": {"candles": [["2026-10-30T00:00:00+0530", 1, 2, 3, 4.5, 6]]}})
    return FResp(404, js={"status": "error", "message": "nope"})


def test_kite_connect_full_flow():
    sess = FSession(kite_handler)
    b = kc.KiteConnectBroker({"kite": {"apiKey": "KEY", "apiSecret": "SEC"}}, fund_meta=Meta(), session=sess)
    assert b.login_status()["status"] == "NOT_CONNECTED"
    with pytest.raises(ApiError) as e:
        b.portfolio()
    assert e.value.code == "BROKER_NOT_CONNECTED"
    st = b.login_start()
    assert st["status"] == "PENDING_LOGIN" and st["loginUrl"] == "https://kite.zerodha.com/connect/login?v=3&api_key=KEY"
    assert st["brokerMode"] == "kite_connect" and st["sampleData"] is False
    done = b.login_complete("RT")
    assert done["status"] == "CONNECTED" and done["accountLabel"] == "Your Zerodha account (AB1234)"
    m, url, _, form, _h = sess.calls[0]
    assert (m, url) == ("POST", "https://api.kite.trade/session/token")
    assert form == {"api_key": "KEY", "request_token": "RT", "checksum": hashlib.sha256(b"KEYRTSEC").hexdigest()}
    assert "X-Kite-Version" in sess.headers and sess.headers["X-Kite-Version"] == "3"
    p = b.portfolio()
    assert p.source == "Your Zerodha account" and p.idleCashInr == 42350.75 and p.sampleData is False
    assert [s["symbol"] for s in p.stocks] == ["TCS", "NEWBUY", "ITC"] and p.funds[0]["schemeCode"] == "900301"
    assert p.unmatched[0]["isin"] == "INF000X01ABC"
    assert b.historical("TCS", date(2026, 1, 1), date(2026, 10, 30)) == [(date(2026, 10, 30), 4.5, 6)]
    assert b.login_status()["status"] == "CONNECTED"
    methods = {(c[0], c[1].replace("https://api.kite.trade", "")) for c in sess.calls}
    assert all(mm in ("GET", "POST", "DELETE") for mm, _ in methods) and not any("/orders" in pp for _, pp in methods)
    out = b.logout()
    assert out["status"] == "NOT_CONNECTED" and out["loginUrl"] is None
    assert sess.calls[-1][0] == "DELETE" and sess.calls[-1][2]["access_token"] == "AT"
    with pytest.raises(ApiError):
        b.portfolio()


def test_kite_connect_token_expiry_and_errors():
    def h(method, url, params, data, headers):
        if url.endswith("/session/token"):
            return FResp(js={"status": "success", "data": {"access_token": "AT", "user_id": "U"}})
        return FResp(403, js={"status": "error", "error_type": "TokenException", "message": "expired AT"})
    b = kc.KiteConnectBroker({"kite": {"apiKey": "KEY", "apiSecret": "SEC"}}, session=FSession(h))
    b.login_complete("RT")
    with pytest.raises(ApiError) as e:
        b.portfolio()
    assert e.value.code == "BROKER_NOT_CONNECTED" and "AT" not in e.value.message
    assert b.login_status()["status"] == "NOT_CONNECTED"
    with pytest.raises(ApiError) as e2:
        kc.KiteConnectBroker({"kite": {}}).login_start()
    assert e2.value.code == "BAD_REQUEST"
    with pytest.raises(ApiError):
        kc.KiteConnectBroker({"kite": {"apiKey": "k", "apiSecret": "s"}}).login_complete("")

    import requests

    class Boom:
        headers = {}

        def request(self, *a, **k):
            raise requests.ConnectionError("x KEY SEC")
    bb = kc.KiteConnectBroker({"kite": {"apiKey": "KEY", "apiSecret": "SEC"}}, session=Boom())
    with pytest.raises(ApiError) as e3:
        bb.login_complete("RT")
    assert e3.value.code == "UPSTREAM_UNAVAILABLE" and "SEC" not in json.dumps(e3.value.body())


def test_kite_connect_login_complete_forbidden_paths_untouched():
    sess = FSession(kite_handler)
    b = kc.KiteConnectBroker({"kite": {"apiKey": "KEY", "apiSecret": "SEC"}}, session=sess)
    b.login_complete("RT")
    for m, p in (("POST", "/orders/regular"), ("PUT", "/orders/regular/1"), ("DELETE", "/orders/regular/1"),
                 ("POST", "/gtt/triggers"), ("DELETE", "/gtt/triggers/3")):
        with pytest.raises(ApiError) as e:
            b._request(m, p)
        assert e.value.code == "BROKER_FORBIDDEN_CALL"
    assert len(sess.calls) == 1  # only the session exchange hit the transport


# ---- MCP pure helpers
class TC:
    def __init__(self, text):
        self.text = text


class Res:
    def __init__(self, text="", sc=None, err=False):
        self.content, self.structured_content, self.is_error = [TC(text)], sc, err


def test_mcp_helpers():
    assert km.first_url("Open https://kite.zerodha.com/connect/login?api_key=x&v=3 to log in.") == \
        "https://kite.zerodha.com/connect/login?api_key=x&v=3"
    assert km.first_url("no link") is None
    assert km.parse_tool_payload(Res('{"a": 1}')) == {"a": 1}
    assert km.parse_tool_payload(Res('Holdings: [{"a": 1}] done')) == [{"a": 1}]
    assert km.parse_tool_payload(Res("plain")) == "plain"
    assert km.parse_tool_payload(Res("", sc={"result": [1]})) == [1]
    assert km.profile_label({"data": {"user_id": "AB1234"}}) == "Your Zerodha account (AB1234)"
    assert km.looks_like_auth_error("Please login first") and not km.looks_like_auth_error('{"user_id": "AB1"}')
    schema = {"properties": {"instrument_token": {}, "from": {}, "to": {}, "interval": {}}}
    assert km.pick_args(schema, {"token": 1, "from": "a", "to": "b", "interval": "day"}) == \
        {"instrument_token": 1, "from": "a", "to": "b", "interval": "day"}
    assert km.pick_args(None, {"token": 1, "from": "a"}) == {"instrument_token": 1, "from_date": "a"}
    assert km.find_nse_token([{"tradingsymbol": "TCS", "exchange": "NSE", "instrument_token": "11"}], "tcs") == 11


# ---- MCP against a loopback server
def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture()
def loopback_mcp(monkeypatch):
    import uvicorn
    from mcp.server.mcpserver import MCPServer

    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(k, raising=False)
    state = {"logged_in": False, "calls": []}
    srv = MCPServer("fake-kite")

    @srv.tool()
    def login() -> str:
        state["calls"].append("login")
        return "Please open https://kite.zerodha.com/connect/login?api_key=abc&v=3 to log in."

    @srv.tool()
    def get_profile() -> str:
        state["calls"].append("get_profile")
        if not state["logged_in"]:
            raise ValueError("Please login first")
        return json.dumps({"user_id": "AB1234"})

    @srv.tool()
    def get_holdings() -> str:
        state["calls"].append("get_holdings")
        return json.dumps(HOLDINGS["data"])

    @srv.tool()
    def get_mf_holdings() -> str:
        state["calls"].append("get_mf_holdings")
        return json.dumps(MF["data"])

    @srv.tool()
    def get_margins() -> str:
        state["calls"].append("get_margins")
        return json.dumps(MARGINS["data"])

    @srv.tool()
    def place_order() -> str:
        state["calls"].append("place_order")
        return "ORDER PLACED"

    port = _free_port()
    app = srv.streamable_http_app(host="127.0.0.1")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started
    yield f"http://127.0.0.1:{port}/mcp", state
    server.should_exit = True
    th.join(timeout=5)


def test_mcp_session_flow_on_loopback(loopback_mcp):
    url, state = loopback_mcp
    b = km.KiteMcpBroker({"kite": {"mcpUrl": url, "loginTimeoutSeconds": 300}}, fund_meta=Meta())
    try:
        assert b.login_status()["status"] == "NOT_CONNECTED"
        with pytest.raises(ApiError) as e:
            b.portfolio()
        assert e.value.code == "BROKER_NOT_CONNECTED"
        st = b.login_start()
        assert st["status"] == "PENDING_LOGIN" and st["loginUrl"].startswith("https://kite.zerodha.com/connect/login")
        assert b.login_status()["status"] == "PENDING_LOGIN"  # session stays open across requests
        state["logged_in"] = True
        s2 = b.login_status()
        assert s2["status"] == "CONNECTED" and s2["accountLabel"] == "Your Zerodha account (AB1234)"
        p = b.portfolio()
        assert [s["symbol"] for s in p.stocks] == ["TCS", "NEWBUY", "ITC"] and p.idleCashInr == 42350.75
        assert p.funds[0]["schemeCode"] == "900301" and p.unmatched[0]["isin"] == "INF000X01ABC"
        with pytest.raises(ApiError) as fe:
            b._call_tool("place_order", {})
        assert fe.value.code == "BROKER_FORBIDDEN_CALL"
        assert "place_order" not in state["calls"]  # never reached the server
        with pytest.raises(ApiError):
            b.login_complete("x")
    finally:
        out = b.logout()
    assert out["status"] == "NOT_CONNECTED" and b._thread is None


def test_mcp_unreachable_gives_upstream_error():
    b = km.KiteMcpBroker({"kite": {"mcpUrl": f"http://127.0.0.1:{_free_port()}/mcp"}})
    km.START_TIMEOUT = 10.0
    with pytest.raises(ApiError) as e:
        b.login_start()
    assert e.value.code == "UPSTREAM_UNAVAILABLE"
    assert b.login_status()["status"] == "NOT_CONNECTED"
