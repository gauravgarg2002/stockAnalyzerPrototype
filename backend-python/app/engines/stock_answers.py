"""The five stock answers (ids and order fixed)."""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Optional

from ..formatting import format_date, format_pct, format_times, format_unit
from ..narrative.render import S, TemplateError
from .figures import comparison as C
from .figures import detail_table, make_figure
from .inputs import StockInputs
from .peers import peer_comparison, peer_label, peer_median
from .series import cagr, fast_on_or_before, pct_change, years_before

TXT = "TEXT"


def annual_rows(f) -> list[dict]:
    return sorted(f.annual, key=lambda r: r["periodEnd"])


def quarter_rows(f) -> list[dict]:
    return sorted(f.quarterly, key=lambda r: r["periodEnd"], reverse=True)


def move_word(new: float, old: float) -> str:
    if old == 0 or abs(new / old - 1) < 0.005:
        return "about the same as"
    return "up from" if new > old else "down from"


def verb(rate: Optional[float]) -> str:
    if rate is None or abs(rate) < 0.05:
        return "was flat"
    return "grew" if rate > 0 else "shrank"


def verb_by(rate: Optional[float]) -> str:
    """Verb for 'X <verb> by Y a year' sentences (flat uses 'changed')."""
    if rate is None or abs(rate) < 0.05:
        return "changed"
    return "grew" if rate > 0 else "shrank"


def position(a: Optional[float], b: Optional[float], tol: float = 0.03) -> str:
    if a is None or b is None or b == 0:
        return "about the same as"
    if abs(a / b - 1) <= tol:
        return "about the same as"
    return "above" if a > b else "below"


def ttm_profit(f) -> Optional[float]:
    q = quarter_rows(f)[:4]
    if len(q) < 4:
        return None
    return sum(r["netProfitInr"] for r in q)


def price_asof(si: StockInputs, d: date) -> Optional[tuple[date, float]]:
    if not si.prices or not si.prices.points:
        return None
    pts = [(p[0], p[1]) for p in si.prices.points]
    return fast_on_or_before([p[0] for p in pts], pts, d)


def last_price(si: StockInputs) -> Optional[float]:
    if si.prices and si.prices.points:
        return si.prices.points[-1][1]
    return si.f.lastPrice


def market_cap_now(si: StockInputs) -> Optional[float]:
    p = last_price(si)
    if p is None or not si.f.sharesOutstanding:
        return None
    return p * si.f.sharesOutstanding


def _safe(si: StockInputs, tid: str, **facts) -> dict:
    try:
        return S(tid, **facts)
    except TemplateError:
        return S("stk.generic.na", companyName=(si.f.name, TXT))


def fy_label(row: dict) -> str:
    return row["fy"]


# ---------------------------------------------------------------- 1 business
def answer_business(si: StockInputs) -> dict:
    f, src = si.f, si.f.source
    rows = annual_rows(f)
    sentences, figures, details = [], [], None
    sentences.append(S("stk.business.about", companyName=(f.name, TXT), about=(f.about, TXT)))
    if rows:
        last = rows[-1]
        base = rows[-4] if len(rows) >= 4 else rows[0]
        rev, prev = last["revenueInr"], base["revenueInr"]
        sentences.append(S("stk.business.revenue", revenue=(rev, "INR"), fy=(last["fy"], TXT), change=(move_word(rev, prev), TXT),
                           prevRevenue=(prev, "INR"), prevFy=(base["fy"], TXT)))
        figures.append(make_figure("revenue_fy", f"Revenue, {last['fy']} (Apr {last['periodStart'][:4]}–Mar {last['periodEnd'][:4]})", rev, "INR", src,
                                   last["periodEnd"], [C("PREVIOUS_PERIOD", base["fy"], prev, "INR")], "revenue"))
    segs = f.revenueSegments or []
    if segs:
        top = max(segs, key=lambda s: s["sharePct"])
        sentences.append(S("stk.business.segment", segmentName=(top["name"], TXT), share=(top["sharePct"], "PCT")))
        asof = rows[-1]["periodEnd"] if rows else (f.asOf or si.as_of.isoformat())
        figures.append(make_figure("top_segment_share", "Largest business, share of revenue", top["sharePct"], "PCT", src, asof,
                                   [C("PREVIOUS_PERIOD", "A year earlier", top.get("prevSharePct"), "PCT")], None))
        details = detail_table("Revenue by business", ["Business", "Share of revenue", "A year earlier"],
                               [[s["name"], format_pct(s["sharePct"]), format_pct(s.get("prevSharePct")) if s.get("prevSharePct") is not None else "Not available"] for s in segs])
    return _answer("business", 1, "What does the company do and how does it earn money?", sentences, figures, details)


