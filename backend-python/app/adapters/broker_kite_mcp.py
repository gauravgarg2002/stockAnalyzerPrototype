"""Broker adapter: MCP client to Zerodha's hosted Kite MCP server (streamable HTTP, read tools only).

Zerodha's hosted server needs no API key. It is an OAuth 2.1 protected resource: the MCP SDK registers a public
client, sends the user to the authorisation page (loginUrl), and exchanges the code we receive on our callback
(login_complete) for a bearer token that lives in memory only. Tokens cannot be refreshed, so expect a daily login.

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

def _leaf_errors(e: BaseException) -> list[BaseException]:
    """Flatten an ExceptionGroup into the errors that actually happened."""
    inner = getattr(e, "exceptions", None)
    if not inner:
        return [e]
    out: list[BaseException] = []
    for x in inner:
        out.extend(_leaf_errors(x))
    return out


def _reason(e: BaseException | None) -> str:
    if e is None:
        return "timeout"
    return ", ".join(dict.fromkeys(type(x).__name__ for x in _leaf_errors(e)))


def _log_error(where: str, e: BaseException) -> None:
    import sys
    for x in _leaf_errors(e):
        extra = getattr(x, "error", None) or getattr(x, "status_code", None) or getattr(x, "response", None)
        print(f"[kite-mcp] {where}: {type(x).__name__}: {str(x)[:500]} | {str(extra)[:500] if extra else ''}",
              file=sys.stderr, flush=True)

def _note(msg: str) -> None:
    import sys
    print(f"[kite-mcp] {msg}", file=sys.stderr, flush=True)


class _with_client:
    """Async context manager that closes the httpx client after the MCP transport that uses it."""

    def __init__(self, client: Any, transport: Any) -> None:
        self._client, self._transport = client, transport

    async def __aenter__(self) -> Any:
        await self._client.__aenter__()
        try:
            return await self._transport.__aenter__()
        except BaseException:
            await self._client.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *exc: Any) -> Any:
        try:
            return await self._transport.__aexit__(*exc)
        finally:
            await self._client.__aexit__(*exc)


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


_NSE_SERIES = ("-BE", "-BZ", "-SM", "-ST", "-EQ")  # same company, different NSE trading series


def find_instrument(payload: Any, symbol: str) -> dict | None:
    """Best match for a holding's symbol: NSE exact, then an NSE series variant (KRONOX-BE), then BSE."""
    rows = unwrap_rows(payload, "instruments", "results")
    sym = symbol.upper()
    best: tuple[int, dict] | None = None
    for r in rows:
        ts = str(r.get("tradingsymbol") or r.get("symbol") or "").upper()
        ex = str(r.get("exchange") or "NSE").upper()
        try:
            token = int(r.get("instrument_token") or r.get("token"))
        except (TypeError, ValueError):
            continue
        if ex == "NSE" and ts == sym:
            rank = 0
        elif ex == "NSE" and any(ts == sym + sfx for sfx in _NSE_SERIES):
            rank = 1
        elif ex == "BSE" and ts == sym:
            rank = 2
        else:
            continue
        if best is None or rank < best[0]:
            best = (rank, {"exchange": ex, "tradingsymbol": ts, "token": token, "name": r.get("name")})
    return best[1] if best else None


def find_nse_token(payload: Any, symbol: str) -> int | None:
    hit = find_instrument(payload, symbol)
    return hit["token"] if hit else None


