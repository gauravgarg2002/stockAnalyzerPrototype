"""Broker adapter: official Kite Connect REST API (read-only).

Every request passes through broker_guard.assert_allowed_kite_connect BEFORE any network I/O.
Key and secret come from config only; the access token lives in memory only; secrets are never logged
or placed in error details. Importing this module performs no network I/O.

UNVERIFIED AGAINST LIVE SERVICE: response field names follow Kite Connect's public documentation
(holdings: tradingsymbol, exchange, isin, quantity, t1_quantity, average_price, last_price; mf/holdings:
tradingsymbol(ISIN), fund, quantity, average_price, last_price; margins: equity.available.live_balance;
candles: [timestamp, o, h, l, c, v]).
"""
from __future__ import annotations

import csv
import hashlib
import io
import threading
from datetime import date, datetime
from typing import Any

import requests

from ..errors import ApiError
from . import broker_guard
from .base import BrokerPortfolio, PricePoint
from .broker_extras import (NIFTY50_TOKEN, build_activity, clean_symbol, count_trades, map_gtts, map_positions,
                            map_quote, pick_quote_row, summarize_orders, unavailable_quote, unwrap_rows)
from .http_util import DEFAULT_TIMEOUT, make_session, today_ist, unavailable

API_BASE = "https://api.kite.trade"
LOGIN_BASE = "https://kite.zerodha.com/connect/login"
SOURCE = "Your Zerodha account"
NOT_CONNECTED_MSG = "Not connected to Zerodha Kite yet."


# ---------- pure mapping helpers (shared with broker_kite_mcp) ----------

def _f(v: Any) -> float | None:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def map_stock_holdings(rows: list[dict]) -> list[dict]:
    """-> [{symbol, isin, quantity, avgPrice, lastPrice, firstBuyDate}]; zero quantity (incl. t1) skipped."""
    out: dict[str, dict] = {}
    for r in rows:
        qty = (_f(r.get("quantity")) or 0.0) + (_f(r.get("t1_quantity")) or 0.0)
        if qty <= 0:
            continue
        sym = clean_symbol(str(r.get("tradingsymbol") or r.get("symbol") or ""))
        if not sym:
            continue
        avg = _f(r.get("average_price"))
        last = _f(r.get("last_price"))
        cur = out.get(sym)
        if cur is None:
            out[sym] = {"symbol": sym, "isin": r.get("isin"), "quantity": qty, "avgPrice": avg,
                        "lastPrice": last, "firstBuyDate": None}
        else:  # same stock on two exchanges/rows: merge with quantity-weighted average
            tot = cur["quantity"] + qty
            if cur["avgPrice"] is not None and avg is not None:
                cur["avgPrice"] = round((cur["avgPrice"] * cur["quantity"] + avg * qty) / tot, 4)
            cur["quantity"] = tot
            cur["lastPrice"] = cur["lastPrice"] if cur["lastPrice"] is not None else last
    for v in out.values():
        if v["quantity"] == int(v["quantity"]):
            v["quantity"] = int(v["quantity"])
    return list(out.values())


def map_mf_holdings(rows: list[dict], fund_meta: Any) -> tuple[list[dict], list[dict]]:
    """-> (funds, unmatched). The ISIN is `tradingsymbol` in Kite's mf/holdings."""
    funds: dict[str, dict] = {}
    unmatched: list[dict] = []
    for r in rows:
        units = _f(r.get("quantity"))
        if not units or units <= 0:
            continue
        isin = str(r.get("isin") or r.get("tradingsymbol") or "").strip().upper() or None
        name = str(r.get("fund") or r.get("name") or isin or "").strip()
        meta = None
        if fund_meta is not None and isin:
            try:
                meta = fund_meta.find_by_isin(isin)
            except Exception:
                meta = None
        if meta is None:
            unmatched.append({"name": name, "isin": isin, "reason": "Fund not found in fund list."})
            continue
        avg = _f(r.get("average_price"))
        last = _f(r.get("last_price"))
        cur = funds.get(meta.schemeCode)
        if cur is None:
            funds[meta.schemeCode] = {"schemeCode": meta.schemeCode, "isin": isin, "name": meta.name,
                                      "units": units, "avgNav": avg, "lastNav": last, "firstBuyDate": None}
        else:  # several folios
            tot = cur["units"] + units
            if cur["avgNav"] is not None and avg is not None:
                cur["avgNav"] = round((cur["avgNav"] * cur["units"] + avg * units) / tot, 4)
            cur["units"] = round(tot, 3)
    return list(funds.values()), unmatched


