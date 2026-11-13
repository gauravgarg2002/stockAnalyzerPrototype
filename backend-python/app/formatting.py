"""Indian number/date formatting (contract 0.4). Round HALF_UP on the shortest decimal string of the float."""
from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

NOT_AVAILABLE = "Not available"
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _dec(x: Any) -> Decimal:
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        raise TypeError("bool is not a number")
    if isinstance(x, int):
        return Decimal(x)
    return Decimal(str(x))


def _round(x: Decimal, places: int) -> Decimal:
    """HALF_UP on the absolute value (symmetric), sign restored."""
    q = Decimal(1).scaleb(-places)
    r = abs(x).quantize(q, rounding=ROUND_HALF_UP)
    return -r if x < 0 else r


def group_indian(int_str: str) -> str:
    """Digits only -> Indian grouping (12,34,567)."""
    if len(int_str) <= 3:
        return int_str
    head, tail = int_str[:-3], int_str[-3:]
    parts = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    if head:
        parts.append(head)
    return ",".join(reversed(parts)) + "," + tail


def _fixed(x: Decimal, places: int) -> str:
    """Absolute value, fixed decimals, no grouping."""
    r = abs(_round(x, places))
    return f"{r:.{places}f}"


def _trim(s: str) -> str:
    return s[:-2] if s.endswith(".0") else s


def format_inr(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    d = _dec(x)
    r = abs(_round(d, 0))
    neg = d < 0 and r != 0
    sign = "-" if neg else ""
    if r < 100000:
        return f"{sign}₹{group_indian(str(int(r)))}"
    lakh = _round(r / Decimal(100000), 1)
    if lakh < 100:
        return f"{sign}₹{_trim(f'{lakh:.1f}')} lakh"
    crore = _round(r / Decimal(10000000), 1)
    if crore < 1000:
        return f"{sign}₹{_trim(f'{crore:.1f}')} crore"
    whole = _round(r / Decimal(10000000), 0)
    return f"{sign}₹{group_indian(str(int(whole)))} crore"


def format_price(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    d = _dec(x)
    s = _fixed(d, 2)
    ip, fp = s.split(".")
    neg = d < 0 and (int(ip) != 0 or int(fp) != 0)
    return f"{'-' if neg else ''}₹{group_indian(ip)}.{fp}"


def format_pct(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    d = _dec(x)
    r = _round(d, 1)
    return f"{r:.1f}%".replace("-0.0%", "0.0%")


def format_pct_change(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    r = _round(_dec(x), 1)
    if r == 0:
        return "0.0%"
    return f"{'+' if r > 0 else '-'}{abs(r):.1f}%"


def format_times(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    r = _round(_dec(x), 1)
    return f"{r:.1f}x".replace("-0.0x", "0.0x")


def format_count(x: Optional[float]) -> str:
    if x is None:
        return NOT_AVAILABLE
    d = _dec(x)
    r = abs(_round(d, 0))
    neg = d < 0 and r != 0
    return f"{'-' if neg else ''}{group_indian(str(int(r)))}"


def _unit_word(x: Optional[float], word: str) -> str:
    if x is None:
        return NOT_AVAILABLE
    r = _round(_dec(x), 1)
    s = _trim(f"{r:.1f}")
    return f"{s} {word}" if s == "1" else f"{s} {word}s"


def format_years(x: Optional[float]) -> str:
    return _unit_word(x, "year")


def format_months(x: Optional[float]) -> str:
    return _unit_word(x, "month")


def format_days(x: Optional[float]) -> str:
    return _unit_word(x, "day")


def format_date(d: "date | str | None") -> str:
    if d is None:
        return NOT_AVAILABLE
    if isinstance(d, str):
        d = datetime.strptime(d[:10], "%Y-%m-%d").date()
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def format_unit(value: Any, unit: str) -> str:
    """Display string for a value in a Unit. None -> 'Not available'; TEXT inserted verbatim."""
    if value is None:
        return NOT_AVAILABLE
    if unit == "TEXT":
        return str(value)
    fn = {
        "INR": format_inr, "INR_PRICE": format_price, "PCT": format_pct, "PCT_CHANGE": format_pct_change,
        "TIMES": format_times, "YEARS": format_years, "MONTHS": format_months, "DAYS": format_days,
        "COUNT": format_count,
    }[unit]
    return fn(value)
