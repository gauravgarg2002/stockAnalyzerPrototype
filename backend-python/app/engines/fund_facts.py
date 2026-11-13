"""The eight fixed fund facts (ids and order fixed)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from ..formatting import format_date, format_inr, format_pct, format_pct_change, format_unit
from ..narrative.render import S
from .figures import comparison as C
from .figures import detail_table, make_figure
from .fund_answers import CAL_YEARS, TXT, bench_points, cost_numbers, nav_points, plan_label, pos, safe, src
from .inputs import FundInputs
from .peers import category_median
from .series import calendar_year_returns


def fact(id: str, order: int, title: str, term: Optional[str], available: bool, sentences, figures, details=None) -> dict:
    return {"id": id, "order": order, "title": title, "termId": term, "available": available, "sentences": sentences, "figures": figures, "details": details}


def fact_plan_type(fi: FundInputs) -> dict:
    m = fi.meta
    n = cost_numbers(fi)
    asof = m.terAsOf or fi.as_of.isoformat()
    title = "Direct or regular plan, and the yearly cost difference"
    ptxt = "Direct plan" if m.planType == "DIRECT" else "Regular plan"
    figs = [make_figure("plan_type", "Plan type", ptxt, "TEXT", src(fi), asof, [], "direct_plan" if m.planType == "DIRECT" else "regular_plan")]
    if n["gap"] is None:
        other = "regular" if m.planType == "DIRECT" else "direct"
        return fact("plan_type", 1, title, "direct_plan" if m.planType == "DIRECT" else "regular_plan", False,
                    [S("fnd.fact.plan_no_twin", planLabel=(plan_label(m.planType), TXT), otherLabel=(other, TXT))], figs)
    figs.append(make_figure("plan_cost_gap", "Yearly cost difference between the two plans on your amount", n["gap"], "INR", src(fi), asof,
                            [C("PLAN_TWIN", f"Yearly cost of the {plan_label(fi.twin.planType)} plan", n["twin_cost"], "INR")], "regular_plan"))
    tid = "fnd.fact.plan_regular" if m.planType == "REGULAR" else "fnd.fact.plan_direct"
    return fact("plan_type", 1, title, "direct_plan" if m.planType == "DIRECT" else "regular_plan", True, [S(tid, amount=(fi.amount_inr, "INR"), gap=(n["gap"], "INR"))], figs)


def fact_expense(fi: FundInputs) -> dict:
    m = fi.meta
    n = cost_numbers(fi)
    asof = m.terAsOf or fi.as_of.isoformat()
    title = "Expense ratio against the category"
    fig = make_figure("expense_ratio", "Yearly fee (expense ratio)", n["ter"], "PCT", src(fi), asof,
                      [C("CATEGORY", f"Median for {plan_label(m.planType)} plans in {m.category}", n["median"], "PCT")], "expense_ratio")
    if n["ter"] is None or n["median"] is None:
        return fact("expense_vs_category", 2, title, "expense_ratio", False, [S("fnd.generic.na", fundName=(m.name, TXT))], [fig])
    s = [S("fnd.fact.expense", ter=(n["ter"], "PCT"), pos=(pos(n["ter"], n["median"], 0.005), TXT), category=(m.category, TXT), median=(n["median"], "PCT"), planLabel=(plan_label(m.planType), TXT)),
         S("fnd.fact.expense_rupees", amount=(fi.amount_inr, "INR"), cost=(n["cost"], "INR"))]
    return fact("expense_vs_category", 2, title, "expense_ratio", True, s, [fig])


def fact_age_size(fi: FundInputs) -> dict:
    m, cat = fi.meta, fi.category
    title = "Fund age and size"
    asof = fi.as_of.isoformat()
    if m.launchDate is None:
        return fact("age_and_size", 3, title, "aum", False, [S("fnd.generic.na", fundName=(m.name, TXT))], [])
    age = (fi.as_of - m.launchDate).days / 365.25
    figs = [make_figure("fund_age", "Age of the fund", age, "YEARS", src(fi), asof, [C("CATEGORY", f"Median for {m.category} funds", category_median(cat, "ageYears"), "YEARS")], None),
            make_figure("aum", "Size of the fund (assets under management)", m.aumInr, "INR", src(fi), asof, [C("CATEGORY", f"Median for {m.category} funds", category_median(cat, "aumInr"), "INR")], "aum")]
    s = [S("fnd.fact.age", launchDate=(format_date(m.launchDate), TXT), age=(age, "YEARS"), category=(m.category, TXT), medianAge=(category_median(cat, "ageYears"), "YEARS")),
         S("fnd.fact.size", aum=(m.aumInr, "INR"), category=(m.category, TXT), medianAum=(category_median(cat, "aumInr"), "INR"))]
    return fact("age_and_size", 3, title, "aum", True, s, figs)


def fact_years_trailed(fi: FundInputs) -> dict:
    m, cat = fi.meta, fi.category
    title = "Years out of the last five it trailed its benchmark"
    f, b = calendar_year_returns(nav_points(fi), CAL_YEARS), calendar_year_returns(bench_points(fi), CAL_YEARS)
    yrs = [y for y in CAL_YEARS if f[y] is not None and b[y] is not None]
    rows = [[str(y), format_pct_change(f[y]) if f[y] is not None else "Not available", format_pct_change(b[y]) if b[y] is not None else "Not available",
             ("Trailed" if f[y] < b[y] else "Matched or ahead") if y in yrs else "Not available"] for y in CAL_YEARS]
    details = detail_table(f"Calendar-year returns: fund and {fi.benchmark_name}", ["Year", "Fund", "Benchmark", "Result"], rows)
    avg = (cat or {}).get("averageYearsTrailed")
    if not yrs:
        return fact("years_trailed_benchmark", 4, title, "benchmark", False, [S("fnd.fact.trailed_na")], [], details)
    trailed = sum(1 for y in yrs if f[y] < b[y])
    fig = make_figure("years_trailed", "Calendar years the fund returned less than its benchmark", trailed, "COUNT", src(fi), fi.as_of.isoformat(),
                      [C("CATEGORY", f"Average for {m.category} funds (out of five)", avg, "YEARS")], "benchmark")
    s = [S("fnd.fact.trailed", trailed=(trailed, "COUNT"), total=(len(yrs), "COUNT"), firstYear=(str(yrs[0]), TXT), lastYear=(str(yrs[-1]), TXT))]
    if avg is not None and len(yrs) == 5:
        s.append(S("fnd.fact.trailed_cmp", category=(m.category, TXT), catAvg=(avg, "YEARS")))
    elif len(yrs) < 5:
        s.append(S("fnd.fact.trailed_na"))
    return fact("years_trailed_benchmark", 4, title, "benchmark", len(yrs) == 5, s, [fig], details)


def fact_mandate(fi: FundInputs) -> dict:
    m, cat, p = fi.meta, fi.category, fi.portfolio
    title = "Category and what it may hold"
    asof = p.portfolioDate if p else fi.as_of.isoformat()
    minimum = (cat or {}).get("minEquityPct")
    eq = p.assetMix["equityPct"] if p else None
    figs = [make_figure("category", "Category", m.category, "TEXT", src(fi), fi.as_of.isoformat(), [], None),
            make_figure("equity_share", "Share of the fund held in shares", eq, "PCT", src(fi), asof,
                        [C("THRESHOLD", "Category minimum" if minimum is not None else "Category minimum (no shares required)", minimum if minimum is not None else 0.0, "PCT")], None)]
    may = (cat or {}).get("mayHold")
    if not may or eq is None:
        return fact("category_mandate", 5, title, None, False, [S("fnd.generic.na", fundName=(m.name, TXT))], figs)
    s = [S("fnd.fact.mandate", category=(m.category, TXT), mayHold=(may, TXT))]
    s.append(S("fnd.fact.mandate_equity", equity=(eq, "PCT"), minimum=(minimum, "PCT")) if minimum is not None else S("fnd.fact.mandate_nomin", equity=(eq, "PCT")))
    return fact("category_mandate", 5, title, None, True, s, figs)


def fact_top10(fi: FundInputs) -> dict:
    m, cat, p = fi.meta, fi.category, fi.portfolio
    title = "Share of the fund in its top ten holdings"
    if not p or not p.holdings:
        return fact("top10_share", 6, title, "top10_share", False, [S("fnd.fact.top10_na")], [])
    hold = sorted(p.holdings, key=lambda h: -h["weightPct"])
    share = sum(h["weightPct"] for h in hold[:10])
    med = category_median(cat, "top10SharePct")
    fig = make_figure("top10_share", "Share of the fund in its ten largest holdings", share, "PCT", src(fi), p.portfolioDate, [C("CATEGORY", f"Median for {m.category} funds", med, "PCT")], "top10_share")
    s = [S("fnd.fact.top10", share=(share, "PCT"), category=(m.category, TXT), median=(med, "PCT")) if med is not None else S("fnd.generic.na", fundName=(m.name, TXT)),
         S("fnd.fact.top10_largest", name=(hold[0]["name"], TXT), weight=(hold[0]["weightPct"], "PCT"))]
    rows = [[h["name"], h.get("sector") or "Not available", format_pct(h["weightPct"])] for h in hold[:10]]
    return fact("top10_share", 6, title, "top10_share", True, s, [fig], detail_table("Ten largest holdings", ["Company", "Sector", "Share of fund"], rows))


def fact_exit_lockin(fi: FundInputs) -> dict:
    m = fi.meta
    title = "Exit load and lock-in"
    asof = fi.as_of.isoformat()
    el = m.exitLoad or {"text": "None", "pct": 0, "days": 0}
    lock = m.lockInYears if m.lockInYears is not None else 0
    if m.category == "ELSS":
        comp = C("THRESHOLD", "ELSS lock-in set by law: 3 years", 3.0, "YEARS")
    else:
        comp = C("CATEGORY", f"Typical for {m.category} funds", 0.0, "YEARS")
    figs = [make_figure("exit_load", "Exit load", el["text"], "TEXT", src(fi), asof, [], "exit_load"),
            make_figure("lock_in", "Lock-in period", lock, "YEARS", src(fi), asof, [comp], "lock_in")]
    s = [S("fnd.fact.exit_none") if el["text"] == "None" else S("fnd.fact.exit_load", exitLoad=(el["text"], TXT)),
         S("fnd.fact.lockin_yes", lockIn=(lock, "YEARS")) if lock else S("fnd.fact.lockin_none")]
    return fact("exit_load_lockin", 7, title, "exit_load", True, s, figs)


def fact_overlap(fi: FundInputs) -> dict:
    title = "Overlap with funds you already hold"
    uf = sorted(fi.user_funds, key=lambda u: -u["overlapPct"])
    if not uf:
        return fact("overlap_with_holdings", 8, title, "fund_overlap", True, [S("fnd.fact.overlap_none")], [])
    figs = [make_figure(f"overlap_{u['schemeCode']}", u["name"], u["overlapPct"], "PCT", "Calculated from your holdings", fi.as_of.isoformat(), [], "fund_overlap") for u in uf]
    top = uf[0]
    s = [S("fnd.fact.overlap_top", fundName=(top["name"], TXT), overlapPct=(top["overlapPct"], "PCT"), commonCount=(top["commonCount"], "COUNT"))]
    if len(uf) > 1:
        s.append(S("fnd.fact.overlap_rest", restCount=(len(uf) - 1, "COUNT")))
    details = detail_table("Overlap with each fund you hold", ["Fund", "Overlap", "Companies in common"], [[u["name"], format_pct(u["overlapPct"]), format_unit(u["commonCount"], "COUNT")] for u in uf])
    return fact("overlap_with_holdings", 8, title, "fund_overlap", True, s, figs, details)


def build_facts(fi: FundInputs) -> list[dict]:
    return [fact_plan_type(fi), fact_expense(fi), fact_age_size(fi), fact_years_trailed(fi), fact_mandate(fi), fact_top10(fi), fact_exit_lockin(fi), fact_overlap(fi)]
