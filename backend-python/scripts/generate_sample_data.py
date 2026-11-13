#!/usr/bin/env python3
"""Deterministic sample-data generator (stdlib only). Seed 20261030.

Usage: python scripts/generate_sample_data.py [output_dir]
Default output: backend-python/app/data/sample. Figures are illustrative, not real.
"""
from __future__ import annotations

import json
import math
import random
import sys
import zlib
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_specs as SP  # noqa: E402

SEED = 20261030
SERIES_START = date(2016, 10, 31)
ASOF = date(2026, 10, 30)
STOCK_START = date(2021, 11, 1)
SQ252 = math.sqrt(252.0)


def bdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def sub_rng(key: str) -> random.Random:
    return random.Random(SEED ^ zlib.crc32(key.encode()))


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, 1)


def month_end(y: int, m: int) -> date:
    return add_months(date(y, m, 1), 1) - timedelta(days=1)


# ---------------------------------------------------------------- market factor
def make_market(days: list[date]) -> list[float]:
    master = random.Random(SEED)
    shock_a, shock_b = date(2022, 1, 17), date(2022, 6, 17)
    rec_a, rec_b = date(2022, 6, 20), date(2022, 12, 30)
    n_shock = sum(1 for d in days if shock_a <= d <= shock_b)
    n_rec = sum(1 for d in days if rec_a <= d <= rec_b)
    m = []
    for d in days:
        r = 0.12 / 252 + 0.13 / SQ252 * master.gauss(0, 1)
        if shock_a <= d <= shock_b:
            r += math.log(0.82) / n_shock
        elif rec_a <= d <= rec_b:
            r += math.log(1.18) / n_rec
        m.append(r)
    return m


def fit_total(rets: list[float], total_log: float) -> list[float]:
    """Shift returns by a constant so their sum equals total_log."""
    c = (total_log - sum(rets)) / len(rets)
    return [r + c for r in rets]


def path_from_rets(rets: list[float], end_value: float) -> list[float]:
    """rets[i] is the log return into day i (rets[0] ignored); scaled so the last value == end_value."""
    lv, acc = [0.0], 0.0
    for r in rets[1:]:
        acc += r
        lv.append(acc)
    scale = end_value / math.exp(lv[-1])
    return [scale * math.exp(x) for x in lv]


# ---------------------------------------------------------------- stocks
SEASON = [0.236, 0.244, 0.252, 0.268]
Q_ENDS = [date(2024, 6, 30), date(2024, 9, 30), date(2024, 12, 31), date(2025, 3, 31), date(2025, 6, 30),
          date(2025, 9, 30), date(2025, 12, 31), date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)]
Q_NAMES = {3: "January–March", 6: "April–June", 9: "July–September", 12: "October–December"}
FY_ENDS = [date(2022, 3, 31), date(2023, 3, 31), date(2024, 3, 31), date(2025, 3, 31), date(2026, 3, 31)]
CR = 1e7


def lerp(a: float, b: float, i: int, n: int = 4) -> float:
    return a + (b - a) * i / n


def qlabel(d: date) -> str:
    return f"{Q_NAMES[d.month]} {d.year}"


def fy_name(i: int) -> str:
    return f"FY{2022 + i}"


