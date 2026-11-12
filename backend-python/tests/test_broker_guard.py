import pytest

from app.adapters import broker_guard as g
from app.errors import ApiError

MCP_OK = ["login", "get_profile", "get_margins", "get_holdings", "get_mf_holdings", "get_positions",
          "get_quotes", "get_ltp", "get_ohlc", "get_historical_data", "search_instruments",
          "get_orders", "get_trades", "get_gtts"]


def test_mcp_allow_list_is_exact():
    assert sorted(g.MCP_ALLOWED_TOOLS) == sorted(MCP_OK)
    for t in MCP_OK:
        assert g.assert_allowed_mcp_tool(t) == t


@pytest.mark.parametrize("tool", ["place_order", "modify_order", "cancel_order", "place_gtt_order",
                                  "modify_gtt_order", "delete_gtt_order", "", "GET_HOLDINGS", "get_holdings ",
                                  "get_holdings;place_order", None, 5])
def test_mcp_forbidden(tool):
    with pytest.raises(ApiError) as e:
        g.assert_allowed_mcp_tool(tool)
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
    for tool in ("place_order", "cancel_order", "modify_gtt_order"):
        with pytest.raises(ApiError) as e:
            b._call_tool(tool, {})
        assert e.value.code == "BROKER_FORBIDDEN_CALL"
    assert b._thread is None  # no background thread / session was started