def _answer(id: str, order: int, question: str, sentences, figures, details) -> dict:
    return {"id": id, "order": order, "question": question, "sentences": sentences, "figures": figures, "details": details}


# ---------------------------------------------------------------- 2 growth
def answer_growth(si: StockInputs) -> dict:
    f, src = si.f, si.f.source
    rows = annual_rows(f)
    sentences, figures = [], []
    if len(rows) < 4:
        return _answer("growth", 2, "Is it growing and profitable?", [_safe(si, "stk.generic.na"), _safe(si, "stk.generic.na")], [], None)
    last, base, prev = rows[-1], rows[-4], rows[-2]
    rev_cagr = cagr(base["revenueInr"], last["revenueInr"], 3)
    prof_cagr = cagr(base["netProfitInr"], last["netProfitInr"], 3)
    margins = [r["operatingProfitInr"] / r["revenueInr"] * 100 for r in rows if r["revenueInr"]]
    margin = last["operatingProfitInr"] / last["revenueInr"] * 100
    own_med = statistics.median(margins)
    roe = last["netProfitInr"] / last["netWorthInr"] * 100 if last["netWorthInr"] else None
    asof = last["periodEnd"]
    figures += [
        make_figure("revenue_cagr_3y", "Revenue growth, yearly average over 3 years", rev_cagr, "PCT", src, asof, [peer_comparison(f, "revenueCagr3yPct", "PCT")], "cagr"),
        make_figure("profit_cagr_3y", "Net profit growth, yearly average over 3 years", prof_cagr, "PCT", src, asof, [peer_comparison(f, "profitCagr3yPct", "PCT")], "cagr"),
        make_figure("operating_margin", "Operating profit as a share of revenue", margin, "PCT", src, asof,
                    [C("OWN_HISTORY", "5-year median", own_med, "PCT"), peer_comparison(f, "operatingMarginPct", "PCT")], "operating_margin"),
        make_figure("roe", "Return on shareholders' money (ROE)", roe, "PCT", src, asof, [peer_comparison(f, "roePct", "PCT")], "roe"),
    ]
    sentences.append(_safe(si, "stk.growth.revenue", verb=(verb_by(rev_cagr), TXT), revenueCagr=(abs(rev_cagr) if rev_cagr is not None else None, "PCT"),
                           peerGroup=(f.peerGroup.get("name", "industry"), TXT), peerRevenueCagr=(peer_median(f, "revenueCagr3yPct"), "PCT")))
    if prof_cagr is not None:
        sentences.append(_safe(si, "stk.growth.profit", verb=(verb_by(prof_cagr), TXT), profitCagr=(abs(prof_cagr), "PCT"),
                               peerProfitCagr=(peer_median(f, "profitCagr3yPct"), "PCT"), netProfit=(last["netProfitInr"], "INR"), fy=(last["fy"], TXT)))
    else:
        sentences.append(S("stk.growth.profit_na", netProfit=(last["netProfitInr"], "INR"), fy=(last["fy"], TXT),
                           prevNetProfit=(prev["netProfitInr"], "INR"), prevFy=(prev["fy"], TXT)))
    sentences.append(_safe(si, "stk.growth.margin_roe", fy=(last["fy"], TXT), operatingMargin=(margin, "PCT"), ownMedian=(own_med, "PCT"),
                           peerMargin=(peer_median(f, "operatingMarginPct"), "PCT"), roe=(roe, "PCT"), peerRoe=(peer_median(f, "roePct"), "PCT")))
    details = detail_table("Five years: revenue, operating profit, net profit and margin",
                           ["Year", "Revenue", "Operating profit", "Net profit", "Operating margin"],
                           [[r["fy"], format_unit(r["revenueInr"], "INR"), format_unit(r["operatingProfitInr"], "INR"), format_unit(r["netProfitInr"], "INR"),
                             format_pct(r["operatingProfitInr"] / r["revenueInr"] * 100 if r["revenueInr"] else None)] for r in reversed(rows)])
    return _answer("growth", 2, "Is it growing and profitable?", sentences, figures, details)


