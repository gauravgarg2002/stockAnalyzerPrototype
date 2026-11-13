"""Broker adapter: MCP client to Zerodha's hosted Kite MCP server (streamable HTTP, read tools only).

The MCP session must stay open across requests, so it lives in a dedicated background thread with its own
asyncio/anyio event loop. Every tool call passes through broker_guard.assert_allowed_mcp_tool BEFORE any
network I/O. Importing this module performs no network I/O (the `mcp` SDK is imported lazily).

UNVERIFIED AGAINST LIVE SERVICE: tool argument names for get_historical_data/search_instruments (picked from the
server's advertised input schema at runtime) and the exact text/JSON shape of tool results (parsed tolerantly by
parse_tool_payload, map_* helpers shared with broker_kite_connect).
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from datetime import date
from typing import Any

from ..errors import ApiError
from . import broker_guard
from .base import BrokerPortfolio, PricePoint
from .broker_extras import (NIFTY50_TOKEN, build_activity, count_trades, map_gtts, map_positions, map_quote,
                            pick_quote_row, summarize_orders, unavailable_quote)
from .broker_kite_connect import (map_mf_holdings, map_stock_holdings, margins_cash, parse_candles,
                                  unwrap_rows)
from .http_util import today_ist, unavailable

SOURCE = "Your Zerodha account"
NOT_CONNECTED_MSG = "Not connected to Zerodha Kite yet."
_URL_RE = re.compile(r"https?://[^\s)\]\">'<]+")
_AUTH_WORDS = ("login", "log in", "logged in", "unauthor", "authenticat", "session", "token", "expired", "forbidden")
CALL_TIMEOUT = 45.0
START_TIMEOUT = 30.0


# ---------- pure helpers ----------

def _attr(obj: Any, *names: str) -> Any:
    """SDK v2 uses snake_case attributes, v1 camelCase; accept both."""
    for n in names:
        v = getattr(obj, n, None)
        if v is not None:
            return v
    return None


def is_error(result: Any) -> bool:
    return bool(_attr(result, "is_error", "isError"))


def result_text(result: Any) -> str:
    parts = []
    for c in getattr(result, "content", None) or []:
        t = getattr(c, "text", None)
        if isinstance(t, str):
            parts.append(t)
    return "\n".join(parts)


def first_url(text: str) -> str | None:
    m = _URL_RE.search(text or "")
    return m.group(0).rstrip(".,;") if m else None


def parse_tool_payload(result: Any) -> Any:
    """Prefer structuredContent; else JSON found in the text content; else the raw text."""
    sc = _attr(result, "structured_content", "structuredContent")
    if sc:
        if isinstance(sc, dict) and set(sc) == {"result"}:
            sc = sc["result"]
        if isinstance(sc, str):  # a tool that returns a JSON string
            try:
                return json.loads(sc)
            except ValueError:
                return sc
        return sc
    text = result_text(result)
    try:
        return json.loads(text)
    except ValueError:
        pass
    pairs = sorted((text.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if text.find(o) >= 0)
    for a, _o, closer in pairs:  # try the earliest opening bracket first
        b = text.rfind(closer)
        if a < b:
            try:
                return json.loads(text[a:b + 1])
            except ValueError:
                continue
    return text


def looks_like_auth_error(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in _AUTH_WORDS)


def profile_label(payload: Any) -> str | None:
    d = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
    if isinstance(d, dict):
        uid = d.get("user_id") or d.get("userId") or d.get("user_shortname")
        if uid:
            return f"Your Zerodha account ({uid})"
    return None


def pick_args(schema: dict | None, wanted: dict[str, Any]) -> dict[str, Any]:
    """Map our logical argument names to the tool's advertised property names by fuzzy match.
    wanted keys: 'token', 'from', 'to', 'interval', 'query'. Falls back to Kite's documented names."""
    defaults = {"token": "instrument_token", "from": "from_date", "to": "to_date", "interval": "interval",
                "query": "query"}
    props = list(((schema or {}).get("properties") or {}).keys())
    out: dict[str, Any] = {}
    for logical, value in wanted.items():
        name = defaults[logical]
        for p in props:
            pl = p.lower()
            if logical == "token" and "token" in pl:
                name = p
            elif logical == "from" and ("from" in pl or "start" in pl):
                name = p
            elif logical == "to" and (pl in ("to", "to_date", "end", "end_date") or pl.startswith("to_")
                                       or "end" in pl):
                name = p
            elif logical == "interval" and ("interval" in pl or "timeframe" in pl):
                name = p
            elif logical == "query" and pl in ("query", "q", "search", "name", "symbol", "tradingsymbol"):
                name = p
        out[name] = value
    return out


