"""Time-series helpers. A series is a list of (date, value) sorted ascending."""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, timedelta
from typing import Optional, Sequence

Series = Sequence[tuple[date, float]]


def years_before(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year - years, day=28)


def on_or_before(series: Series, d: date) -> Optional[tuple[date, float]]:
    """Last point with date <= d, or None."""
    dates = [p[0] for p in series]
    i = bisect_right(dates, d)
    return series[i - 1] if i > 0 else None


def fast_on_or_before(dates: list[date], series: Series, d: date) -> Optional[tuple[date, float]]:
    i = bisect_right(dates, d)
    return series[i - 1] if i > 0 else None


def pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
    if old is None or new is None or old == 0:
        return None
    return (new / old - 1.0) * 100.0


def cagr(v0: Optional[float], v1: Optional[float], years: float) -> Optional[float]:
    """Compound yearly growth in percent; None if undefined (non-positive values or zero years)."""
    if v0 is None or v1 is None or v0 <= 0 or v1 <= 0 or years <= 0:
        return None
    return ((v1 / v0) ** (1.0 / years) - 1.0) * 100.0


def window(series: Series, start: date, end: Optional[date] = None) -> list[tuple[date, float]]:
    return [p for p in series if p[0] >= start and (end is None or p[0] <= end)]


def drawdown_episodes(series: Series) -> list[dict]:
    """All peak-to-trough episodes. Each: peak_date, peak, trough_date, trough, fall_pct (negative), recovery_date|None."""
    episodes: list[dict] = []
    if not series:
        return episodes
    peak_d, peak = series[0]
    cur = None  # current episode
    for d, v in series[1:]:
        if v >= peak:
            if cur is not None:
                cur["recovery_date"] = d
                episodes.append(cur)
                cur = None
            peak_d, peak = d, v
        else:
            if cur is None:
                cur = {"peak_date": peak_d, "peak": peak, "trough_date": d, "trough": v, "recovery_date": None}
            elif v < cur["trough"]:
                cur["trough_date"], cur["trough"] = d, v
    if cur is not None:
        episodes.append(cur)
    for e in episodes:
        e["fall_pct"] = (e["trough"] / e["peak"] - 1.0) * 100.0
        e["recovery_days"] = (e["recovery_date"] - e["trough_date"]).days if e["recovery_date"] else None
    return episodes


def max_drawdown(series: Series) -> Optional[dict]:
    eps = drawdown_episodes(series)
    return min(eps, key=lambda e: e["fall_pct"]) if eps else None


def top_drawdowns(series: Series, n: int = 5) -> list[dict]:
    return sorted(drawdown_episodes(series), key=lambda e: e["fall_pct"])[:n]


def weekly_resample(series: Series) -> list[tuple[date, float]]:
    """Last close of each ISO week; the final point is always the last date of the series."""
    out: list[tuple[date, float]] = []
    last_key = None
    for d, v in series:
        key = d.isocalendar()[:2]
        if key == last_key:
            out[-1] = (d, v)
        else:
            out.append((d, v))
            last_key = key
    return out


def rebase(series: Series, dates: Sequence[date], first_value: float) -> list[tuple[date, float]]:
    """Series values at `dates` (on-or-before), scaled so the first equals first_value."""
    ds = [p[0] for p in series]
    vals = []
    for d in dates:
        p = fast_on_or_before(ds, series, d)
        vals.append(p[1] if p else None)
    base = next((v for v in vals if v is not None), None)
    if base is None or base == 0:
        return []
    return [(d, v / base * first_value) for d, v in zip(dates, vals) if v is not None]


def calendar_year_returns(series: Series, years: Sequence[int]) -> dict[int, Optional[float]]:
    """Percent return for each calendar year, last close of year vs last close of previous year (on-or-before)."""
    ds = [p[0] for p in series]
    out: dict[int, Optional[float]] = {}
    for y in years:
        end = fast_on_or_before(ds, series, date(y, 12, 31))
        start = fast_on_or_before(ds, series, date(y - 1, 12, 31))
        if end is None or start is None or end[0] < date(y, 12, 1):
            out[y] = None
        else:
            out[y] = pct_change(start[1], end[1])
    return out


def avg_daily_traded_value(points: Sequence[tuple[date, float, Optional[int]]], n: int = 20,
                           end: Optional[date] = None) -> Optional[float]:
    """Mean of close*volume over the last n sessions on or before `end`."""
    pts = [p for p in points if (end is None or p[0] <= end) and p[2] is not None]
    if len(pts) < n:
        return None
    pts = pts[-n:]
    return sum(p[1] * p[2] for p in pts) / n


def median(xs: Sequence[float]) -> Optional[float]:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2.0


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)
