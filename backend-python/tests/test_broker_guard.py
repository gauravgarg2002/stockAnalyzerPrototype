import pytest

from app.adapters import broker_guard as g
from app.errors import ApiError

OK_CALLS = [("portfolio", m) for m in ("profile", "margins", "holdings", "positions")] + [
    ("market", m) for m in ("quote", "ltp", "ohlc", "historical", "search")] + [
    ("mutual_funds", "holdings"), ("gtt", "list"), ("session", "status")] + [
    ("orders", m) for m in ("list", "history", "trades", "all_trades")]


@pytest.mark.parametrize("tool,mode", OK_CALLS)
def test_mcp_read_modes_allowed(tool, mode):
    assert g.assert_allowed_mcp_tool(tool, {"mode": mode}) == tool


@pytest.mark.parametrize("tool,args", [
    ("orders", {"mode": "place"}), ("orders", {"mode": "modify"}), ("orders", {"mode": "cancel"}),
    ("orders", {"mode": "permissions"}), ("orders", {"mode": "approval_status"}),
    ("gtt", {"mode": "place"}), ("gtt", {"mode": "modify"}), ("gtt", {"mode": "delete"}),
    ("alerts", {"mode": "get"}), ("alerts", {"mode": "create"}), ("session", {"mode": "logout"}),
    ("market", {"mode": "option_chain"}), ("portfolio", {}), ("portfolio", None), ("portfolio", {"mode": 5}),
    ("portfolio", {"mode": "Holdings"}), ("help", {"key": "/"}), ("place_order", {"mode": "holdings"}),
    ("", {"mode": "list"}), (None, {"mode": "list"}), (5, {"mode": "list"}), ("orders ", {"mode": "list"})])
def test_mcp_forbidden(tool, args):
    with pytest.raises(ApiError) as e:
        g.assert_allowed_mcp_tool(tool, args)
    assert e.value.code == "BROKER_FORBIDDEN_CALL" and e.value.status == 403


@pytest.mark.parametrize("method,path", [
    ("GET", "/user/profile"), ("GET", "/user/margins"), ("GET", "/user/margins/equity"),
    ("GET", "/portfolio/holdings"), ("GET", "/portfolio/positions"), ("GET", "/mf/holdings"),
    ("GET", "/quote"), ("GET", "/quote/ltp"), ("GET", "/quote/ohlc"), ("GET", "/instruments"),
    ("GET", "/instruments/NSE"), ("GET", "/instruments/historical/738561/day"),
    ("GET", "/instruments/historical/738561/minute"), ("GET", "/orders"), ("GET", "/trades"),
    ("GET", "/gtt/triggers"), ("POST", "/session/token"), ("DELETE", "/session/token"),
    ("get", "/quote/ltp?i=NSE:INFY"), ("GET", "https://api.kite.trade/portfolio/holdings"),
])
def test_kite_connect_allowed(method, path):
    m, p = g.assert_allowed_kite_connect(method, path)
    assert m == method.upper() and p.startswith("/")


@pytest.mark.parametrize("method,path", [
    ("POST", "/orders/regular"), ("POST", "/orders"), ("PUT", "/orders/regular/123"),
    ("DELETE", "/orders/regular/123"), ("GET", "/orders/123"), ("POST", "/gtt/triggers"),
    ("PUT", "/gtt/triggers/9"), ("DELETE", "/gtt/triggers/9"), ("POST", "/orders/amo"),
    ("POST", "/portfolio/positions"), ("PUT", "/portfolio/positions"), ("GET", "/anything/else"),
    ("POST", "/portfolio/holdings/authorise"), ("POST", "/mf/orders"), ("GET", "/mf/orders"),
    ("POST", "/user/profile"), ("GET", "/portfolio/holdings/../../orders/regular"),
    ("GET", "/quote%2f..%2forders"), ("POST", "/session/token/x"), ("GET", "/instruments/historical/abc/day"),
    ("PATCH", "/orders"), ("POST", "//orders/regular"),
])
def test_kite_connect_forbidden(method, path):
    with pytest.raises(ApiError) as e:
        g.assert_allowed_kite_connect(method, path)
    assert e.value.code == "BROKER_FORBIDDEN_CALL" and e.value.status == 403
    assert e.value.body()["error"]["details"] is not None


def test_forbidden_error_does_no_network(monkeypatch):
    import requests

    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(requests.sessions.Session, "request", boom)
    from app.adapters.broker_kite_connect import KiteConnectBroker

    b = KiteConnectBroker({"kite": {"apiKey": "k", "apiSecret": "s"}})
    with pytest.raises(ApiError) as e:
        b._request("POST", "/orders/regular", data={"x": 1})
    assert e.value.code == "BROKER_FORBIDDEN_CALL"
    with pytest.raises(ApiError):
        b._request("DELETE", "/gtt/triggers/1")


def test_mcp_adapter_guard_before_io():
    from app.adapters.broker_kite_mcp import KiteMcpBroker

    b = KiteMcpBroker({"kite": {"mcpUrl": "https://mcp.kite.trade/mcp", "loginTimeoutSeconds": 5}})
    for tool, mode in (("orders", "place"), ("orders", "cancel"), ("gtt", "modify"), ("place_order", "x")):
        with pytest.raises(ApiError) as e:
            b._call_tool(tool, {"mode": mode})
        assert e.value.code == "BROKER_FORBIDDEN_CALL"
    assert b._thread is None  # no background thread / session was started