def margins_cash(obj: Any) -> float | None:
    """equity.available.live_balance from a get_margins / GET /user/margins result."""
    if isinstance(obj, dict):
        d = obj.get("data") if isinstance(obj.get("data"), dict) else obj
        eq = d.get("equity") if isinstance(d, dict) else None
        if isinstance(eq, dict):
            av = eq.get("available")
            if isinstance(av, dict):
                v = _f(av.get("live_balance"))
                if v is not None:
                    return v
    return None


def parse_instruments_csv(text: str) -> dict[str, int]:
    """tradingsymbol -> instrument_token for NSE equities."""
    out: dict[str, int] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("exchange") == "NSE" and row.get("instrument_type") == "EQ":
            try:
                out[row["tradingsymbol"].upper()] = int(row["instrument_token"])
            except (KeyError, ValueError):
                continue
    return out


def parse_candles(obj: Any) -> list[PricePoint]:
    """{'data': {'candles': [[ts, o, h, l, c, v], ...]}} -> [(date, close, volume)] ascending."""
    candles = []
    if isinstance(obj, dict):
        d = obj.get("data") if isinstance(obj.get("data"), dict) else obj
        candles = d.get("candles") or []
    out: dict[date, PricePoint] = {}
    for c in candles:
        try:
            ts = str(c[0])[:10]
            d0 = date.fromisoformat(ts)
            out[d0] = (d0, float(c[4]), int(c[5]) if len(c) > 5 and c[5] is not None else None)
        except (ValueError, TypeError, IndexError):
            continue
    return [out[k] for k in sorted(out)]


def checksum(api_key: str, request_token: str, api_secret: str) -> str:
    return hashlib.sha256((api_key + request_token + api_secret).encode("utf-8")).hexdigest()


# ---------- adapter ----------