def build_stock(s: dict, days: list[date], market: list[float], idx: int) -> tuple[dict, list[tuple[date, float, int]]]:
    sym = s["symbol"]
    rng = sub_rng(sym)
    shares = round(s["mcap"] * CR / s["price"])
    # price path: simulate from 2021-10-29 (internal) to ASOF
    first = date(2021, 10, 29)
    sd = [d for d in days if d >= first]
    mk = market[len(days) - len(sd):]
    mean_m = sum(mk) / len(mk)
    idio = max(0.10, math.sqrt(max(s["vol"] ** 2 - (s["beta"] * 0.13) ** 2, 0.0)))
    rets = [s["beta"] * (m - mean_m) + idio / SQ252 * rng.gauss(0, 1) for m in mk]
    rets = fit_total(rets[1:], math.log(s["mult"]))
    rets = [0.0] + rets
    closes = path_from_rets(rets, s["price"])
    closes = [round(c, 2) for c in closes]
    closes[-1] = s["price"]
    mean_sh = s["adtv"] * CR / s["price"]
    series = []
    for d, c in zip(sd, closes):
        v = max(1, int(mean_sh * math.exp(0.35 * rng.gauss(0, 1) - 0.06)))
        series.append((d, c, v))
    # financials
    rev = [0.0] * 5
    rev[4] = s["rev"]
    g = s["growth"]
    rev[3] = rev[4] / (1 + g[0] / 100)
    rev[2] = rev[3] / (1 + g[1] / 100)
    rev[1] = rev[2] / (1 + g[2] / 100)
    rev[0] = rev[1] / (1 + g[3] / 100)
    annual = []
    eps_list, bvps_list = [], []
    for i in range(5):
        opm = lerp(s["opm"][0], s["opm"][1], i) + rng.uniform(-0.4, 0.4)
        npm = lerp(s["npm"][0], s["npm"][1], i) + rng.uniform(-0.25, 0.25)
        if s.get("loss_year") == fy_name(i):
            npm = -3.5
        if i == 4:
            opm, npm = s["opm"][1], s["npm"][1]
        op = rev[i] * opm / 100
        npf = rev[i] * npm / 100
        debt = lerp(*s["debt"], i) * (1 + rng.uniform(-0.03, 0.03)) if i not in (0, 4) else s["debt"][0 if i == 0 else 1]
        cash = lerp(*s["cash"], i) * (1 + rng.uniform(-0.04, 0.04)) if i not in (0, 4) else s["cash"][0 if i == 0 else 1]
        nw = lerp(*s["nw"], i) * (1 + rng.uniform(-0.02, 0.02)) if i not in (0, 4) else s["nw"][0 if i == 0 else 1]
        intr = lerp(*s["intr"], i) * (1 + rng.uniform(-0.04, 0.04)) if i not in (0, 4) else s["intr"][0 if i == 0 else 1]
        eps = npf * CR / shares
        eps_list.append(eps)
        bvps_list.append(nw * CR / shares)
        annual.append({
            "fy": fy_name(i), "periodStart": f"{2021 + i}-04-01", "periodEnd": FY_ENDS[i].isoformat(),
            "revenueInr": round(rev[i] * CR), "operatingProfitInr": round(op * CR), "netProfitInr": round(npf * CR),
            "totalDebtInr": round(debt * CR), "cashInr": round(cash * CR), "netWorthInr": round(nw * CR),
            "interestInr": round(intr * CR), "eps": round(eps, 2)})
    annual.reverse()  # latest first (FY2026 first), as in the contract example
    # quarterly
    qrev = [0.0] * 10
    qnp = [0.0] * 10
    a_rev = {3: rev[3], 4: rev[4]}
    np_ = {3: annual[1]["netProfitInr"] / CR, 4: annual[0]["netProfitInr"] / CR}
    for fy, base in ((3, 0), (4, 4)):
        w = [x * (1 + rng.uniform(-0.02, 0.02)) for x in SEASON]
        tot = sum(w)
        for k in range(4):
            qrev[base + k] = a_rev[fy] * w[k] / tot
            qnp[base + k] = np_[fy] * w[k] / tot * (1 + rng.uniform(-0.04, 0.04))
        adj = np_[fy] / sum(qnp[base:base + 4])
        for k in range(4):
            qnp[base + k] *= adj
    rg = g[0] / 100 + rng.uniform(-0.01, 0.01)
    pg = (np_[4] / np_[3] - 1) if np_[3] > 0 else 0.1
    pg = max(-0.3, min(0.4, pg)) + rng.uniform(-0.02, 0.02)
    for k, src in ((8, 4), (9, 5)):
        qrev[k] = qrev[src] * (1 + rg)
        qnp[k] = qnp[src] * (1 + pg)
    results_future = s["qdate"] > ASOF.isoformat()
    top = 8 if results_future else 9
    quarterly = []
    rdates = {}
    for q in range(top, top - 8, -1):
        pe = Q_ENDS[q]
        if q == 9 and not results_future:
            rd = date.fromisoformat(s["qdate"])
        else:
            rd = pe + timedelta(days=rng.randint(14, 30)) if q != 8 else pe + timedelta(days=rng.randint(22, 36))
        if q == 8 and results_future:
            rd = date(2026, 7, rng.randint(24, 31)) if s["qdate"] <= "2026-11-06" else date(2026, 8, rng.randint(5, 12))
        rdates[q] = rd
        quarterly.append({"label": qlabel(pe), "periodEnd": pe.isoformat(), "resultsDate": rd.isoformat(),
                          "revenueInr": round(qrev[q] * CR), "netProfitInr": round(qnp[q] * CR)})
    # shareholding
    sh_dates = ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"]
    shareholding = []
    for k in range(5):
        p, pl, f, di = s["promoter"][k], s["pledge"][k], s["fii"][k], s["dii"][k]
        shareholding.append({"quarterEnd": sh_dates[k], "promoterPct": p, "pledgedPctOfPromoter": float(pl),
                             "fiiPct": f, "diiPct": di, "publicPct": round(100 - p - f - di, 2)})
    # valuation history: 60 month-ends 2021-10 .. 2026-09
    by_date = {d: c for d, c, _ in series}
    sd_list = [d for d, _, _ in series]
    fy_pts = [date(2021, 3, 31)] + FY_ENDS + [date(2027, 3, 31)]
    grow = max(0.04, min(0.2, (eps_list[4] / eps_list[3] - 1) if eps_list[3] > 0 else 0.1))
    eps_pts = [eps_list[0] * 0.9] + eps_list + [eps_list[4] * (1 + grow)]
    bv_pts = [bvps_list[0] * 0.9] + bvps_list + [bvps_list[4] * 1.1]

    def interp(d: date, xs: list[float]) -> float:
        for j in range(len(fy_pts) - 1):
            if fy_pts[j] <= d <= fy_pts[j + 1]:
                t = (d - fy_pts[j]).days / (fy_pts[j + 1] - fy_pts[j]).days
                return xs[j] + (xs[j + 1] - xs[j]) * t
        return xs[-1]

    vh = []
    y, m = 2021, 10
    for _ in range(60):
        me = month_end(y, m)
        pd_ = max(d for d in sd_list if d <= me)
        pr = by_date[pd_]
        e, b = interp(me, eps_pts), interp(me, bv_pts)
        vh.append({"monthEnd": me.isoformat(), "pe": round(pr / e, 1) if e > 0 else None, "pb": round(pr / b, 1) if b > 0 else None})
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    # events
    events = []
    for q in sorted(rdates):
        if rdates[q] <= ASOF and rdates[q] >= date(2025, 11, 1):
            events.append({"date": rdates[q].isoformat(), "type": "RESULTS", "text": f"Results for {qlabel(Q_ENDS[q])} announced."})
    for d, t, txt in s["extra_events"]:
        events.append({"date": d, "type": t, "text": txt})
    events.sort(key=lambda e: e["date"], reverse=True)
    pg_ = s["peer"]
    rec = {
        "symbol": sym, "name": s["name"], "isin": f"INESMP{idx + 1:06d}", "exchange": "NSE", "fictional": bool(s.get("fictional", False)),
        "sector": s["sector"], "industry": s["industry"], "sizeBand": s["band"], "marketCapRank": s["rank"], "isFinancial": s["fin"],
        "sharesOutstanding": shares, "lastPrice": s["price"], "about": s["about"],
        "revenueSegments": [{"name": n, "sharePct": a, "prevSharePct": b} for n, a, b in s["segments"]],
        "peerGroup": {"name": pg_[0], "members": [{"name": n, "symbol": sy} for n, sy in pg_[1]], "medians": pg_[2]},
        "annual": annual, "quarterly": quarterly, "shareholding": shareholding, "valuationHistory": vh,
        "dividendYieldPct": s["divy"], "events": events,
    }
    return rec, [p for p in series if p[0] >= STOCK_START]


