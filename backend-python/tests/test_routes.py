import asyncio
import json

import pytest

from app import asgi_fallback
from app.routes import ROUTES

CONTRACT_ROUTES = [
    ("GET", "/internal/health"), ("GET", "/internal/search"), ("GET", "/internal/stocks/{symbol}/check"), ("POST", "/internal/funds/{schemeCode}/check"),
    ("GET", "/internal/compare"), ("GET", "/internal/glossary"), ("GET", "/internal/explain"), ("POST", "/internal/instruments/bundle"),
    ("POST", "/internal/prices/points"), ("POST", "/internal/broker/login/start"), ("GET", "/internal/broker/login/status"),
    ("POST", "/internal/broker/login/complete"), ("POST", "/internal/broker/logout"), ("GET", "/internal/broker/portfolio"),
    ("POST", "/internal/statements/parse"), ("POST", "/internal/narrate")]


def test_routes_equal_contract_list():
    assert sorted((r.method, r.path) for r in ROUTES) == sorted(CONTRACT_ROUTES)
    assert {r.kind for r in ROUTES} <= {"query", "json_body"}
    assert all(r.kind == "json_body" for r in ROUTES if r.path in ("/internal/narrate", "/internal/prices/points", "/internal/instruments/bundle", "/internal/statements/parse"))


async def _call(app, method, path, query="", body=None):
    raw = json.dumps(body).encode() if body is not None else b""
    sent = {}
    msgs = [{"type": "http.request", "body": raw, "more_body": False}]

    async def receive():
        return msgs.pop(0) if msgs else {"type": "http.disconnect"}

    async def send(m):
        if m["type"] == "http.response.start":
            sent["status"] = m["status"]
        elif m["type"] == "http.response.body":
            sent["body"] = sent.get("body", b"") + m.get("body", b"")

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path, "raw_path": path.encode(), "root_path": "",
             "scheme": "http", "query_string": query.encode(), "headers": [(b"content-type", b"application/json"), (b"host", b"test")],
             "server": ("test", 80), "client": ("c", 1)}
    await app(scope, receive, send)
    return sent["status"], json.loads(sent["body"])


def call(method, path, query="", body=None):
    return asyncio.run(_call(asgi_fallback.app, method, path, query, body))


def test_asgi_serves_every_route():
    assert call("GET", "/internal/health")[1]["status"] == "ok"
    st, b = call("GET", "/internal/search", "q=tata")
    assert st == 200 and len(b["results"]) == 2
    assert call("GET", "/internal/stocks/TCS/check")[0] == 200
    st, b = call("POST", "/internal/funds/900101/check", body={"amountInr": 100000, "amountBasis": "ILLUSTRATIVE", "userFunds": []})
    assert st == 200 and b["amount"]["display"] == "₹1 lakh"
    assert call("GET", "/internal/compare", "kind=STOCK&ids=TCS,INFY")[0] == 200
    assert len(call("GET", "/internal/glossary")[1]["terms"]) >= 40
    assert call("GET", "/internal/explain", "term=pe_ratio&kind=STOCK&id=TCS")[1]["typical"]["value"] == 25.1
    assert call("POST", "/internal/instruments/bundle", body={"stocks": ["TCS"], "funds": ["900101"]})[0] == 200
    assert call("POST", "/internal/prices/points", body={"items": []})[1]["items"] == []
    assert call("POST", "/internal/broker/login/start")[1]["status"] == "CONNECTED"
    assert call("GET", "/internal/broker/login/status")[1]["status"] == "CONNECTED"
    assert len(call("GET", "/internal/broker/portfolio")[1]["stocks"]) == 6
    assert call("POST", "/internal/broker/logout")[1]["status"] == "NOT_CONNECTED"
    assert call("POST", "/internal/broker/login/complete", body={"requestToken": "x"})[0] == 400
    st, b = call("POST", "/internal/narrate", body={"items": [{"key": "a", "templateId": "pf.summary.empty", "facts": {}}]})
    assert st == 200 and b["items"][0]["key"] == "a"
    assert call("POST", "/internal/statements/parse", body={"filename": "a", "fileBase64": "", "password": ""})[0] == 400


def test_error_shape_and_statuses():
    st, b = call("GET", "/internal/stocks/XYZ/check")
    assert st == 404 and b == {"error": {"code": "NOT_FOUND", "message": "No stock found for symbol XYZ.", "details": {"symbol": "XYZ"}}}
    st, b = call("GET", "/internal/search", "q=")
    assert st == 400 and b["error"]["code"] == "BAD_REQUEST" and b["error"]["details"] == {"param": "q"}
    st, b = call("GET", "/internal/broker/portfolio")
    assert st == 409 and b["error"]["code"] == "BROKER_NOT_CONNECTED" and b["error"]["details"] is None
    assert call("GET", "/internal/nothing")[0] == 404


def test_invalid_json_body_is_400():
    async def go():
        sent = {}
        msgs = [{"type": "http.request", "body": b"{bad", "more_body": False}]

        async def receive():
            return msgs.pop(0)

        async def send(m):
            if m["type"] == "http.response.start":
                sent["status"] = m["status"]
            else:
                sent["body"] = m.get("body", b"")
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "path": "/internal/narrate", "raw_path": b"/internal/narrate",
                 "root_path": "", "scheme": "http", "query_string": b"", "headers": [], "server": ("t", 80), "client": ("c", 1)}
        await asgi_fallback.app(scope, receive, send)
        return sent
    s = asyncio.run(go())
    assert s["status"] == 400 and json.loads(s["body"])["error"]["code"] == "BAD_REQUEST"


def test_main_module_is_wired_from_routes_source():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent / "app" / "main.py").read_text()
    assert "for _r in ROUTES" in src and "exception_handler(ApiError)" in src
    compile(src, "main.py", "exec")
