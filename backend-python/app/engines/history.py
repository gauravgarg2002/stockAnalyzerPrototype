"""Shared price-history and drawdown builders for stock and fund checks."""
from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from ..formatting import format_date
from ..narrative.render import S
from .figures import comparison as C
from .figures import make_figure
from .series import max_drawdown, rebase, weekly_resample, window, years_before

TXT = "TEXT"


def build_price_history(points: Sequence[tuple[date, float]], bench: Sequence[tuple[date, float]], bench_id: str, bench_name: str,
                        start: date, source: str, as_of: date) -> Optional[dict]:
    pts = window(points, start, as_of)
    if len(pts) < 2:
        return None
    weekly = weekly_resample(pts)
    dates = [d for d, _ in weekly]
    b = rebase(bench, dates, weekly[0][1]) if bench else []
    return {
        "frequency": "WEEKLY", "from": dates[0].isoformat(), "to": dates[-1].isoformat(),
        "points": [{"date": d.isoformat(), "value": round(v, 4)} for d, v in weekly],
        "benchmark": {"id": bench_id, "name": bench_name, "points": [{"date": d.isoformat(), "value": round(v, 4)} for d, v in b]},
        "source": source, "asOf": as_of.isoformat(),
    }


def empty_history(bench_id: str, bench_name: str, source: str, as_of: date) -> dict:
    return {"frequency": "WEEKLY", "from": as_of.isoformat(), "to": as_of.isoformat(), "points": [],
            "benchmark": {"id": bench_id, "name": bench_name, "points": []}, "source": source, "asOf": as_of.isoformat()}


def build_drawdown(prefix: str, window_code: str, window_label: str, points: Sequence[tuple[date, float]], bench: Sequence[tuple[date, float]],
                   bench_name: str, start: date, source: str, as_of: date) -> dict:
    """prefix is 'stk' or 'fnd' (template family)."""
    pts = window(points, start, as_of)
    bpts = window(bench, pts[0][0], as_of) if (bench and pts) else []
    dd = max_drawdown(pts)
    bdd = max_drawdown(bpts) if bpts else None
    comps = [C("BENCHMARK", f"{bench_name}, same period", bdd["fall_pct"] if bdd else None, "PCT_CHANGE")]
    sentences = []
    if dd is None:
        fig = make_figure("worst_fall", "Worst fall from a high to a later low", 0.0, "PCT_CHANGE", source, as_of.isoformat(), comps, "worst_fall")
        sentences.append(S(f"{prefix}.drawdown.none"))
        return {"window": window_code, "worstFall": fig, "peakDate": None, "troughDate": None, "recoveryDate": None, "recoveryDays": None, "sentences": sentences}
    fig = make_figure("worst_fall", "Worst fall from a high to a later low", dd["fall_pct"], "PCT_CHANGE", source, as_of.isoformat(), comps, "worst_fall")
    sentences.append(S(f"{prefix}.drawdown.fall", windowLabel=(window_label, TXT), fall=(abs(round(dd["fall_pct"], 2)), "PCT"),
                       peakDate=(format_date(dd["peak_date"]), TXT), troughDate=(format_date(dd["trough_date"]), TXT)))
    if dd["recovery_date"]:
        sentences.append(S(f"{prefix}.drawdown.recovered", days=(dd["recovery_days"], "DAYS")))
    else:
        sentences.append(S(f"{prefix}.drawdown.not_recovered", asOfDate=(format_date(as_of), TXT)))
    if bdd is not None:
        if prefix == "stk":
            sentences.append(S("stk.drawdown.benchmark", benchFall=(abs(round(bdd["fall_pct"], 2)), "PCT")))
        else:
            sentences.append(S("fnd.drawdown.benchmark", benchName=(bench_name, TXT), benchFall=(abs(round(bdd["fall_pct"], 2)), "PCT")))
    return {"window": window_code, "worstFall": fig, "peakDate": dd["peak_date"].isoformat(), "troughDate": dd["trough_date"].isoformat(),
            "recoveryDate": dd["recovery_date"].isoformat() if dd["recovery_date"] else None, "recoveryDays": dd["recovery_days"], "sentences": sentences}