# ---------------------------------------------------------------- 3 safety
def answer_safety(si: StockInputs) -> dict:
    f, src = si.f, si.f.source
    rows = annual_rows(f)
    q = "Is it financially safe?"
    if len(rows) < 4:
        return _answer("safety", 3, q, [_safe(si, "stk.generic.na"), _safe(si, "stk.generic.na")], [], None)
    last, base = rows[-1], rows[-4]
    asof = last["periodEnd"]
    sentences, figures = [], []
    roe = last["netProfitInr"] / last["netWorthInr"] * 100 if last["netWorthInr"] else None
    if f.isFinancial:
        figures += [
            make_figure("net_worth", "Shareholders' money (net worth)", last["netWorthInr"], "INR", src, asof, [C("PREVIOUS_PERIOD", base["fy"], base["netWorthInr"], "INR")], "net_worth"),
            make_figure("roe", "Return on shareholders' money (ROE)", roe, "PCT", src, asof, [peer_comparison(f, "roePct", "PCT")], "roe"),
        ]
        sentences = [
            S("stk.safety.fin_intro", companyName=(f.name, TXT)),
            S("stk.safety.fin_networth", netWorth=(last["netWorthInr"], "INR"), fy=(last["fy"], TXT), change=(move_word(last["netWorthInr"], base["netWorthInr"]), TXT),
              prevNetWorth=(base["netWorthInr"], "INR"), prevFy=(base["fy"], TXT)),
            _safe(si, "stk.safety.fin_roe", roe=(roe, "PCT"), fy=(last["fy"], TXT), peerRoe=(peer_median(f, "roePct"), "PCT")),
        ]
    else:
        dte = [r["totalDebtInr"] / r["netWorthInr"] for r in rows if r["netWorthInr"]]
        dte_now = last["totalDebtInr"] / last["netWorthInr"] if last["netWorthInr"] else None
        own = statistics.median(dte) if dte else None
        cov = last["operatingProfitInr"] / last["interestInr"] if last["interestInr"] else None
        figures += [
            make_figure("total_debt", "Total debt", last["totalDebtInr"], "INR", src, asof, [C("PREVIOUS_PERIOD", base["fy"], base["totalDebtInr"], "INR")], "debt"),
            make_figure("debt_to_equity", "Debt compared with shareholders' money", dte_now, "TIMES", src, asof,
                        [C("OWN_HISTORY", "5-year median", own, "TIMES"), peer_comparison(f, "debtToEquity", "TIMES")], "debt_to_equity"),
            make_figure("interest_coverage", "Operating profit compared with yearly interest", cov, "TIMES", src, asof, [peer_comparison(f, "interestCoverage", "TIMES")], "interest_coverage"),
            make_figure("cash", "Cash", last["cashInr"], "INR", src, asof, [C("PREVIOUS_PERIOD", base["fy"], base["cashInr"], "INR")], None),
        ]
        sentences.append(S("stk.safety.debt", debt=(last["totalDebtInr"], "INR"), fy=(last["fy"], TXT), change=(move_word(last["totalDebtInr"], base["totalDebtInr"]), TXT),
                           prevDebt=(base["totalDebtInr"], "INR"), prevFy=(base["fy"], TXT), cash=(last["cashInr"], "INR")))
        sentences.append(_safe(si, "stk.safety.ratio", debtToEquity=(dte_now, "TIMES"), ownMedian=(own, "TIMES"), peerMedian=(peer_median(f, "debtToEquity"), "TIMES")))
        if cov is not None:
            sentences.append(_safe(si, "stk.safety.coverage", coverage=(cov, "TIMES"), peerMedian=(peer_median(f, "interestCoverage"), "TIMES")))
        else:
            sentences.append(S("stk.safety.coverage_none", fy=(last["fy"], TXT)))
    details = detail_table("Five years: debt, cash, net worth and interest", ["Year", "Total debt", "Cash", "Net worth", "Interest paid"],
                           [[r["fy"], format_unit(r["totalDebtInr"], "INR"), format_unit(r["cashInr"], "INR"), format_unit(r["netWorthInr"], "INR"),
                             format_unit(r["interestInr"], "INR")] for r in reversed(rows)])
    return _answer("safety", 3, q, sentences, figures, details)


