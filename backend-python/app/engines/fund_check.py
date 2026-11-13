"""Assembles the FundCheck payload (contract B.4)."""
from __future__ import annotations

from ..formatting import format_inr
from .figures import comparison as C
from .figures import make_figure
from .fund_answers import bench_points, build_answers as _answers, fund_window, nav_points, value_on_or_before
from .fund_facts import build_facts
from .history import build_drawdown, build_price_history, empty_history
from .inputs import FundInputs
from .series import years_before


def fund_subtitle(category: str, plan: str) -> str:
    return f"{category} · {'Direct' if plan == 'DIRECT' else 'Regular'} plan"


def build_fund_check(fi: FundInputs, sample: bool) -> dict:
    m = fi.meta
    asof = fi.as_of.isoformat()
    pts, bpts = nav_points(fi), bench_points(fi)
    last = pts[-1][1] if pts else None
    ago = value_on_or_before(pts, years_before(fi.as_of, 1)) if pts else None
    nav_asof = pts[-1][0].isoformat() if pts else asof
    inst = {
        "kind": "FUND", "schemeCode": m.schemeCode, "isin": m.isin, "name": m.name, "shortName": m.shortName, "amc": m.amc, "category": m.category,
        "categoryGroup": m.categoryGroup, "planType": m.planType,
        "twin": {"schemeCode": fi.twin.schemeCode, "name": fi.twin.name, "planType": fi.twin.planType} if fi.twin else None,
        "benchmark": {"id": m.benchmarkId or "", "name": fi.benchmark_name},
        "nav": make_figure("nav", "NAV (price of one unit)", last, "INR_PRICE", m.source, nav_asof, [C("PREVIOUS_PERIOD", "1 year ago", ago[1] if ago else None, "INR_PRICE")], "nav"),
    }
    code, label, start = fund_window(fi)
    bsrc = m.source
    ph = build_price_history(pts, bpts, m.benchmarkId or "", fi.benchmark_name, start, bsrc, fi.as_of) or empty_history(m.benchmarkId or "", fi.benchmark_name, bsrc, fi.as_of)
    dd = build_drawdown("fnd", code, label, pts, bpts, fi.benchmark_name, start, bsrc, fi.as_of)
    return {"sampleData": sample, "asOf": asof, "instrument": inst,
            "amount": {"amountInr": fi.amount_inr, "display": format_inr(fi.amount_inr), "basis": fi.amount_basis},
            "answers": _answers(fi), "facts": build_facts(fi), "priceHistory": ph, "drawdown": dd}