def ltp_rows(payload: Any) -> dict[str, float]:
    """{'NSE:INFY': price} from a quote/ltp payload: a dict keyed by instrument, or a list of rows."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    out: dict[str, float] = {}
    if isinstance(data, dict):
        items = [(k, v) for k, v in data.items() if isinstance(v, dict)]
    elif isinstance(data, list):
        items = [(str(r.get("instrument") or r.get("id") or
                      f"{r.get('exchange', '')}:{r.get('tradingsymbol', '')}"), r) for r in data if isinstance(r, dict)]
    else:
        items = []
    for k, v in items:
        try:
            price = float(v.get("last_price"))
        except (TypeError, ValueError):
            continue
        if price > 0:
            out[str(k).upper()] = price
    return out


class _MemoryStorage:
    """OAuth token + registered-client store. In memory only: nothing about the login is written to disk."""

    def __init__(self) -> None:
        self.tokens: Any = None
        self.client_info: Any = None

    async def get_tokens(self) -> Any:
        return self.tokens

    async def set_tokens(self, tokens: Any) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> Any:
        return self.client_info

    async def set_client_info(self, client_info: Any) -> None:
        self.client_info = client_info


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
        self._instruments: dict[str, dict | None] = {}
        self._redirect_uri = str(k.get("redirectUrl") or "http://localhost:8080/api/connect/kite/callback")
        self._storage = _MemoryStorage()
        self._auth_url: str | None = None
        self._auth_event = threading.Event()
        # Kite rate-limits bursts (HTTP 429 drops the whole session): one call at a time, spaced out.
        self._call_lock = threading.Lock()
        self._min_gap_s = float(k.get("mcpMinGapSeconds", 0.4))
        self._last_call = 0.0
        self._retry_after = 0.0  # monotonic time before which we do not reconnect on our own
        self._code_future: Any = None

    # -- OAuth hooks (run on the session thread's event loop)
    def _build_auth(self) -> Any:
        from mcp.client.auth import OAuthClientProvider
        from mcp.shared.auth import OAuthClientMetadata

        meta = OAuthClientMetadata(client_name="Stock Analyzer (local prototype)", redirect_uris=[self._redirect_uri],
                                   grant_types=["authorization_code"], response_types=["code"],
                                   token_endpoint_auth_method="none")
        return OAuthClientProvider(server_url=self._url, client_metadata=meta, storage=self._storage,
                                   redirect_handler=self._on_redirect, callback_handler=self._on_callback)

    async def _on_redirect(self, url: str) -> None:
        self._code_future = asyncio.get_running_loop().create_future()
        self._auth_url = url
        self._auth_event.set()

    async def _on_callback(self) -> tuple[str, str | None]:
        return await asyncio.wait_for(self._code_future, self._timeout_s)

    # -- background session
    def _thread_main(self) -> None:
        try:
            asyncio.run(self._runner())
        except BaseException as e:  # noqa: BLE001 - surfaced through _start_error
            self._start_error = e
            _log_error("session", e)
        finally:
            self._session = None
            self._loop = None
            self._ready.set()

    async def _runner(self) -> None:
        from mcp import ClientSession

        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        auth = self._build_auth()
        try:
            from mcp.client.streamable_http import streamable_http_client
            from mcp.shared._httpx_utils import create_mcp_http_client
        except ImportError:  # older SDKs: the transport takes the auth object directly
            from mcp.client.streamable_http import streamablehttp_client

            transport = streamablehttp_client(self._url, auth=auth)
        else:
            http_client = create_mcp_http_client(auth=auth)
            transport = _with_client(http_client, streamable_http_client(self._url, http_client=http_client))
        async with transport as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                try:
                    tools = await session.list_tools()
                    self._tool_schemas = {t.name: (_attr(t, "input_schema", "inputSchema") or {}) for t in tools.tools}
                except Exception:
                    self._tool_schemas = {}
                import sys
                print(f"[kite-mcp] tools: {sorted(self._tool_schemas)}", file=sys.stderr, flush=True)
                self._session = session
                self._ready.set()
                await self._stop.wait()

    def _ensure_session(self) -> None:
        """Data calls never start a login: they need the session that login_start / login_complete opened."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive() and self._session is not None:
                return
        # The session dropped but today's login token is still in memory: reopen it quietly (never a new login).
        if self._storage.tokens is not None and self._auth_url is None:
            if time.monotonic() < self._retry_after:
                raise unavailable("Zerodha Kite is limiting requests. Please try again in a minute.")
            self._shutdown()
            self._begin()
            if self._session is not None:
                self._status = "CONNECTED"
                return
            needs_login = self._auth_url is not None
            self._shutdown()
            if needs_login:  # the token was rejected: the user has to sign in again
                self._storage.tokens = None
                self._status = "NOT_CONNECTED"
            else:
                self._retry_after = time.monotonic() + 60
                raise unavailable("Zerodha Kite could not be reached. Please try again in a minute.")
        raise ApiError("BROKER_NOT_CONNECTED", NOT_CONNECTED_MSG)

    def _begin(self) -> None:
        """Start the session thread and wait until it either connects or needs the user to authorise."""
        with self._lock:
            self._ready.clear()
            self._auth_event.clear()
            self._auth_url, self._code_future, self._start_error = None, None, None
            self._thread = threading.Thread(target=self._thread_main, name="kite-mcp", daemon=True)
            self._thread.start()
        end = time.monotonic() + START_TIMEOUT
        while time.monotonic() < end and not (self._ready.is_set() or self._auth_event.is_set()):
            time.sleep(0.05)

    def _shutdown(self) -> None:
        with self._lock:
            loop, stop, th, fut = self._loop, self._stop, self._thread, self._code_future
            if loop is not None and stop is not None:
                try:
                    loop.call_soon_threadsafe(stop.set)
                    if fut is not None:
                        loop.call_soon_threadsafe(fut.cancel)
                except RuntimeError:
                    pass
            if th is not None and th.is_alive() and th is not threading.current_thread():
                th.join(timeout=5)
            self._thread = None
            self._session = None
            self._loop = None
            self._auth_url, self._code_future = None, None

    # -- guarded tool call
    def _call_tool(self, name: str, arguments: dict | None = None) -> Any:
        broker_guard.assert_allowed_mcp_tool(name, arguments)  # raises BEFORE any I/O or thread start
        with self._call_lock:
            self._ensure_session()
            loop, session = self._loop, self._session
            if loop is None or session is None:
                raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.")
            wait = self._last_call + self._min_gap_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            fut = asyncio.run_coroutine_threadsafe(session.call_tool(name, arguments or {}), loop)
            try:
                return fut.result(timeout=CALL_TIMEOUT)
            except Exception as e:  # network drop, timeout, protocol error
                fut.cancel()
                _log_error(f"tool {name}", e)
                if type(e).__name__ == "McpError":  # the server answered; the session itself is fine
                    raise unavailable("Zerodha Kite returned an error.", tool=name)
                # Keep the login token: the next call reopens the session after a pause.
                self._shutdown()
                self._retry_after = time.monotonic() + 20
                raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.",
                                  reason=_reason(e))
            finally:
                self._last_call = time.monotonic()

    def _info(self, status: str, message: str, **extra: Any) -> dict:
        d = {"sampleData": False, "brokerMode": self.mode, "status": status, "message": message}
        d.update(extra)
        return d

    # -- login
    def login_start(self) -> dict:
        if self._session is not None and self._thread is not None and self._thread.is_alive():
            st = self.login_status()
            if st["status"] == "CONNECTED":
                return self._info("CONNECTED", "Connected.", loginUrl=None)
        self._shutdown()
        self._begin()
        if self._auth_url:
            self._status = "PENDING_LOGIN"
            self._login_started = time.monotonic()
            return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", loginUrl=self._auth_url)
        if self._session is not None:  # a token from an earlier login in this run was still valid
            st = self.login_status()
            return self._info(st["status"], st["message"], loginUrl=None)
        err = self._start_error
        self._shutdown()
        self._status = "NOT_CONNECTED"
        raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.", reason=_reason(err))

    def login_status(self) -> dict:
        if self._session is None and self._storage.tokens is not None and self._auth_url is None:
            try:
                self._ensure_session()  # today's token is still held: reopen the dropped session
            except ApiError as e:
                if e.code != "BROKER_NOT_CONNECTED":
                    return self._info("CONNECTED", "Connected. Zerodha Kite is busy; data will refresh shortly.",
                                      accountLabel=self._label)
        alive = self._thread is not None and self._thread.is_alive()
        if self._session is None:
            if alive and self._auth_url:
                if self._login_started is not None and time.monotonic() - self._login_started > self._timeout_s:
                    self._shutdown()
                    self._status = "FAILED"
                    return self._info("FAILED", "Login timed out. Please try connecting again.", accountLabel=None)
                return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", accountLabel=None)
            return self._info("NOT_CONNECTED", NOT_CONNECTED_MSG, accountLabel=None)
        if "portfolio" not in self._tool_schemas:  # unexpected server: the session itself is the proof
            self._status, self._label = "CONNECTED", "Your Zerodha account"
            return self._info("CONNECTED", "Connected.", accountLabel=self._label)
        res = self._call_tool("portfolio", {"mode": "profile"})
        text = result_text(res)
        if is_error(res) or (looks_like_auth_error(text) and profile_label(parse_tool_payload(res)) is None):
            self._status = "PENDING_LOGIN"
            return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", accountLabel=None)
        self._status = "CONNECTED"
        self._label = profile_label(parse_tool_payload(res)) or "Your Zerodha account"
        return self._info("CONNECTED", "Connected.", accountLabel=self._label)

    def login_complete(self, request_token: str, state: str | None = None) -> dict:
        """Hand the OAuth authorisation code (our callback's `code` + `state`) to the waiting session."""
        loop, fut = self._loop, self._code_future
        if not request_token or loop is None or fut is None or fut.done():
            raise ApiError("BAD_REQUEST", "No Kite login is waiting for a code. Start the connection again.")

        def deliver() -> None:
            if not fut.done():
                fut.set_result((request_token, state))

        loop.call_soon_threadsafe(deliver)
        end = time.monotonic() + START_TIMEOUT
        while time.monotonic() < end and self._session is None and self._thread is not None and self._thread.is_alive():
            time.sleep(0.05)
        if self._session is None:
            err = self._start_error
            self._shutdown()
            self._status = "NOT_CONNECTED"
            raise unavailable("Zerodha Kite did not accept the login. Please try connecting again.",
                              reason=_reason(err))
        return self.login_status()

    def logout(self) -> dict:
        self._shutdown()
        self._storage = _MemoryStorage()
        self._status, self._label, self._login_started = "NOT_CONNECTED", None, None
        return self._info("NOT_CONNECTED", "Disconnected. Imported holdings are kept.", loginUrl=None)

    # -- data
    def _require_connected(self) -> None:
        if self._status != "CONNECTED":
            raise ApiError("BROKER_NOT_CONNECTED", NOT_CONNECTED_MSG)

    def _data_call(self, name: str, arguments: dict | None = None) -> Any:
        res = self._call_tool(name, arguments or {})
        if is_error(res):
            if looks_like_auth_error(result_text(res)):
                self._status = "PENDING_LOGIN"
                raise ApiError("BROKER_NOT_CONNECTED", "Your Zerodha session has ended. Please connect again.")
            raise unavailable("Zerodha Kite returned an error.", tool=name)
        return parse_tool_payload(res)

    def _paged_rows(self, tool: str, base: dict, *keys: str, page: int = 500, max_pages: int = 10) -> list[dict]:
        rows: list[dict] = []
        for i in range(max_pages):
            got = unwrap_rows(self._data_call(tool, {**base, "from": i * page, "limit": page}), *keys)
            rows.extend(got)
            if len(got) < page:
                break
        return rows

    def portfolio(self) -> BrokerPortfolio:
        self._require_connected()
        holdings = self._paged_rows("portfolio", {"mode": "holdings", "type": "full"}, "holdings")
        stocks = map_stock_holdings(holdings)
        try:
            funds, unmatched = map_mf_holdings(
                unwrap_rows(self._data_call("mutual_funds", {"mode": "holdings"}), "holdings", "mf_holdings"),
                self._fund_meta)
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
            funds, unmatched = [], []
        cash = None
        try:
            cash = margins_cash(self._data_call("portfolio", {"mode": "margins"}))
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
        return BrokerPortfolio(source=SOURCE, asOf=today_ist().isoformat(), accountLabel=self._label,
                               stocks=stocks, funds=funds, idleCashInr=cash, unmatched=unmatched, sampleData=False)

    def _find_token(self, query: str, symbol: str) -> int | None:
        hit = self._instrument(symbol)
        return hit["token"] if hit else None

    def _instrument(self, symbol: str) -> dict | None:
        sym = symbol.strip().upper()
        if sym in self._instruments:
            return self._instruments[sym]
        args = {"mode": "search", "query": sym}
        if "verbosity" in ((self._tool_schemas.get("market") or {}).get("properties") or {}):
            args["verbosity"] = "compact"
        payload = parse_tool_payload(self._call_tool("market", args))
        hit = find_instrument(payload, sym)
        if hit is None:
            _note(f"search {sym!r}: no NSE or BSE match in {str(payload)[:500]}")
        self._instruments[sym] = hit
        return hit

    def bse_code(self, symbol: str) -> str | None:
        """BSE scrip code for a BSE-only holding (Kite packs it into the instrument token)."""
        if self._status != "CONNECTED":
            return None
        try:
            hit = self._instrument(symbol)
        except ApiError:
            return None
        return str(hit["token"] >> 8) if hit and hit["exchange"] == "BSE" else None

    def last_prices(self, symbols: list[str]) -> dict[str, float]:
        """Last traded price per symbol, for holdings that have no price history."""
        out: dict[str, float] = {}
        if self._status != "CONNECTED" or not symbols:
            return out
        try:
            keys = {}
            for s in symbols:
                hit = self._instrument(s)
                if hit:
                    keys[f"{hit['exchange']}:{hit['tradingsymbol']}"] = s.strip().upper()
            if keys:
                got = ltp_rows(self._data_call("market", {"mode": "ltp", "instruments": sorted(keys)}))
                for k, sym in keys.items():
                    if k in got:
                        out[sym] = got[k]
                if len(out) < len(keys):
                    _note(f"ltp: asked {sorted(keys)}, got {sorted(got)}")
        except ApiError as e:
            _note(f"ltp: {e.code} {e}")
        return out

    def _candles(self, token: int, start: date, end: date) -> list[PricePoint]:
        """Daily candles in chunks (Kite limits one request to about 2000 days)."""
        pts: dict[date, PricePoint] = {}
        cur = start
        while cur <= end:
            stop = min(end, date.fromordinal(cur.toordinal() + 1990))
            payload = parse_tool_payload(self._call_tool("market", {
                "mode": "historical", "instrument_token": token, "interval": "day",
                "from_date": cur.isoformat(), "to_date": stop.isoformat()}))
            got = parse_candles(payload)
            if not got:
                _note(f"historical token={token} {cur}..{stop}: no candles parsed from {str(payload)[:500]}")
            for p in got:
                pts[p[0]] = p
            cur = date.fromordinal(stop.toordinal() + 1)
        return [pts[k] for k in sorted(pts)]

    def historical(self, symbol: str, start: date, end: date) -> list[PricePoint]:
        if self._status != "CONNECTED":
            return []
        try:  # UNVERIFIED AGAINST LIVE SERVICE: the search result shape is parsed tolerantly
            token = self._find_token(symbol, symbol)
            return self._candles(token, start, end) if token is not None else []
        except ApiError as e:
            _note(f"historical {symbol}: {e.code} {e}")
            return []

    # -- extras (read-only): live quote, today's activity, index history
    def quote(self, symbol: str) -> dict:
        sym = symbol.strip().upper()
        if self._status != "CONNECTED":
            return unavailable_quote(sym, "Connect your Zerodha account to see the live price.", False)
        try:  # UNVERIFIED AGAINST LIVE SERVICE
            hit = self._instrument(sym)
            key = f"{hit['exchange']}:{hit['tradingsymbol']}" if hit else f"NSE:{sym}"
            row = pick_quote_row(self._data_call("market", {"mode": "quote", "instruments": [key]}), sym)
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                return unavailable_quote(sym, "Your Zerodha session has ended. Please connect again.", False)
            return unavailable_quote(sym, "Zerodha Kite did not return a price just now.", False)
        if row is None:
            return unavailable_quote(sym, "Zerodha Kite has no live price for this symbol.", False)
        return map_quote(row, sym, "NSE, live via your Zerodha account", False)

    def activity(self) -> dict:
        connected = self._status == "CONNECTED"

        def part(tool: str, args: dict, mapper):
            try:
                return mapper(self._data_call(tool, args))
            except ApiError:
                return None

        if not connected:
            return build_activity(sample=False, connected=False, source=SOURCE, as_of=today_ist().isoformat(),
                                  positions=None, orders=None, trades=None, gtts=None)
        return build_activity(sample=False, connected=True, source=SOURCE, as_of=today_ist().isoformat(),
                              positions=part("portfolio", {"mode": "positions"}, map_positions),
                              orders=part("orders", {"mode": "list"}, summarize_orders),
                              trades=part("orders", {"mode": "all_trades"}, count_trades),
                              gtts=part("gtt", {"mode": "list"}, map_gtts))

    def index_history(self, index_id: str, start: date, end: date) -> list[PricePoint]:
        if index_id != "NIFTY50" or self._status != "CONNECTED":
            return []
        try:  # UNVERIFIED AGAINST LIVE SERVICE
            token = NIFTY50_TOKEN
            try:
                args = {"mode": "search", "query": "NIFTY 50"}
                rows = unwrap_rows(parse_tool_payload(self._call_tool("market", args)), "instruments", "results")
                for r in rows:
                    if str(r.get("tradingsymbol") or "").upper() == "NIFTY 50" and r.get("instrument_token"):
                        token = int(r["instrument_token"])
                        break
            except (ApiError, TypeError, ValueError):
                pass
            return self._candles(token, start, end)
        except ApiError:
            return []


def build(config: dict, deps: dict) -> KiteMcpBroker:
    return KiteMcpBroker(config, fund_meta=deps.get("fund_meta"))
