"""/internal/prices/points: last available value on or before each requested date."""
from __future__ import annotations

from datetime import date
from typing import Callable, Optional, Sequence

from .series import fast_on_or_before


def points_for(series: Optional[Sequence[tuple[date, float]]], dates: list[str]) -> list[dict]:
    out = []
    ds = [p[0] for p in series] if series else []
    for d in dates:
        req = date.fromisoformat(d)
        p = fast_on_or_before(ds, series, req) if series else None
        out.append({"requestedDate": d, "date": p[0].isoformat() if p else None, "value": round(p[1], 4) if p else None})
    return out
