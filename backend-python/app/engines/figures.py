"""Figure / Comparison builders (contract 0.3). Values are rounded sensibly, display derives from the rounded value."""
from __future__ import annotations

from typing import Any, Optional

from ..formatting import NOT_AVAILABLE, format_unit

_ROUND = {"INR": 0, "INR_PRICE": 4, "PCT": 2, "PCT_CHANGE": 2, "TIMES": 2, "YEARS": 2, "MONTHS": 2, "DAYS": 0, "COUNT": 0}


def norm_value(value: Any, unit: str) -> Any:
    if value is None:
        return None
    if unit == "TEXT":
        return str(value)
    nd = _ROUND[unit]
    r = round(float(value), nd)
    if nd == 0:
        return int(r)
    return r + 0.0  # avoid -0.0


def comparison(kind: str, label: str, value: Any, unit: str) -> dict:
    v = norm_value(value, unit)
    return {"kind": kind, "label": label, "value": v, "unit": unit, "display": format_unit(v, unit)}


def make_figure(id: str, label: str, value: Any, unit: str, source: str, as_of: str,
                comparisons: Optional[list[dict]] = None, term_id: Optional[str] = None) -> dict:
    v = norm_value(value, unit)
    return {"id": id, "label": label, "value": v, "unit": unit, "display": format_unit(v, unit) if v is not None else NOT_AVAILABLE,
            "source": source, "asOf": as_of, "comparisons": comparisons or [], "termId": term_id}


def detail_table(title: str, columns: list[str], rows: list[list[str]]) -> dict:
    return {"title": title, "columns": columns, "rows": rows}