def find_nse_token(payload: Any, symbol: str) -> int | None:
    rows = unwrap_rows(payload, "instruments", "results")
    sym = symbol.upper()
    for r in rows:
        ts = str(r.get("tradingsymbol") or r.get("symbol") or "").upper()
        ex = str(r.get("exchange") or "NSE").upper()
        if ts == sym and ex == "NSE":
            try:
                return int(r.get("instrument_token") or r.get("token"))
            except (TypeError, ValueError):
                continue
    return None


# ---------- adapter ----------

class KiteMcpBroker:
    mode = "kite_mcp"

    def __init__(self, config: dict, fund_meta: Any = None):
        k = (config or {}).get("kite", {}) or {}
        self._url = str(k.get("mcpUrl") or "https://mcp.kite.trade/mcp")
        self._timeout_s = float(k.get("loginTimeoutSeconds") or 300)
        self._fund_meta = fund_meta
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: Any = None
        self._stop: asyncio.Event | None = None
        self._ready = threading.Event()
        self._start_error: BaseException | None = None
        self._lock = threading.RLock()
        self._status = "NOT_CONNECTED"
        self._label: str | None = None
        self._login_started: float | None = None
        self._tool_schemas: dict[str, dict] = {}

    # -- background session
    def _thread_main(self) -> None:
        try:
            asyncio.run(self._runner())
        except BaseException as e:  # noqa: BLE001 - surfaced through _start_error
            self._start_error = e
        finally:
            self._session = None
            self._loop = None
            self._ready.set()

    async def _runner(self) -> None:
        from mcp import ClientSession

        try:
            from mcp.client.streamable_http import streamable_http_client as open_stream
        except ImportError:  # older SDKs
            from mcp.client.streamable_http import streamablehttp_client as open_stream  # type: ignore

        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        async with open_stream(self._url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                try:
                    tools = await session.list_tools()
                    self._tool_schemas = {t.name: (_attr(t, "input_schema", "inputSchema") or {}) for t in tools.tools}
                except Exception:
                    self._tool_schemas = {}
                self._session = session
                self._ready.set()
                await self._stop.wait()

    def _ensure_session(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive() and self._session is not None:
                return
            self._ready.clear()
            self._start_error = None
            self._thread = threading.Thread(target=self._thread_main, name="kite-mcp", daemon=True)
            self._thread.start()
        if not self._ready.wait(START_TIMEOUT) or self._session is None:
            self._shutdown()
            raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.",
                              reason=type(self._start_error).__name__ if self._start_error else "timeout")

    def _shutdown(self) -> None:
        with self._lock:
            loop, stop, th = self._loop, self._stop, self._thread
            if loop is not None and stop is not None:
                try:
                    loop.call_soon_threadsafe(stop.set)
                except RuntimeError:
                    pass
            if th is not None and th.is_alive() and th is not threading.current_thread():
                th.join(timeout=5)
            self._thread = None
            self._session = None
            self._loop = None

    # -- guarded tool call
    def _call_tool(self, name: str, arguments: dict | None = None) -> Any:
        broker_guard.assert_allowed_mcp_tool(name)  # raises BEFORE any I/O or thread start
        self._ensure_session()
        loop, session = self._loop, self._session
        if loop is None or session is None:
            raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.")
        fut = asyncio.run_coroutine_threadsafe(session.call_tool(name, arguments or {}), loop)
        try:
            return fut.result(timeout=CALL_TIMEOUT)
        except Exception as e:  # network drop, timeout, protocol error
            fut.cancel()
            self._shutdown()
            self._status = "NOT_CONNECTED" if self._status != "PENDING_LOGIN" else self._status
            raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.",
                              reason=type(e).__name__)

    def _info(self, status: str, message: str, **extra: Any) -> dict:
        d = {"sampleData": False, "brokerMode": self.mode, "status": status, "message": message}
        d.update(extra)
        return d

    # -- login
    def login_start(self) -> dict:
        res = self._call_tool("login", {})
        text = result_text(res)
        url = first_url(text)
        if url is None and not is_error(res):
            # already logged in on this MCP session? confirm with the profile
            st = self.login_status()
            if st["status"] == "CONNECTED":
                return self._info("CONNECTED", "Connected.", loginUrl=None)
        if url is None:
            raise unavailable("Zerodha Kite did not give a login link. Please try again.")
        self._status = "PENDING_LOGIN"
        self._login_started = time.monotonic()
        return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", loginUrl=url)

    def login_status(self) -> dict:
        if self._thread is None or self._session is None:
            return self._info("NOT_CONNECTED", NOT_CONNECTED_MSG, accountLabel=None)
        res = self._call_tool("get_profile", {})
        text = result_text(res)
        if is_error(res) or (looks_like_auth_error(text) and profile_label(parse_tool_payload(res)) is None):
            if self._login_started is not None and time.monotonic() - self._login_started > self._timeout_s:
                self._status = "FAILED"
                return self._info("FAILED", "Login timed out. Please try connecting again.", accountLabel=None)
            self._status = "PENDING_LOGIN"
            return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", accountLabel=None)
        self._status = "CONNECTED"
        self._label = profile_label(parse_tool_payload(res)) or "Your Zerodha account"
        return self._info("CONNECTED", "Connected.", accountLabel=self._label)

    def login_complete(self, request_token: str) -> dict:
        raise ApiError("BAD_REQUEST", "This connection mode does not use a request token.")

    def logout(self) -> dict:
        self._shutdown()
        self._status, self._label, self._login_started = "NOT_CONNECTED", None, None
        return self._info("NOT_CONNECTED", "Disconnected. Imported holdings are kept.", loginUrl=None)

    # -- data
    def _require_connected(self) -> None:
        if self._status != "CONNECTED" or self._session is None:
            raise ApiError("BROKER_NOT_CONNECTED", NOT_CONNECTED_MSG)

    def _data_call(self, name: str, arguments: dict | None = None) -> Any:
        res = self._call_tool(name, arguments or {})
        if is_error(res):
            if looks_like_auth_error(result_text(res)):
                self._status = "PENDING_LOGIN"
                raise ApiError("BROKER_NOT_CONNECTED", "Your Zerodha session has ended. Please connect again.")
            raise unavailable("Zerodha Kite returned an error.", tool=name)
        return parse_tool_payload(res)

    def portfolio(self) -> BrokerPortfolio:
        self._require_connected()
        holdings = self._data_call("get_holdings")
        stocks = map_stock_holdings(unwrap_rows(holdings, "holdings"))
        try:
            funds, unmatched = map_mf_holdings(unwrap_rows(self._data_call("get_mf_holdings"), "holdings", "mf_holdings"),
                                               self._fund_meta)
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
            funds, unmatched = [], []
        cash = None
        try:
            cash = margins_cash(self._data_call("get_margins"))
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
        return BrokerPortfolio(source=SOURCE, asOf=today_ist().isoformat(), accountLabel=self._label,
                               stocks=stocks, funds=funds, idleCashInr=cash, unmatched=unmatched, sampleData=False)

    def historical(self, symbol: str, start: date, end: date) -> list[PricePoint]:
        if self._status != "CONNECTED" or self._session is None:
            return []
        try:  # UNVERIFIED AGAINST LIVE SERVICE (argument names come from the advertised schema)
            q = pick_args(self._tool_schemas.get("search_instruments"), {"query": symbol})
            token = find_nse_token(parse_tool_payload(self._call_tool("search_instruments", q)), symbol)
            if token is None:
                return []
            a = pick_args(self._tool_schemas.get("get_historical_data"),
                          {"token": token, "from": start.isoformat(), "to": end.isoformat(), "interval": "day"})
            payload = parse_tool_payload(self._call_tool("get_historical_data", a))
            pts = parse_candles(payload if isinstance(payload, dict) else {"candles": payload})
            return pts
        except ApiError:
            return []


    # -- extras (read-only): live quote, today's activity, index history
    def _arg_name(self, tool: str, needle: str, default: str) -> str:
        props = ((self._tool_schemas.get(tool) or {}).get("properties") or {}).keys()
        return next((p for p in props if needle in p.lower()), default)

    def quote(self, symbol: str) -> dict:
        sym = symbol.strip().upper()
        if self._status != "CONNECTED" or self._session is None:
            return unavailable_quote(sym, "Connect your Zerodha account to see the live price.", False)
        try:  # UNVERIFIED AGAINST LIVE SERVICE: argument name taken from the advertised schema
            arg = self._arg_name("get_quotes", "instrument", "instruments")
            row = pick_quote_row(self._data_call("get_quotes", {arg: [f"NSE:{sym}"]}), sym)
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                return unavailable_quote(sym, "Your Zerodha session has ended. Please connect again.", False)
            return unavailable_quote(sym, "Zerodha Kite did not return a price just now.", False)
        if row is None:
            return unavailable_quote(sym, "Zerodha Kite has no live price for this symbol.", False)
        return map_quote(row, sym, "NSE, live via your Zerodha account", False)

    def activity(self) -> dict:
        connected = self._status == "CONNECTED" and self._session is not None

        def part(tool: str, mapper):
            try:
                return mapper(self._data_call(tool))
            except ApiError:
                return None

        if not connected:
            return build_activity(sample=False, connected=False, source=SOURCE, as_of=today_ist().isoformat(),
                                  positions=None, orders=None, trades=None, gtts=None)
        return build_activity(sample=False, connected=True, source=SOURCE, as_of=today_ist().isoformat(),
                              positions=part("get_positions", map_positions), orders=part("get_orders", summarize_orders),
                              trades=part("get_trades", count_trades), gtts=part("get_gtts", map_gtts))

    def index_history(self, index_id: str, start: date, end: date) -> list[PricePoint]:
        if index_id != "NIFTY50" or self._status != "CONNECTED" or self._session is None:
            return []
        try:  # UNVERIFIED AGAINST LIVE SERVICE
            token = NIFTY50_TOKEN
            try:
                q = pick_args(self._tool_schemas.get("search_instruments"), {"query": "NIFTY 50"})
                rows = unwrap_rows(parse_tool_payload(self._call_tool("search_instruments", q)), "instruments", "results")
                for r in rows:
                    if str(r.get("tradingsymbol") or "").upper() == "NIFTY 50" and r.get("instrument_token"):
                        token = int(r["instrument_token"])
                        break
            except (ApiError, TypeError, ValueError):
                pass
            a = pick_args(self._tool_schemas.get("get_historical_data"),
                          {"token": token, "from": start.isoformat(), "to": end.isoformat(), "interval": "day"})
            payload = parse_tool_payload(self._call_tool("get_historical_data", a))
            return parse_candles(payload if isinstance(payload, dict) else {"candles": payload})
        except ApiError:
            return []


def build(config: dict, deps: dict) -> KiteMcpBroker:
    return KiteMcpBroker(config, fund_meta=deps.get("fund_meta"))