class KiteConnectBroker:
    mode = "kite_connect"

    def __init__(self, config: dict, fund_meta: Any = None, session: requests.Session | None = None):
        k = (config or {}).get("kite", {}) or {}
        self._api_key = str(k.get("apiKey") or "")
        self._api_secret = str(k.get("apiSecret") or "")
        self._base = API_BASE
        self._fund_meta = fund_meta
        self._session = session or make_session(headers={"X-Kite-Version": "3"})
        self._session.headers["X-Kite-Version"] = "3"
        self._access_token: str | None = None
        self._user_id: str | None = None
        self._tokens: dict[str, int] | None = None
        self._lock = threading.Lock()

    # -- guarded transport
    def _request(self, method: str, path: str, params: dict | None = None, data: dict | None = None,
                 authed: bool = True) -> Any:
        m, p = broker_guard.assert_allowed_kite_connect(method, path)  # raises BEFORE any I/O
        headers = {}
        if authed:
            if not self._access_token:
                raise ApiError("BROKER_NOT_CONNECTED", NOT_CONNECTED_MSG)
            headers["Authorization"] = f"token {self._api_key}:{self._access_token}"
        try:
            resp = self._session.request(m, self._base + p, params=params, data=data, headers=headers,
                                         timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise unavailable("Zerodha Kite could not be reached. Please try again in a moment.",
                              reason=type(e).__name__)
        if p == "/instruments/NSE" or p == "/instruments":
            if resp.status_code == 200:
                return resp.text
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code == 403 or (isinstance(body, dict) and body.get("error_type") == "TokenException"):
            self._access_token = None
            raise ApiError("BROKER_NOT_CONNECTED", "Your Zerodha session has ended. Please connect again.")
        if resp.status_code >= 400 or (isinstance(body, dict) and body.get("status") == "error"):
            msg = body.get("message") if isinstance(body, dict) else None
            raise unavailable("Zerodha Kite returned an error.", httpStatus=resp.status_code,
                              reason=str(msg)[:200] if msg else None)
        return body

    # -- login
    def _info(self, status: str, message: str, **extra: Any) -> dict:
        d = {"sampleData": False, "brokerMode": self.mode, "status": status, "message": message}
        d.update(extra)
        return d

    def login_start(self) -> dict:
        if not self._api_key or not self._api_secret:
            raise ApiError("BAD_REQUEST", "Kite Connect needs an API key and secret in the configuration file.")
        url = f"{LOGIN_BASE}?v=3&api_key={self._api_key}"
        return self._info("PENDING_LOGIN", "Waiting for you to finish logging in to Kite.", loginUrl=url)

    def _label(self) -> str:
        return f"Your Zerodha account ({self._user_id})" if self._user_id else "Your Zerodha account"

    def login_status(self) -> dict:
        if not self._access_token:
            return self._info("NOT_CONNECTED", NOT_CONNECTED_MSG, accountLabel=None)
        try:
            self._request("GET", "/user/profile")
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                return self._info("NOT_CONNECTED", NOT_CONNECTED_MSG, accountLabel=None)
            # transient failure: keep the session, report it as connected but unverified
        return self._info("CONNECTED", "Connected.", accountLabel=self._label())

    def login_complete(self, request_token: str) -> dict:
        if not request_token or not self._api_key or not self._api_secret:
            raise ApiError("BAD_REQUEST", "A request token and the Kite API key and secret are required.")
        form = {"api_key": self._api_key, "request_token": request_token,
                "checksum": checksum(self._api_key, request_token, self._api_secret)}
        body = self._request("POST", "/session/token", data=form, authed=False)
        d = (body or {}).get("data") if isinstance(body, dict) else None
        tok = d.get("access_token") if isinstance(d, dict) else None
        if not tok:
            raise unavailable("Zerodha Kite did not return a session. Please try connecting again.")
        with self._lock:
            self._access_token = tok
            self._user_id = d.get("user_id")
        return self._info("CONNECTED", "Connected.", accountLabel=self._label())

    def logout(self) -> dict:
        tok, self._access_token = self._access_token, None
        self._user_id = None
        if tok:
            try:  # best effort invalidate; allow-listed DELETE /session/token
                m, p = broker_guard.assert_allowed_kite_connect("DELETE", "/session/token")
                self._session.request(m, self._base + p, params={"api_key": self._api_key, "access_token": tok},
                                      timeout=DEFAULT_TIMEOUT)
            except Exception:
                pass
        return self._info("NOT_CONNECTED", "Disconnected. Imported holdings are kept.", loginUrl=None)

    # -- data
    def portfolio(self) -> BrokerPortfolio:
        if not self._access_token:
            raise ApiError("BROKER_NOT_CONNECTED", NOT_CONNECTED_MSG)
        holdings = self._request("GET", "/portfolio/holdings")
        stocks = map_stock_holdings(unwrap_rows(holdings))
        try:
            mf = self._request("GET", "/mf/holdings")
            funds, unmatched = map_mf_holdings(unwrap_rows(mf), self._fund_meta)
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
            funds, unmatched = [], []  # account without mutual fund access
        cash = None
        try:
            cash = margins_cash(self._request("GET", "/user/margins"))
        except ApiError as e:
            if e.code == "BROKER_NOT_CONNECTED":
                raise
        return BrokerPortfolio(source=SOURCE, asOf=today_ist().isoformat(), accountLabel=self._label(),
                               stocks=stocks, funds=funds, idleCashInr=cash, unmatched=unmatched, sampleData=False)

    def _token_for(self, symbol: str) -> int | None:
        if self._tokens is None:
            text = self._request("GET", "/instruments/NSE")
            self._tokens = parse_instruments_csv(text if isinstance(text, str) else "")
        return self._tokens.get(symbol.upper())

    def historical(self, symbol: str, start: date, end: date) -> list[PricePoint]:
        if not self._access_token:
            return []
        try:
            tok = self._token_for(symbol)
            if tok is None:
                return []
            body = self._request("GET", f"/instruments/historical/{tok}/day",
                                 params={"from": start.isoformat(), "to": end.isoformat()})
            return parse_candles(body)
        except ApiError:
            return []


    # -- extras (read-only): live quote, today's activity, index history
    def quote(self, symbol: str) -> dict:
        sym = symbol.strip().upper()
        if not self._access_token:
            return unavailable_quote(sym, "Connect your Zerodha account to see the live price.", False)
        try:
            row = pick_quote_row(self._request("GET", "/quote", params={"i": f"NSE:{sym}"}), sym)
        except ApiError:
            return unavailable_quote(sym, "Zerodha Kite did not return a price just now.", False)
        if row is None:
            return unavailable_quote(sym, "Zerodha Kite has no live price for this symbol.", False)
        return map_quote(row, sym, "NSE, live via your Zerodha account", False)

    def activity(self) -> dict:
        if not self._access_token:
            return build_activity(sample=False, connected=False, source=SOURCE, as_of=today_ist().isoformat(),
                                  positions=None, orders=None, trades=None, gtts=None)

        def part(path: str, mapper):
            try:
                return mapper(self._request("GET", path))
            except ApiError:
                return None

        return build_activity(sample=False, connected=True, source=SOURCE, as_of=today_ist().isoformat(),
                              positions=part("/portfolio/positions", map_positions), orders=part("/orders", summarize_orders),
                              trades=part("/trades", count_trades), gtts=part("/gtt/triggers", map_gtts))

    def index_history(self, index_id: str, start: date, end: date) -> list[PricePoint]:
        if index_id != "NIFTY50" or not self._access_token:
            return []
        try:
            body = self._request("GET", f"/instruments/historical/{NIFTY50_TOKEN}/day",
                                 params={"from": start.isoformat(), "to": end.isoformat()})
            return parse_candles(body)
        except ApiError:
            return []


def build(config: dict, deps: dict) -> KiteConnectBroker:
    return KiteConnectBroker(config, fund_meta=deps.get("fund_meta"))