# ---------------------------------------------------------------- indices and funds
def build_indices(days: list[date], market: list[float]) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """Returns (values, log-returns) per index id."""
    vals, rets_by = {}, {}
    mean_m = sum(market) / len(market)
    for iid, _n, _k, start, end, beta, idio in SP.INDICES:
        rng = sub_rng(iid)
        if iid.startswith("CRISIL_SHORT"):
            rets = [0.0] + [0.0003 * rng.gauss(0, 1) for _ in days[1:]]
        elif iid == "NIFTY50_TRI":
            rets = [0.0] + list(market[1:])
        elif iid == "NIFTY50":
            rets = [0.0] + list(market[1:])
        else:
            rets = [0.0] + [beta * (m - mean_m) + beta * mean_m + idio / SQ252 * 3 * rng.gauss(0, 1) for m in market[1:]]
        rets = [0.0] + fit_total(rets[1:], math.log(end / start))
        lv, acc = [0.0], 0.0
        for r in rets[1:]:
            acc += r
            lv.append(acc)
        vals[iid] = [start * math.exp(x) for x in lv]
        rets_by[iid] = rets
    return vals, rets_by


def build_fund_holdings(f: dict, pools: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    mixeq = f["mix"][0]
    if f["group"] == "DEBT":
        return [], []
    disclosed = round(mixeq - rng.uniform(0.8, 2.5), 2)
    chosen = []
    if f.get("index_fund"):
        chosen = [(e, 1.0 / (i + 3) ** 0.9) for i, e in enumerate(pools["LARGE"][:50])]
    else:
        nl, nm, ns = f["ntype"]
        bf = {"LARGE": 1.0, "MID": 0.9, "SMALL": 0.8}
        off = {"LARGE": 3, "MID": 9, "SMALL": 14}
        if f["cat"] == "Mid Cap Fund":
            bf, off = {"LARGE": 1.0, "MID": 1.0, "SMALL": 0.8}, {"LARGE": 4, "MID": 2, "SMALL": 12}
        if f["cat"] == "Small Cap Fund":
            bf, off = {"LARGE": 1.0, "MID": 0.9, "SMALL": 1.0}, {"LARGE": 4, "MID": 6, "SMALL": 2}
        for band, n in (("LARGE", nl), ("MID", nm), ("SMALL", ns)):
            pool = pools[band]
            if n <= 0:
                continue
            pre = min(len(pool), max(n, int(n * 1.35)))
            idxs = sorted(rng.sample(range(pre), min(n, pre)))
            for rank_i, ix in enumerate(idxs):
                noise = math.exp(rng.gauss(0, 0.45))
                chosen.append((pool[ix], bf[band] / (ix + off[band]) ** 0.7 * noise))
    tot = sum(w for _, w in chosen)
    ws = [w / tot * disclosed for _, w in chosen]
    cap = 9.8 if not f.get("index_fund") else 99.0
    for _ in range(6):
        over = sum(max(0.0, w - cap) for w in ws)
        if over <= 1e-9:
            break
        under = sum(w for w in ws if w < cap)
        ws = [cap if w >= cap else w + over * w / under for w in ws]
    ws = [round(w, 2) for w in ws]
    ordered = sorted(zip([e for e, _ in chosen], ws), key=lambda t: (-t[1], t[0]["symbol"]))
    diff = round(disclosed - sum(w for _, w in ordered), 2)
    ordered[0] = (ordered[0][0], round(ordered[0][1] + diff, 2))
    ordered.sort(key=lambda t: (-t[1], t[0]["symbol"]))
    holdings = [{"symbol": e["symbol"], "isin": None, "name": e["name"], "sector": e["sector"], "sizeBand": e["sizeBand"], "weightPct": w} for e, w in ordered]
    # previous top 10
    rest = [{"symbol": e["symbol"], "name": e["name"]} for e, _ in ordered[10:12]]
    prev = [{"symbol": h["symbol"], "name": h["name"], "weightPct": round(max(0.1, h["weightPct"] + rng.uniform(-0.45, 0.45)), 2)} for h in holdings[:10]]
    nswap = 1 + rng.randint(0, 1)
    for k in range(nswap):
        if k < len(rest):
            prev[9 - k] = {"symbol": rest[k]["symbol"], "name": rest[k]["name"], "weightPct": round(holdings[9]["weightPct"] + rng.uniform(0.0, 0.2), 2)}
    prev.sort(key=lambda p: (-p["weightPct"], p["symbol"]))
    return holdings, prev


def generate(out: Path) -> None:
    out = Path(out)
    days = bdays(SERIES_START, ASOF)
    market = make_market(days)
    # manifest
    write_text(out / "manifest.json", dumps({"asOf": ASOF.isoformat(), "seed": SEED, "generator": "scripts/generate_sample_data.py",
                                              "generatorVersion": 1, "note": "Illustrative sample data, not real figures."}))
    # stocks
    stocks, stock_names = [], {}
    for i, s in enumerate(SP.STOCKS):
        rec, series = build_stock(s, days, market, i)
        stocks.append(rec)
        stock_names[s["symbol"]] = s
        write_text(out / "prices" / "stocks" / f"{s['symbol']}.csv",
                   "date,close,volume\n" + "".join(f"{d.isoformat()},{c:.2f},{v}\n" for d, c, v in series))
    write_text(out / "stocks.json", dumps(stocks))
    write_text(out / "universe.json", dumps([{"symbol": a, "name": b, "sector": c, "sizeBand": d} for a, b, c, d in SP.UNIVERSE]))
    # indices
    ivals, irets = build_indices(days, market)
    write_text(out / "indices.json", dumps([{"id": i[0], "name": i[1], "kind": i[2]} for i in SP.INDICES]))
    for iid, vs in ivals.items():
        write_text(out / "prices" / "indices" / f"{iid}.csv", "date,close\n" + "".join(f"{d.isoformat()},{v:.2f}\n" for d, v in zip(days, vs)))
    # pools for fund holdings
    large_order = ["RELIANCE", "HDFCBANK", "TCS", "BHARTIARTL", "ICICIBANK", "INFY", "SBIN", "ITC", "HINDUNILVR", "LT", "KOTAKBANK", "BAJFINANCE",
                   "AXISBANK", "HCLTECH", "MARUTI", "SUNPHARMA", "NTPC", "ULTRACEMCO", "TITAN", "ONGC", "POWERGRID", "ADANIPORTS", "ASIANPAINT",
                   "BAJAJFINSV", "COALINDIA", "WIPRO", "NESTLEIND", "JSWSTEEL", "TATASTEEL", "HINDALCO", "GRASIM", "TECHM", "DRREDDY", "CIPLA",
                   "APOLLOHOSP", "BRITANNIA", "EICHERMOT", "HEROMOTOCO", "BAJAJAUTO", "SBILIFE", "HDFCLIFE", "INDUSINDBK", "SHRIRAMFIN", "TATACONSUM",
                   "DIVISLAB", "LTIM", "BPCL", "TRENT", "DMART", "HAL", "BEL", "INDIGO", "IOC"]
    allco = {s["symbol"]: dict(symbol=s["symbol"], name=s["name"], sector=s["sector"], sizeBand=s["band"]) for s in SP.STOCKS}
    for a, b, c, d in SP.UNIVERSE:
        allco[a] = dict(symbol=a, name=b, sector=c, sizeBand=d)
    pools = {"LARGE": [allco[x] for x in large_order],
             "MID": [allco[x] for x in ["PERSISTENT", "VOLTAS", "FEDERALBNK", "COFORGE", "MPHASIS", "MUTHOOTFIN", "CHOLAFIN", "ABCAPITAL", "IDFCFIRSTB", "LUPIN",
                                          "AUROPHARMA", "MAXHEALTH", "POLYCAB", "CUMMINSIND", "PIIND", "SRF", "SUPREMEIND", "TATAELXSI", "JUBLFOOD", "PAGEIND",
                                          "BALKRISIND", "ASHOKLEY", "GODREJPROP", "OBEROIRLTY"]],
             "SMALL": [allco[x] for x in ["DECCANINF", "RADICO", "KIRLOSENG", "GRINDWELL", "SUNTECK", "JKPAPER", "WELSPUNLIV", "GREENPLY", "CERA", "ANANTRAJ",
                                           "JBMA", "JYOTHYLAB", "NAVINFLUOR", "SHIVAGRO", "ORCHVAL", "MEGHCAST", "KESARPLAS", "TARAPACK"]]}
    # funds
    funds, fund_navs, reg_rets = [], {}, {}
    fund_days_all = days
    for f in SP.FUNDS:
        code = f["code"]
        rng = sub_rng("fund" + code)
        launch = date.fromisoformat(f["launch"])
        start = max(launch, SERIES_START)
        i0 = next(i for i, d in enumerate(days) if d >= start)
        fd = days[i0:]
        mk = market[i0:]
        years = len(fd) / 252.0
        if f.get("twin_of"):
            base = reg_rets[f["twin_of"]]
            gap = SP.FUNDS[0]["ter"] - f["ter"]
            rets = [0.0] + [r + math.log(1 + gap / 100) / 252 for r in base[1:]]
        elif f.get("index_fund"):
            tri = irets[f["track"]][i0:]
            rets = [0.0] + [r - f["ter"] / 100 / 252 + 0.00012 * rng.gauss(0, 1) for r in tri[1:]]
        else:
            if f["group"] == "DEBT":
                rets = [0.0] + [f["cagr"] / 100 / 252 + f["vol"] / SQ252 * rng.gauss(0, 1) for _ in fd[1:]]
            else:
                mean_m = sum(mk) / len(mk)
                rets = [0.0] + [f["beta"] * (m - mean_m) + f["vol"] / SQ252 * rng.gauss(0, 1) for m in mk[1:]]
                rets = [0.0] + fit_total(rets[1:], math.log(1 + f["cagr"] / 100) * years)
        reg_rets[code] = rets
        navs = path_from_rets(rets, f["nav"])
        fund_navs[code] = (fd, navs)
        write_text(out / "navs" / f"{code}.csv", "date,nav\n" + "".join(f"{d.isoformat()},{v:.4f}\n" for d, v in zip(fd, navs)))
    # holdings per code (twins share)
    hold_cache = {}
    for f in SP.FUNDS:
        code = f["code"]
        src = f.get("twin_of") or code
        if src not in hold_cache:
            fsrc = next(x for x in SP.FUNDS if x["code"] == src)
            hold_cache[src] = build_fund_holdings(fsrc, pools, sub_rng("hold" + src))
        hold, prev = hold_cache[src]
        eq, de, ca, ot = f["mix"]
        funds.append({
            "schemeCode": code, "isin": f"INFSMP{code}", "name": f["name"], "shortName": f["short"], "amc": f["amc"], "category": f["cat"],
            "categoryGroup": f["group"], "planType": f["plan"], "twinSchemeCode": f["twin"], "launchDate": f["launch"],
            "aumInr": f["aum"], "aumInr1yAgo": f["aum1y"], "terPct": f["ter"], "terAsOf": "2026-09-30",
            "exitLoad": ({"text": "None", "pct": 0, "days": 0} if f["exit"][0] == 0 else
                         {"text": f"{f['exit'][0]:g}% if you take money out within {f['exit'][1]} days", "pct": f["exit"][0], "days": f["exit"][1]}),
            "lockInYears": f["lock"], "benchmarkId": f["bench"],
            "managers": [{"name": n, "since": s} for n, s in f["managers"]],
            "assetMix": {"equityPct": eq, "debtPct": de, "cashPct": ca, "otherPct": ot}, "portfolioDate": "2026-09-30",
            "holdings": hold, "previousTop10": prev,
            "events": [{"date": d, "type": t, "text": x} for d, t, x in f["events"]],
        })
    write_text(out / "funds.json", dumps(funds))
    write_text(out / "fund_categories.json", dumps(SP.CATEGORIES))
    u = SP.SAMPLE_USER
    write_text(out / "sample_user.json", dumps({
        "accountLabel": u["accountLabel"], "idleCashInr": u["idleCashInr"],
        "stocks": [{"symbol": a, "quantity": b, "avgPrice": c, "firstBuyDate": d} for a, b, c, d in u["stocks"]],
        "funds": [{"schemeCode": a, "units": b, "avgNav": c, "firstBuyDate": d} for a, b, c, d in u["funds"]]}))
    for name, rows in SP.SURVEILLANCE.items():
        write_text(out / "surveillance" / f"{name}.csv", "symbol,name,stage,since\n" + "".join(",".join(r) + "\n" for r in rows))


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "app" / "data" / "sample"
    generate(target)
    print(f"Sample data written to {target}")
