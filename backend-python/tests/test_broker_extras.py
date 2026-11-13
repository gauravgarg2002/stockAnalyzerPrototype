"""Quote and account-activity mapping from Kite-shaped JSON (as documented), mock broker extras, and the new routes."""
from app.adapters import broker_extras as bx
from app.adapters.broker_mock import MockBroker
from app.verdict_scan import scan


def test_quote_from_kite_shape():
    payload = {"status": "success", "data": {"NSE:INFY": {
        "instrument_token": 408065, "last_price": 1412.95, "volume": 7360198, "net_change": 0,
        "timestamp": "2021-06-08 15:45:56", "ohlc": {"open": 1396, "high": 1421.75, "low": 1395.55, "close": 1389.65}}}}
    row = bx.pick_quote_row(payload, "INFY")
    q = bx.map_quote(row, "INFY", "NSE", False)
    assert q["available"] is True
    assert q["lastPriceDisplay"] == "₹1,412.95"
    assert q["changeDisplay"] == "+1.7%"  # net_change 0 -> computed from previous close
    assert q["volumeDisplay"] == "73,60,198"
    assert 0 < q["rangePosition"] < 1
    assert q["asOf"].startswith("2021-06-08T15:45:56")


def test_quote_row_missing():
    assert bx.pick_quote_row({"data": {}}, "INFY") is None
    assert bx.unavailable_quote("INFY", "x", False)["available"] is False


def test_positions_orders_trades_gtts():
    positions = {"data": {"net": [
        {"tradingsymbol": "SBIN", "exchange": "NSE", "product": "MIS", "quantity": 10, "average_price": 600.5, "last_price": 605, "pnl": 45},
        {"tradingsymbol": "ITC", "exchange": "NSE", "product": "CNC", "quantity": 0, "average_price": 0, "last_price": 450, "pnl": 12}],
        "day": []}}
    ps = bx.map_positions(positions)
    assert [p["symbol"] for p in ps] == ["SBIN"]  # closed positions are dropped
    assert ps[0]["pnlDisplay"] == "₹45"
    orders = {"data": [{"status": "COMPLETE"}, {"status": "OPEN"}, {"status": "TRIGGER PENDING"}, {"status": "REJECTED"}]}
    assert bx.summarize_orders(orders) == {"total": 4, "complete": 1, "open": 2, "cancelled": 1}
    assert bx.count_trades({"data": [{}, {}]}) == 2
    gtts = {"data": [
        {"id": 1, "type": "two-leg", "status": "active", "created_at": "2026-11-01 10:00:00",
         "condition": {"tradingsymbol": "INFY", "exchange": "NSE", "trigger_values": [1300, 1600], "last_price": 1450},
         "orders": [{"quantity": 5, "price": 1300}]},
        {"id": 2, "type": "single", "status": "triggered", "condition": {"tradingsymbol": "TCS", "trigger_values": [3000]}, "orders": []}]}
    gs = bx.map_gtts(gtts)
    assert len(gs) == 1 and gs[0]["kind"] == "TWO_LEG" and gs[0]["triggerDisplays"] == ["₹1,300.00", "₹1,600.00"]
    assert gs[0]["quantity"] == 5


def test_activity_sentences_have_no_verdict_words():
    a = bx.build_activity(sample=False, connected=True, source="x", as_of="2026-11-13", positions=[{"symbol": "A"}],
                          orders={"total": 2, "complete": 1, "open": 1, "cancelled": 0}, trades=1, gtts=[])
    texts = [s["text"] for s in a["sentences"]]
    assert len(texts) == 3
    for t in texts:
        assert scan(t) == [], t
    off = bx.build_activity(sample=False, connected=False, source="x", as_of="d", positions=None, orders=None, trades=None, gtts=None)
    assert off["connected"] is False and len(off["sentences"]) == 1


def test_mock_broker_extras():
    b = MockBroker()
    q = b.quote("TCS")
    assert q["sampleData"] is True and q["available"] is True and q["lastPrice"] > 0
    assert b.quote("NOPE")["available"] is False
    assert b.activity()["connected"] is False
    b.login_start()
    a = b.activity()
    assert a["connected"] is True and a["positions"] and a["gtts"]
    for s in a["sentences"]:
        assert scan(s["text"]) == []


def test_new_routes_registered():
    from app.routes import ROUTES
    paths = {(r.method, r.path) for r in ROUTES}
    assert ("GET", "/internal/broker/quote") in paths
    assert ("GET", "/internal/broker/activity") in paths
