"""The eight fixed stock facts (ids and order fixed)."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

from ..formatting import format_date, format_pct, format_unit
from ..narrative.render import S, TemplateError
from .figures import comparison as C
from .figures import detail_table, make_figure
from .inputs import StockInputs
from .peers import peer_comparison, peer_median
from .series import avg_daily_traded_value, fast_on_or_before, pct_change, years_before
from .stock_answers import annual_rows, last_price, market_cap_now, price_asof

TXT = "TEXT"
BAND_LABEL = {"LARGE": "large cap", "MID": "mid cap", "SMALL": "small cap", "MICRO": "micro cap"}
BAND_TITLE = {"LARGE": "Large cap", "MID": "Mid cap", "SMALL": "Small cap", "MICRO": "Micro cap"}


def _fact(id: str, order: int, title: str, term: Optional[str], available: bool, sentences, figures, details=None) -> dict:
    return {"id": id, "order": order, "title": title, "termId": term, "available": available, "sentences": sentences, "figures": figures, "details": details}


def _na(si: StockInputs, id: str, order: int, title: str, term: Optional[str], tid: str, **facts) -> dict:
    return _fact(id, order, title, term, False, [S(tid, **facts)], [])


def fact_promoter_holding(si: StockInputs) -> dict:
    f = si.f
    sh = sorted(f.shareholding, key=lambda r: r["quarterEnd"], reverse=True)
    title = "Promoter holding"
    if len(sh) < 2:
        return _na(si, "promoter_holding", 1, title, "promoter_holding", "stk.generic.na", companyName=(f.name, TXT))
    cur, old = sh[0], sh[min(4, len(sh) - 1)]
    p, o = cur["promoterPct"], old["promoterPct"]
    fig = make_figure("promoter_holding", "Promoter holding", p, "PCT", f.source, cur["quarterEnd"], [C("PREVIOUS_PERIOD", "Four quarters ago", o, "PCT")], "promoter_holding")
    if p == 0 and o == 0:
        s = [S("stk.fact.promoter_holding_none", companyName=(f.name, TXT))]
    else:
        d = "unchanged from" if abs(p - o) < 0.1 else ("up from" if p > o else "down from")
        s = [S("stk.fact.promoter_holding", holding=(p, "PCT"), direction=(d, TXT), prevHolding=(o, "PCT"))]
    details = detail_table("Promoter holding by quarter", ["Quarter end", "Promoter holding", "Pledged (of promoter shares)"],
                           [[format_date(r["quarterEnd"]), format_pct(r["promoterPct"]), format_pct(r["pledgedPctOfPromoter"])] for r in sh])
    return _fact("promoter_holding", 1, title, "promoter_holding", True, s, [fig], details)


def fact_promoter_pledge(si: StockInputs) -> dict:
    f = si.f
    sh = sorted(f.shareholding, key=lambda r: r["quarterEnd"], reverse=True)
    title = "Promoter pledge"
    if len(sh) < 2:
        return _na(si, "promoter_pledge", 2, title, "promoter_pledge", "stk.generic.na", companyName=(f.name, TXT))
    cur, old = sh[0], sh[min(4, len(sh) - 1)]
    p, o = cur["pledgedPctOfPromoter"], old["pledgedPctOfPromoter"]
    fig = make_figure("promoter_pledge", "Promoter shares pledged (share of promoter shares)", p, "PCT", f.source, cur["quarterEnd"],
                      [C("PREVIOUS_PERIOD", "Four quarters ago", o, "PCT")], "promoter_pledge")
    if cur["promoterPct"] == 0:
        s = [S("stk.fact.promoter_pledge_nopromoter")]
    elif p == 0 and o == 0:
        s = [S("stk.fact.promoter_pledge_none")]
    else:
        s = [S("stk.fact.promoter_pledge", pledge=(p, "PCT"), prevPledge=(o, "PCT"))]
    return _fact("promoter_pledge", 2, title, "promoter_pledge", True, s, [fig])


def fact_profit_last_3y(si: StockInputs) -> dict:
    f = si.f
    rows = annual_rows(f)
    title = "Profit or loss in each of the last three years"
    if len(rows) < 3:
        return _fact("profit_last_3y", 3, title, "net_profit", False, [S("stk.fact.profit_na")], [])
    figs = []
    last3 = rows[-3:]
    for i, r in enumerate(last3):
        prev = rows[len(rows) - 3 + i - 1] if len(rows) - 3 + i - 1 >= 0 else None
        a, b = r["periodStart"][:4], r["periodEnd"][:4]
        figs.append(make_figure(f"net_profit_y{i + 1}", f"{r['fy']} (Apr {a}–Mar {b})", r["netProfitInr"], "INR", f.source, r["periodEnd"],
                                [C("PREVIOUS_PERIOD", prev["fy"] if prev else "Previous year", prev["netProfitInr"] if prev else None, "INR")], "net_profit"))
    def pl(v: float) -> str:
        return f"a profit of {format_unit(v, 'INR')}" if v >= 0 else f"a loss of {format_unit(abs(v), 'INR')}"

    s = [S("stk.fact.profit", profit1=(pl(last3[0]["netProfitInr"]), TXT), fy1=(last3[0]["fy"], TXT), profit2=(pl(last3[1]["netProfitInr"]), TXT),
           fy2=(last3[1]["fy"], TXT), profit3=(pl(last3[2]["netProfitInr"]), TXT), fy3=(last3[2]["fy"], TXT))]
    losses = sum(1 for r in last3 if r["netProfitInr"] < 0)
    s.append(S("stk.fact.profit_loss", lossCount=(losses, "COUNT")) if losses else S("stk.fact.profit_all"))
    return _fact("profit_last_3y", 3, title, "net_profit", True, s, figs)


def fact_debt_to_earnings(si: StockInputs) -> dict:
    f = si.f
    title = "Debt against yearly earnings"
    rows = annual_rows(f)
    if f.isFinancial:
        return _fact("debt_to_earnings", 4, title, "debt_to_profit", False, [S("stk.fact.debt_financial", companyName=(f.name, TXT))], [])
    if len(rows) < 4:
        return _na(si, "debt_to_earnings", 4, title, "debt_to_profit", "stk.generic.na", companyName=(f.name, TXT))
    last, base = rows[-1], rows[-4]
    peer = peer_comparison(f, "debtToProfit", "TIMES")
    old = base["totalDebtInr"] / base["netProfitInr"] if base["netProfitInr"] > 0 else None
    comps = [C("OWN_HISTORY", f"3 years earlier ({base['fy']})", old, "TIMES"), peer]
    if last["netProfitInr"] <= 0:
        fig = make_figure("debt_to_profit", "Total debt compared with yearly net profit", None, "TIMES", f.source, last["periodEnd"], comps, "debt_to_profit")
        s = [S("stk.fact.debt_loss", loss=(abs(last["netProfitInr"]), "INR"), fy=(last["fy"], TXT), debt=(last["totalDebtInr"], "INR"))]
        return _fact("debt_to_earnings", 4, title, "debt_to_profit", True, s, [fig])
    ratio = last["totalDebtInr"] / last["netProfitInr"]
    fig = make_figure("debt_to_profit", "Total debt compared with yearly net profit", ratio, "TIMES", f.source, last["periodEnd"], comps, "debt_to_profit")
    s = [S("stk.fact.debt_to_profit", debt=(last["totalDebtInr"], "INR"), ratio=(ratio, "TIMES"), profit=(last["netProfitInr"], "INR"))]
    try:
        s.append(S("stk.fact.debt_to_profit_cmp", ownPrev=(old, "TIMES"), peerMedian=(peer["value"], "TIMES")))
    except TemplateError:
        pass
    return _fact("debt_to_earnings", 4, title, "debt_to_profit", True, s, [fig])


def fact_price_move_30d(si: StockInputs) -> dict:
    f = si.f
    title = "Price move in the last 30 days"
    now = price_asof(si, si.as_of)
    then = price_asof(si, si.as_of - timedelta(days=30))
    first = si.prices.points[0][0] if si.prices and si.prices.points else None
    if not now or not then or first is None or first > si.as_of - timedelta(days=30):
        return _fact("price_move_30d", 5, title, None, False, [S("stk.fact.price_move_na")], [])
    ch = pct_change(then[1], now[1])
    nifty = None
    if si.benchmark and si.benchmark.points:
        bp = [(p[0], p[1]) for p in si.benchmark.points]
        bd = [p[0] for p in bp]
        b1, b0 = fast_on_or_before(bd, bp, now[0]), fast_on_or_before(bd, bp, then[0])
        if b1 and b0:
            nifty = pct_change(b0[1], b1[1])
    src = si.prices.source
    start = si.as_of - timedelta(days=30)
    res = [e for e in f.events if e["type"] == "RESULTS" and start < __import__("datetime").date.fromisoformat(e["date"]) <= si.as_of]
    res_txt = f"Yes, on {format_date(max(e['date'] for e in res))}" if res else "No"
    figs = [make_figure("price_change_30d", "Share price change in the last 30 days", ch, "PCT_CHANGE", src, si.as_of.isoformat(),
                        [C("INDEX", f"{si.benchmark_name}, same dates", nifty, "PCT_CHANGE")], None),
            make_figure("results_in_window", "Results announced in this period", res_txt, "TEXT", f.source, si.as_of.isoformat(), [], None)]
    s = [S("stk.fact.price_move", priceChange=(ch, "PCT_CHANGE"), niftyChange=(nifty, "PCT_CHANGE")) if nifty is not None
         else S("stk.fact.price_move_only", priceChange=(ch, "PCT_CHANGE"))]
    s.append(S("stk.fact.results_yes", resultsDate=(format_date(max(e["date"] for e in res)), TXT)) if res else S("stk.fact.results_no"))
    return _fact("price_move_30d", 5, title, None, True, s, figs)


def fact_avg_traded_value(si: StockInputs) -> dict:
    f = si.f
    title = "Average daily trading value"
    pts = si.prices.points if si.prices else []
    cur = avg_daily_traded_value(pts, 20, si.as_of)
    if cur is None:
        return _fact("avg_traded_value", 6, title, "avg_daily_traded_value", False, [S("stk.fact.avg_traded_na")], [])
    prev = avg_daily_traded_value(pts, 20, years_before(si.as_of, 1))
    peer = peer_median(f, "avgDailyTradedValueInr")
    fig = make_figure("avg_daily_traded_value", "Average daily trading value (last 20 sessions)", cur, "INR", si.prices.source, si.as_of.isoformat(),
                      [C("OWN_HISTORY", "Same 20 sessions a year earlier", prev, "INR"), peer_comparison(f, "avgDailyTradedValueInr", "INR")], "avg_daily_traded_value")
    s = [S("stk.fact.avg_traded", adtv=(cur, "INR"))]
    if prev is not None and peer is not None:
        s.append(S("stk.fact.avg_traded_cmp", prevAdtv=(prev, "INR"), peerAdtv=(peer, "INR")))
    return _fact("avg_traded_value", 6, title, "avg_daily_traded_value", True, s, [fig])


def band_cutoff_inr(si: StockInputs, band: str) -> Optional[float]:
    sb = si.size_bands
    crore = {"LARGE": sb["largeMinCrore"], "MID": sb["midMinCrore"], "SMALL": sb["smallMinCrore"], "MICRO": 0}[band]
    return crore * 1e7


def fact_size_band(si: StockInputs) -> dict:
    f = si.f
    title = "Size band"
    cap = market_cap_now(si)
    cut = band_cutoff_inr(si, f.sizeBand)
    label = BAND_LABEL[f.sizeBand]
    asof = si.as_of.isoformat()
    src = si.prices.source if si.prices else f.source
    text = f"{BAND_TITLE[f.sizeBand]}, rank {f.marketCapRank} by market value" if f.marketCapRank else BAND_TITLE[f.sizeBand]
    figs = [make_figure("market_cap", "Market value of the company", cap, "INR", src, asof,
                        [C("THRESHOLD", f"Lowest market value counted as {label}", cut, "INR")], "market_cap"),
            make_figure("size_band", "Size band", text, "TEXT", src, asof, [], "size_band")]
    s = [S("stk.fact.size_band", companyName=(f.name, TXT), bandLabel=(label, TXT), marketCap=(cap, "INR"))]
    if f.marketCapRank:
        if cut:
            s.append(S("stk.fact.size_rank", rank=(f.marketCapRank, "COUNT"), bandLabel=(label, TXT), cutoff=(cut, "INR")))
        else:
            s.append(S("stk.fact.size_rank_nolimit", rank=(f.marketCapRank, "COUNT"), bandLabel=(label, TXT)))
    return _fact("size_band", 7, title, "size_band", True, s, figs)


def surveillance_status_text(entries) -> str:
    parts = []
    for e in entries:
        m = re.match(r"(Long-term |Short-term )?(ASM|GSM|ESM)\s+Stage\s+([IV]+)", e.stage, re.I)
        if m:
            term = (m.group(1) or "").strip().lower()
            txt = f"{m.group(2).upper()} {term + ' ' if term else ''}stage {m.group(3).upper()}"
        else:
            txt = f"{e.list} {e.stage}"
        if e.since:
            txt += f" since {format_date(e.since)}"
        parts.append(txt)
    return "; ".join(parts)


def fact_surveillance(si: StockInputs) -> dict:
    f = si.f
    title = "NSE surveillance lists (ASM, GSM, ESM)"
    if si.surveillance is None:
        return _fact("surveillance", 8, title, "surveillance_asm", False, [S("stk.fact.surv_na")], [])
    asof = si.as_of.isoformat()
    src = "Sample data" if f.source == "Sample data" else "NSE"
    if si.surveillance:
        status = surveillance_status_text(si.surveillance)
        s = [S("stk.fact.surv_on", companyName=(f.name, TXT), status=(status, TXT)), S("stk.fact.surv_note")]
        term = "surveillance_" + si.surveillance[0].list.lower()
    else:
        status = "Not on ASM, GSM or ESM lists"
        s = [S("stk.fact.surv_off", companyName=(f.name, TXT)), S("stk.fact.surv_note")]
        term = "surveillance_asm"
    fig = make_figure("surveillance_status", "Surveillance list status", status, "TEXT", src, asof, [], term)
    return _fact("surveillance", 8, title, term, True, s, [fig])


def build_facts(si: StockInputs) -> list[dict]:
    return [fact_promoter_holding(si), fact_promoter_pledge(si), fact_profit_last_3y(si), fact_debt_to_earnings(si),
            fact_price_move_30d(si), fact_avg_traded_value(si), fact_size_band(si), fact_surveillance(si)]
