"""Read-only extras from the broker: a live quote for one stock, and today's account activity
(open positions, today's orders and trades, price triggers). Pure mapping helpers shared by kite_mcp,
kite_connect and mock, so the response shape is identical whatever the source.

UNVERIFIED AGAINST LIVE SERVICE: field names follow Kite Connect's documented JSON (quote: last_price, ohlc,
volume, net_change, timestamp; positions: net[]; orders: status; gtt: type, condition.trigger_values,
orders[].quantity). The MCP server is assumed to return the same JSON inside its text result.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ..formatting import format_count, format_inr, format_pct_change, format_price

NIFTY50_TOKEN = 256265  # Kite instrument token for the NIFTY 50 index (general knowledge; checked by search first)


def unwrap_rows(obj: Any, *keys: str) -> list[dict]:
    """Accept a list, or a dict wrapping the list under data/holdings/etc."""
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        for k in ("data", *keys):
            v = obj.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
            if isinstance(v, dict):
                inner = unwrap_rows(v, *keys)
                if inner:
                    return inner
    return []


def clean_symbol(ts: str) -> str:
    s = (ts or "").strip().upper()
    for suf in ("-BE", "-T0", "-BZ", "-SM", "-ST", "-X1"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return s


def _f(v: Any) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _when(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v).replace(" ", "T")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return s


def unavailable_quote(symbol: str, reason: str, sample: bool) -> dict:
    return {"sampleData": sample, "available": False, "symbol": symbol, "reason": reason}


def pick_quote_row(payload: Any, symbol: str) -> Optional[dict]:
    """Kite returns {"NSE:INFY": {...}}; accept that, {"data": {...}}, or a bare row."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data", payload)
    if isinstance(data, dict):
        for key in (f"NSE:{symbol}", f"BSE:{symbol}", symbol):
            row = data.get(key)
            if isinstance(row, dict):
                return row
        if "last_price" in data:
            return data
        rows = [v for v in data.values() if isinstance(v, dict) and "last_price" in v]
        if len(rows) == 1:
            return rows[0]
    return None


def map_quote(row: dict, symbol: str, source: str, sample: bool) -> dict:
    last = _f(row.get("last_price"))
    ohlc = row.get("ohlc") or {}
    prev = _f(ohlc.get("close"))
    change = _f(row.get("net_change"))
    if change in (None, 0.0) and last is not None and prev:
        change = last - prev
    pct = (change / prev) if (change is not None and prev) else None
    high, low = _f(ohlc.get("high")), _f(ohlc.get("low"))
    position = None
    if last is not None and high is not None and low is not None and high > low:
        position = max(0.0, min(1.0, (last - low) / (high - low)))
    return {
        "sampleData": sample,
        "available": last is not None,
        "symbol": symbol,
        "source": source,
        "asOf": _when(row.get("timestamp") or row.get("last_trade_time")),
        "lastPrice": last,
        "lastPriceDisplay": format_price(last),
        "open": _f(ohlc.get("open")),
        "openDisplay": format_price(_f(ohlc.get("open"))),
        "high": high,
        "highDisplay": format_price(high),
        "low": low,
        "lowDisplay": format_price(low),
        "prevClose": prev,
        "prevCloseDisplay": format_price(prev),
        "changeDisplay": format_pct_change(pct * 100 if pct is not None else None),
        "volume": _f(row.get("volume")),
        "volumeDisplay": format_count(_f(row.get("volume"))),
        "rangePosition": position,
    }


