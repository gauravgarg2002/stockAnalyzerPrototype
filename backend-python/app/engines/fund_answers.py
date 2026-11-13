"""The five fund answers (ids and order fixed) and helpers shared with fund facts."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from ..formatting import format_date, format_inr, format_pct, format_pct_change, format_unit
from ..narrative.render import S, TemplateError
from .figures import comparison as C
from .figures import detail_table, make_figure
from .inputs import FundInputs
from .peers import category_median
from .series import cagr, calendar_year_returns, fast_on_or_before, max_drawdown, pct_change, top_drawdowns, window, years_before

TXT = "TEXT"
TOLERANCE_DAYS = 5
CAL_YEARS = [2021, 2022, 2023, 2024, 2025]


def nav_points(fi: FundInputs) -> list[tuple[date, float]]:
    return list(fi.nav.points) if fi.nav else []


def bench_points(fi: FundInputs) -> list[tuple[date, float]]:
    return [(p[0], p[1]) for p in fi.benchmark.points] if fi.benchmark else []


def src(fi: FundInputs) -> str:
    return fi.meta.source


def value_on_or_before(pts: list[tuple[date, float]], d: date, tolerance_start: bool = False) -> Optional[tuple[date, float]]:
    p = fast_on_or_before([x[0] for x in pts], pts, d)
    if p is None and tolerance_start and pts and (pts[0][0] - d).days <= TOLERANCE_DAYS:
        return pts[0]
    return p


def period_return(pts: list[tuple[date, float]], years: int, as_of: date) -> Optional[tuple[float, date, date]]:
    """(CAGR %, start date, end date) over `years` ending at as_of, or None if the series is shorter."""
    if not pts:
        return None
    start = years_before(as_of, years)
    a = value_on_or_before(pts, start, tolerance_start=True)
    b = value_on_or_before(pts, as_of)
    if a is None or b is None:
        return None
    yrs = (b[0] - a[0]).days / 365.25
    if yrs < years - 0.05:
        return None
    r = cagr(a[1], b[1], years)
    return (r, a[0], b[0]) if r is not None else None


def pos(a: Optional[float], b: Optional[float], tol: float = 0.1) -> str:
    """'above' / 'below' / 'the same as' using an absolute tolerance in percentage points."""
    if a is None or b is None or abs(a - b) <= tol:
        return "the same as"
    return "above" if a > b else "below"


def safe(fi: FundInputs, tid: str, **facts) -> dict:
    try:
        return S(tid, **facts)
    except TemplateError:
        return S("fnd.generic.na", fundName=(fi.meta.name, TXT))


def answer(id: str, order: int, question: str, sentences, figures, details) -> dict:
    return {"id": id, "order": order, "question": question, "sentences": sentences, "figures": figures, "details": details}


def plan_label(plan: str) -> str:
    return "direct" if plan == "DIRECT" else "regular"


def fund_window(fi: FundInputs) -> tuple[str, str, date]:
    """(window code, label for sentences, start date) for the drawdown/price-history window."""
    pts = nav_points(fi)
    ten = years_before(fi.as_of, 10)
    if pts and (pts[0][0] - ten).days <= TOLERANCE_DAYS:
        return "10Y", "the last ten years", ten
    return "SINCE_LAUNCH", "the years since launch", pts[0][0] if pts else ten


def manager_tenure_years(fi: FundInputs) -> Optional[float]:
    ts = []
    for m in fi.meta.managers:
        try:
            ts.append((fi.as_of - date.fromisoformat(m["since"])).days / 365.25)
        except (KeyError, ValueError):
            pass
    return max(ts) if ts else None


# ---------------------------------------------------------------- 1 holdings
def answer_holdings(fi: FundInputs) -> dict:
    m, p, cat = fi.meta, fi.portfolio, fi.category
    q = "What does it invest in and who runs it?"
    asof = (p.portfolioDate if p else fi.as_of.isoformat())
    mix = p.assetMix if p else {"equityPct": 0.0, "debtPct": 0.0, "cashPct": 0.0, "otherPct": 0.0}
    hold = sorted(p.holdings, key=lambda h: -h["weightPct"]) if p else []
    minimum = (cat or {}).get("minEquityPct")
    tenure = manager_tenure_years(fi)
    figures = [
        make_figure("equity_share", "Share of the fund held in shares", mix["equityPct"], "PCT", src(fi), asof,
                    [C("THRESHOLD", "Category minimum" if minimum is not None else "Category minimum (no shares required)", minimum if minimum is not None else 0.0, "PCT")], None),
        make_figure("holdings_count", "Number of companies held", len(hold) if hold else None, "COUNT", src(fi), asof,
                    [C("CATEGORY", f"Median for {m.category} funds", category_median(cat, "holdingsCount"), "COUNT")], None),
        make_figure("manager_tenure", "Time the longest-serving manager has run it", tenure, "YEARS", src(fi), fi.as_of.isoformat(),
                    [C("CATEGORY", f"Median for {m.category} funds", category_median(cat, "managerTenureYears"), "YEARS")], "fund_manager"),
    ]
    sentences = [safe(fi, "fnd.holdings.what", fundName=(m.name, TXT), category=(m.category, TXT), amc=(m.amc, TXT), equityPct=(mix["equityPct"], "PCT"),
                      debtPct=(mix["debtPct"], "PCT"), cashPct=(mix["cashPct"] + mix.get("otherPct", 0.0), "PCT"))]
    if len(hold) >= 3:
        sentences.append(S("fnd.holdings.top", count=(len(hold), "COUNT"), top1Name=(hold[0]["name"], TXT), top1Weight=(hold[0]["weightPct"], "PCT"),
                           top2Name=(hold[1]["name"], TXT), top2Weight=(hold[1]["weightPct"], "PCT"), top3Name=(hold[2]["name"], TXT), top3Weight=(hold[2]["weightPct"], "PCT")))
    else:
        sentences.append(S("fnd.holdings.debt_only"))
    if m.managers and tenure is not None:
        sentences.append(S("fnd.holdings.managers", managerNames=(" and ".join(x["name"] for x in m.managers), TXT), tenure=(tenure, "YEARS")))
    rows = [[h["name"], h.get("sector") or "Not available", format_pct(h["weightPct"])] for h in hold[:10]]
    rows += [[f"Asset mix: {lab}", "", format_pct(mix[k])] for lab, k in (("Shares", "equityPct"), ("Debt", "debtPct"), ("Cash", "cashPct"), ("Other", "otherPct"))]
    rows += [[f"Manager: {x['name']}", "", f"Since {format_date(x['since'])}"] for x in m.managers]
    return answer("holdings", 1, q, sentences, figures, detail_table("Top 10 holdings, asset mix and managers", ["Item", "Sector or detail", "Share or date"], rows))


# ---------------------------------------------------------------- 2 performance
def answer_performance(fi: FundInputs) -> dict:
    m, cat = fi.meta, fi.category
    q = "How has it done against its benchmark and category over 3, 5 and 10 years?"
    pts, bpts = nav_points(fi), bench_points(fi)
    sentences, figures, rows = [], [], []
    for n in (3, 5, 10):
        fr = period_return(pts, n, fi.as_of)
        br = None
        if fr is not None and bpts:
            a = value_on_or_before(bpts, fr[1]); b = value_on_or_before(bpts, fr[2])
            br = cagr(a[1], b[1], n) if a and b else None
        catr = ((cat or {}).get("averageReturns") or {}).get(f"{n}Y")
        label = f"{n} years"
        figures.append(make_figure(f"return_{n}y", f"Return over {label}, yearly average", fr[0] if fr else None, "PCT", src(fi), fi.as_of.isoformat(),
                                   [C("BENCHMARK", f"{fi.benchmark_name}, same period", br, "PCT"), C("CATEGORY", f"Average for {m.category} funds", catr, "PCT")], "cagr"))
        if fr is None:
            sentences.append(S("fnd.perf.na", periodLabel=(label, TXT)))
        elif br is not None and catr is not None:
            sentences.append(S("fnd.perf.period", periodLabel=(f"the last {label}", TXT), fundReturn=(fr[0], "PCT"), benchPos=(pos(fr[0], br), TXT), benchName=(fi.benchmark_name, TXT),
                               benchReturn=(br, "PCT"), catPos=(pos(fr[0], catr), TXT), category=(m.category, TXT), catReturn=(catr, "PCT")))
        elif catr is not None:
            sentences.append(S("fnd.perf.period_nobench", periodLabel=(f"the last {label}", TXT), fundReturn=(fr[0], "PCT"), category=(m.category, TXT), catReturn=(catr, "PCT")))
        else:
            sentences.append(S("fnd.generic.na", fundName=(m.name, TXT)))
        rows.append([f"{label} (yearly average)", format_pct(fr[0]) if fr else "Not available", format_pct(br) if br is not None else "Not available"])
    fcal, bcal = calendar_year_returns(pts, CAL_YEARS), calendar_year_returns(bpts, CAL_YEARS)
    for y in CAL_YEARS:
        rows.append([f"Calendar year {y}", format_pct_change(fcal[y]) if fcal[y] is not None else "Not available",
                     format_pct_change(bcal[y]) if bcal[y] is not None else "Not available"])
    return answer("performance", 2, q, sentences, figures, detail_table("Returns by period and calendar year", ["Period", "Fund", "Benchmark"], rows))


# ---------------------------------------------------------------- 3 bumpiness
def answer_bumpiness(fi: FundInputs) -> dict:
    m, cat = fi.meta, fi.category
    q = "How bumpy has the ride been?"
    code, label, start = fund_window(fi)
    pts = window(nav_points(fi), start, fi.as_of)
    bpts = window(bench_points(fi), pts[0][0], fi.as_of) if pts and fi.benchmark else []
    dd, bdd = max_drawdown(pts), max_drawdown(bpts) if bpts else None
    catfall = (cat or {}).get("averageWorstFallPct")
    asof = fi.as_of.isoformat()
    fall = dd["fall_pct"] if dd else 0.0
    figures = [
        make_figure("worst_fall", "Worst fall from a high to a later low", fall, "PCT_CHANGE", src(fi), asof,
                    [C("BENCHMARK", f"{fi.benchmark_name}, same period", bdd["fall_pct"] if bdd else None, "PCT_CHANGE"),
                     C("CATEGORY", f"Average for {m.category} funds", catfall, "PCT_CHANGE")], "worst_fall"),
        make_figure("recovery_time", "Time to get back to the earlier high", dd["recovery_days"] if dd else None, "DAYS", src(fi), asof,
                    [C("BENCHMARK", f"{fi.benchmark_name}, same period", bdd["recovery_days"] if bdd else None, "DAYS")], "recovery_time"),
    ]
    sentences = []
    if dd is None:
        sentences.append(S("fnd.bump.none"))
    else:
        sentences.append(safe(fi, "fnd.bump.rupees", amount=(fi.amount_inr, "INR"), fall=(abs(round(fall, 2)), "PCT"), rupeeFall=(abs(fi.amount_inr * fall / 100), "INR")))
        if bdd is not None and catfall is not None:
            sentences.append(S("fnd.bump.compare", benchFall=(abs(round(bdd["fall_pct"], 2)), "PCT"), category=(m.category, TXT), catFall=(abs(catfall), "PCT")))
        sentences.append(S("fnd.bump.recovered", days=(dd["recovery_days"], "DAYS")) if dd["recovery_date"] else S("fnd.bump.not_recovered", asOfDate=(format_date(fi.as_of), TXT)))
    rows = [[format_date(e["peak_date"]), format_date(e["trough_date"]), format_pct_change(e["fall_pct"]),
             format_date(e["recovery_date"]) if e["recovery_date"] else "Not yet"] for e in top_drawdowns(pts, 5)]
    details = detail_table("Five largest falls", ["High point", "Low point", "Fall", "Back to earlier high on"], rows) if rows else None
    return answer("bumpiness", 3, q, sentences[:3], figures, details)


# ---------------------------------------------------------------- 4 cost
AMOUNT_NOTE = {"HOLDING": "your holding in this fund", "ILLUSTRATIVE": "an illustrative amount, since you do not hold this fund", "USER_INPUT": "the amount you entered", "COMPARE": "the same amount used for every fund compared"}


def cost_numbers(fi: FundInputs) -> dict:
    m, cat = fi.meta, fi.category
    key = "terPctDirect" if m.planType == "DIRECT" else "terPctRegular"
    med = category_median(cat, key)
    ter = m.terPct
    cost = fi.amount_inr * ter / 100 if ter is not None else None
    tw = fi.twin
    twin_cost = fi.amount_inr * tw.terPct / 100 if tw and tw.terPct is not None else None
    gap = abs(cost - twin_cost) if cost is not None and twin_cost is not None else None
    return dict(median=med, ter=ter, cost=cost, twin=tw, twin_cost=twin_cost, gap=gap, cat_cost=fi.amount_inr * med / 100 if med is not None else None)


def answer_cost(fi: FundInputs) -> dict:
    m = fi.meta
    q = "What does it cost per year on your amount?"
    n = cost_numbers(fi)
    asof = m.terAsOf or fi.as_of.isoformat()
    if n["twin_cost"] is not None:
        cost_comp = C("PLAN_TWIN", f"{plan_label(fi.twin.planType).capitalize()} plan of the same fund", n["twin_cost"], "INR")
    else:
        cost_comp = C("CATEGORY", f"At the {m.category} median fee", n["cat_cost"], "INR")
    figures = [
        make_figure("expense_ratio", "Yearly fee (expense ratio)", n["ter"], "PCT", src(fi), asof,
                    [C("CATEGORY", f"Median for {plan_label(m.planType)} plans in {m.category}", n["median"], "PCT")], "expense_ratio"),
        make_figure("yearly_cost", "Yearly fee in rupees on your amount", n["cost"], "INR", src(fi), asof, [cost_comp], "expense_ratio"),
        make_figure("twin_gap", "Yearly difference between regular and direct plan", n["gap"], "INR", src(fi), asof,
                    [C("PLAN_TWIN", "Cost of the other plan" if n["twin_cost"] is not None else "No matching plan known", n["twin_cost"], "INR")], "direct_plan" if m.planType == "DIRECT" else "regular_plan"),
    ]
    sentences = [safe(fi, "fnd.cost.yearly", amount=(fi.amount_inr, "INR"), amountNote=(AMOUNT_NOTE[fi.amount_basis], TXT), yearlyCost=(n["cost"], "INR"), ter=(n["ter"], "PCT"),
                      category=(m.category, TXT), planLabel=(plan_label(m.planType), TXT), median=(n["median"], "PCT"))]
    if n["gap"] is not None:
        sentences.append(S("fnd.cost.gap_regular" if m.planType == "REGULAR" else "fnd.cost.gap_direct", twinCost=(n["twin_cost"], "INR"), gap=(n["gap"], "INR")))
    else:
        sentences.append(S("fnd.cost.no_twin"))
    sentences.append(S("fnd.cost.how"))
    return answer("cost", 4, q, sentences, figures, None)


# ---------------------------------------------------------------- 5 recent
def top10_changes(fi: FundInputs) -> Optional[tuple[list[dict], list[dict]]]:
    p = fi.portfolio
    if not p or not p.previousTop10:
        return None
    hold = sorted(p.holdings, key=lambda h: -h["weightPct"])[:10]
    cur = {h["symbol"] or h["name"]: h for h in hold}
    prev = {h.get("symbol") or h["name"]: h for h in p.previousTop10}
    return [cur[k] for k in cur if k not in prev], [prev[k] for k in prev if k not in cur]


def _names(items: list[dict]) -> str:
    ns = [i["name"] for i in items]
    return ns[0] if len(ns) == 1 else (" and ".join(ns) if len(ns) == 2 else ", ".join(ns[:-1]) + " and " + ns[-1])


def answer_recent(fi: FundInputs) -> dict:
    m, p = fi.meta, fi.portfolio
    q = "What changed recently?"
    asof = fi.as_of.isoformat()
    chg = pct_change(m.aumInr1yAgo, m.aumInr)
    figures = [
        make_figure("aum", "Size of the fund (assets under management)", m.aumInr, "INR", src(fi), asof, [C("PREVIOUS_PERIOD", "1 year ago", m.aumInr1yAgo, "INR")], "aum"),
        make_figure("aum_change_1y", "Change in fund size over 1 year", chg, "PCT_CHANGE", src(fi), asof, [C("PREVIOUS_PERIOD", "Fund size a year ago", m.aumInr1yAgo, "INR")], "aum"),
    ]
    sentences = []
    if chg is not None and m.aumInr is not None:
        sentences.append(S("fnd.recent.aum", aum=(m.aumInr, "INR"), aumPrev=(m.aumInr1yAgo, "INR"), change=(chg, "PCT_CHANGE")))
    else:
        sentences.append(S("fnd.generic.na", fundName=(m.name, TXT)))
    ch = top10_changes(fi)
    rows = []
    if ch is None:
        sentences.append(S("fnd.recent.top10_na"))
    elif ch[0] or ch[1]:
        sentences.append(S("fnd.recent.top10", added=(_names(ch[0]) if ch[0] else "no new company", TXT), dropped=(_names(ch[1]) if ch[1] else "no company", TXT)))
        rows += [["Top 10", f"Entered: {h['name']}", f"{format_pct(h['weightPct'])} now"] for h in ch[0]]
        rows += [["Top 10", f"Left: {h['name']}", f"{format_pct(h['weightPct'])} last month"] for h in ch[1]]
    else:
        sentences.append(S("fnd.recent.top10_same"))
    cutoff = (fi.as_of - timedelta(days=183)).isoformat()
    evs = sorted([e for e in (p.events if p else []) + [] if cutoff <= e["date"] <= fi.as_of.isoformat()], key=lambda e: e["date"], reverse=True)
    all_evs = sorted(p.events if p else [], key=lambda e: e["date"], reverse=True)
    if evs:
        sentences.append(S("fnd.recent.event", eventDate=(format_date(evs[0]["date"]), TXT), eventText=(evs[0]["text"], TXT)))
    else:
        sentences.append(S("fnd.recent.event_none"))
    rows += [[format_date(e["date"]), e["text"], e["type"].replace("_", " ").capitalize()] for e in all_evs]
    details = detail_table("Changes in the top 10 since last month, and fund events", ["Date or item", "What changed", "Detail"], rows) if rows else None
    return answer("recent", 5, q, sentences, figures, details)


def build_answers(fi: FundInputs) -> list[dict]:
    return [answer_holdings(fi), answer_performance(fi), answer_bumpiness(fi), answer_cost(fi), answer_recent(fi)]