# ---------------------------------------------------------------- 4 price
def valuation_median(f, key: str) -> Optional[float]:
    vals = [v[key] for v in f.valuationHistory if v.get(key) is not None]
    return statistics.median(vals) if vals else None


def current_pe(si: StockInputs) -> Optional[float]:
    p, t, sh = last_price(si), ttm_profit(si.f), si.f.sharesOutstanding
    if p is None or t is None or t <= 0 or not sh:
        return None
    return p / (t / sh)


def current_pb(si: StockInputs) -> Optional[float]:
    rows = annual_rows(si.f)
    p, sh = last_price(si), si.f.sharesOutstanding
    if p is None or not rows or not sh or rows[-1]["netWorthInr"] <= 0:
        return None
    return p / (rows[-1]["netWorthInr"] / sh)


def answer_price(si: StockInputs) -> dict:
    f, src = si.f, si.f.source
    q = "How is it priced against its own history and its peers?"
    pe, pb = current_pe(si), current_pb(si)
    own_pe, own_pb = valuation_median(f, "pe"), valuation_median(f, "pb")
    cap = market_cap_now(si)
    ago = price_asof(si, years_before(si.as_of, 1))
    cap_prev = ago[1] * f.sharesOutstanding if ago and f.sharesOutstanding else None
    asof = si.as_of.isoformat()
    psrc = si.prices.source if si.prices else src
    figures = [
        make_figure("pe", "Price to yearly profit (P/E)", pe, "TIMES", src, asof, [C("OWN_HISTORY", "5-year median", own_pe, "TIMES"), peer_comparison(f, "pe", "TIMES")], "pe_ratio"),
        make_figure("pb", "Price to shareholders' money (P/B)", pb, "TIMES", src, asof, [C("OWN_HISTORY", "5-year median", own_pb, "TIMES"), peer_comparison(f, "pb", "TIMES")], "pb_ratio"),
        make_figure("market_cap", "Market value of the company", cap, "INR", psrc, asof, [C("PREVIOUS_PERIOD", "1 year ago", cap_prev, "INR")], "market_cap"),
        make_figure("dividend_yield", "Dividend yield", f.dividendYieldPct, "PCT", src, asof, [peer_comparison(f, "dividendYieldPct", "PCT")], "dividend_yield"),
    ]
    sentences = []
    if pe is not None:
        sentences.append(_safe(si, "stk.price.pe", pe=(pe, "TIMES"), ownPos=(position(pe, own_pe), TXT), ownPe=(own_pe, "TIMES"),
                               peerPos=(position(pe, peer_median(f, "pe")), TXT), peerPe=(peer_median(f, "pe"), "TIMES")))
    else:
        sentences.append(_safe(si, "stk.price.pe_loss", peerPe=(peer_median(f, "pe"), "TIMES")))
    if pb is not None:
        sentences.append(_safe(si, "stk.price.pb", pb=(pb, "TIMES"), ownPos=(position(pb, own_pb), TXT), ownPb=(own_pb, "TIMES"),
                               peerPos=(position(pb, peer_median(f, "pb")), TXT), peerPb=(peer_median(f, "pb"), "TIMES")))
    else:
        sentences.append(_safe(si, "stk.generic.na"))
    sentences.append(_safe(si, "stk.price.cap", marketCap=(cap, "INR"), prevMarketCap=(cap_prev, "INR"), dividendYield=(f.dividendYieldPct, "PCT"),
                           peerYield=(peer_median(f, "dividendYieldPct"), "PCT")))
    sept = [v for v in f.valuationHistory if v["monthEnd"][5:7] == "09"]
    details = detail_table("Price to profit and to shareholders' money, September of each year", ["Month end", "P/E", "P/B"],
                           [[format_date(v["monthEnd"]), format_unit(v["pe"], "TIMES") if v.get("pe") is not None else "Not available",
                             format_unit(v["pb"], "TIMES") if v.get("pb") is not None else "Not available"] for v in reversed(sept)]) if sept else None
    return _answer("price", 4, q, sentences, figures, details)