def map_positions(payload: Any) -> list[dict]:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    rows = data.get("net") if isinstance(data, dict) and isinstance(data.get("net"), list) else unwrap_rows(data, "net", "positions")
    out = []
    for r in rows:
        qty = _f(r.get("quantity"))
        if not qty:
            continue  # closed today
        out.append({
            "symbol": clean_symbol(str(r.get("tradingsymbol") or "")),
            "exchange": str(r.get("exchange") or ""),
            "product": str(r.get("product") or ""),
            "quantity": qty,
            "avgPrice": _f(r.get("average_price")),
            "avgPriceDisplay": format_price(_f(r.get("average_price"))),
            "lastPrice": _f(r.get("last_price")),
            "lastPriceDisplay": format_price(_f(r.get("last_price"))),
            "pnl": _f(r.get("pnl")),
            "pnlDisplay": format_inr(_f(r.get("pnl"))),
        })
    return out


def summarize_orders(payload: Any) -> dict:
    rows = unwrap_rows(payload.get("data", payload) if isinstance(payload, dict) else payload, "orders")
    by: dict[str, int] = {}
    for r in rows:
        st = str(r.get("status") or "UNKNOWN").upper()
        group = "COMPLETE" if st == "COMPLETE" else "CANCELLED" if st in ("CANCELLED", "REJECTED") else "OPEN"
        by[group] = by.get(group, 0) + 1
    return {"total": len(rows), "complete": by.get("COMPLETE", 0), "open": by.get("OPEN", 0), "cancelled": by.get("CANCELLED", 0)}


def count_trades(payload: Any) -> int:
    return len(unwrap_rows(payload.get("data", payload) if isinstance(payload, dict) else payload, "trades"))


def map_gtts(payload: Any) -> list[dict]:
    rows = unwrap_rows(payload.get("data", payload) if isinstance(payload, dict) else payload, "gtts", "triggers")
    out = []
    for r in rows:
        cond = r.get("condition") or {}
        trig = [t for t in (_f(v) for v in (cond.get("trigger_values") or [])) if t is not None]
        orders = r.get("orders") or []
        qty = _f(orders[0].get("quantity")) if orders and isinstance(orders[0], dict) else None
        kind = str(r.get("type") or "single").lower()
        out.append({
            "symbol": clean_symbol(str(cond.get("tradingsymbol") or "")),
            "kind": "TWO_LEG" if "two" in kind or "oco" in kind else "SINGLE",
            "triggerPrices": trig,
            "triggerDisplays": [format_price(t) for t in trig],
            "lastPriceAtSetup": _f(cond.get("last_price")),
            "quantity": qty,
            "status": str(r.get("status") or "").lower(),
            "createdAt": _when(r.get("created_at")),
        })
    return [g for g in out if g["status"] in ("", "active")]


def build_activity(*, sample: bool, connected: bool, source: str, as_of: str, positions: list[dict] | None,
                   orders: dict | None, trades: int | None, gtts: list[dict] | None) -> dict:
    """Plain-words facts about today's account activity. States what is there and stops."""
    sentences: list[str] = []
    if not connected:
        sentences.append("Connect your Zerodha account to see today's positions, orders and price triggers.")
    else:
        if positions is not None:
            sentences.append(
                "You have no open positions today." if not positions else
                f"You have {len(positions)} open position{'s' if len(positions) != 1 else ''} today, separate from your long-term holdings.")
        if orders is not None:
            if orders["total"] == 0:
                sentences.append("No orders were placed today.")
            else:
                sentences.append(f"{orders['total']} order{'s' if orders['total'] != 1 else ''} today: {orders['complete']} completed, "
                                 f"{orders['open']} still open and {orders['cancelled']} cancelled or rejected.")
        if gtts is not None:
            sentences.append("You have no active price triggers (GTT)." if not gtts else
                             f"You have {len(gtts)} active price trigger{'s' if len(gtts) != 1 else ''} (GTT) waiting on your account.")
    return {
        "sampleData": sample,
        "connected": connected,
        "source": source,
        "asOf": as_of,
        "sentences": [{"templateId": f"activity.{i}", "text": t} for i, t in enumerate(sentences)],
        "positions": positions or [],
        "orders": orders,
        "tradesToday": trades,
        "gtts": gtts or [],
    }