# ---------------------------------------------------------------- 5 recent
def answer_recent(si: StockInputs) -> dict:
    f, src = si.f, si.f.source
    q = "What changed recently?"
    qs = quarter_rows(f)
    sentences, figures = [], []
    if len(qs) >= 6:
        cur, yago = qs[0], qs[4]
        pq, pyago = qs[1], qs[5]
        rev_yoy = pct_change(yago["revenueInr"], cur["revenueInr"])
        prof_yoy = pct_change(yago["netProfitInr"], cur["netProfitInr"]) if yago["netProfitInr"] > 0 else None
        prev_rev = pct_change(pyago["revenueInr"], pq["revenueInr"])
        prev_prof = pct_change(pyago["netProfitInr"], pq["netProfitInr"]) if pyago["netProfitInr"] > 0 else None
        figures += [
            make_figure("quarter_revenue_yoy", f"Revenue, {cur['label']}, against the same quarter a year earlier", rev_yoy, "PCT_CHANGE", src, cur["periodEnd"],
                        [C("PREVIOUS_PERIOD", f"{pq['label']}, same measure", prev_rev, "PCT_CHANGE")], "revenue"),
            make_figure("quarter_profit_yoy", f"Net profit, {cur['label']}, against the same quarter a year earlier", prof_yoy, "PCT_CHANGE", src, cur["periodEnd"],
                        [C("PREVIOUS_PERIOD", f"{pq['label']}, same measure", prev_prof, "PCT_CHANGE")], "net_profit"),
        ]
        if prof_yoy is not None:
            sentences.append(S("stk.recent.results", quarterLabel=(cur["label"], TXT), revenueYoy=(rev_yoy, "PCT_CHANGE"), profitYoy=(prof_yoy, "PCT_CHANGE"),
                               resultsDate=(format_date(cur["resultsDate"]), TXT)))
        else:
            sentences.append(S("stk.recent.results_profit_na", quarterLabel=(cur["label"], TXT), revenueYoy=(rev_yoy, "PCT_CHANGE"),
                               resultsDate=(format_date(cur["resultsDate"]), TXT)))
    else:
        sentences.append(S("stk.recent.results_none"))
    ch90 = None
    nifty90 = None
    p_now, p_then = price_asof(si, si.as_of), price_asof(si, si.as_of - timedelta(days=90))
    if p_now and p_then:
        ch90 = pct_change(p_then[1], p_now[1])
        if si.benchmark and si.benchmark.points:
            bpts = [(p[0], p[1]) for p in si.benchmark.points]
            bd = [p[0] for p in bpts]
            b1, b0 = fast_on_or_before(bd, bpts, p_now[0]), fast_on_or_before(bd, bpts, p_then[0])
            if b1 and b0:
                nifty90 = pct_change(b0[1], b1[1])
        figures.append(make_figure("price_change_90d", "Share price change in the last 90 days", ch90, "PCT_CHANGE", si.prices.source if si.prices else src, si.as_of.isoformat(),
                                   [C("INDEX", f"{si.benchmark_name}, same dates", nifty90, "PCT_CHANGE")], None))
        if nifty90 is not None:
            sentences.append(S("stk.recent.price", priceChange=(ch90, "PCT_CHANGE"), niftyChange=(nifty90, "PCT_CHANGE")))
        else:
            sentences.append(S("stk.recent.price_na"))
    else:
        sentences.append(S("stk.recent.price_na"))
    cutoff = (si.as_of - timedelta(days=120)).isoformat()
    evs = [e for e in sorted(f.events, key=lambda e: e["date"], reverse=True) if e["type"] != "RESULTS" and cutoff <= e["date"] <= si.as_of.isoformat()]
    if evs:
        sentences.append(S("stk.recent.event", eventDate=(format_date(evs[0]["date"]), TXT), eventText=(evs[0]["text"], TXT)))
    else:
        sentences.append(S("stk.recent.event_none"))
    ev_all = sorted([e for e in f.events if e["date"] <= si.as_of.isoformat()], key=lambda e: e["date"], reverse=True)[:8]
    details = detail_table("Recent company events", ["Date", "Event"], [[format_date(e["date"]), e["text"]] for e in ev_all]) if ev_all else None
    return _answer("recent", 5, q, sentences[:3], figures, details)


def build_answers(si: StockInputs) -> list[dict]:
    return [answer_business(si), answer_growth(si), answer_safety(si), answer_price(si), answer_recent(si)]
