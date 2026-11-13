"""Assembles the StockCheck payload (contract B.3)."""
from __future__ import annotations

from ..formatting import format_unit
from .figures import comparison as C
from .figures import make_figure
from .history import build_drawdown, build_price_history, empty_history
from .inputs import StockInputs
from .series import years_before
from .stock_answers import build_answers, last_price, market_cap_now, price_asof
from .stock_facts import BAND_TITLE, build_facts


def stock_subtitle(sector: str, band: str) -> str:
    return f"{sector} · {BAND_TITLE[band]}"


def build_stock_check(si: StockInputs, sample: bool) -> dict:
    f = si.f
    asof = si.as_of.isoformat()
    psrc = si.prices.source if si.prices else f.source
    ago = price_asof(si, years_before(si.as_of, 1))
    price = last_price(si)
    cap = market_cap_now(si)
    cap_prev = ago[1] * f.sharesOutstanding if ago and f.sharesOutstanding else None
    instrument = {
        "kind": "STOCK", "symbol": f.symbol, "name": f.name, "exchange": f.exchange, "isin": f.isin, "sector": f.sector, "industry": f.industry,
        "sizeBand": f.sizeBand, "fictional": f.fictional,
        "lastPrice": make_figure("last_price", "Last price", price, "INR_PRICE", psrc, asof, [C("PREVIOUS_PERIOD", "1 year ago", ago[1] if ago else None, "INR_PRICE")], None),
        "marketCap": make_figure("market_cap", "Market value of the company", cap, "INR", psrc, asof, [C("PREVIOUS_PERIOD", "1 year ago", cap_prev, "INR")], "market_cap"),
    }
    pts = [(p[0], p[1]) for p in si.prices.points] if si.prices else []
    bpts = [(p[0], p[1]) for p in si.benchmark.points] if si.benchmark else []
    start = years_before(si.as_of, 5)
    ph = build_price_history(pts, bpts, "NIFTY50", si.benchmark_name, start, psrc, si.as_of) or empty_history("NIFTY50", si.benchmark_name, psrc, si.as_of)
    dd = build_drawdown("stk", "5Y", "the last five years", pts, bpts, si.benchmark_name, start, psrc, si.as_of)
    peers = {"groupName": f.peerGroup.get("name", ""), "members": [
        {"name": m["name"], "symbol": m.get("symbol"), "checkAvailable": bool(m.get("symbol") and m["symbol"] in si.checkable_symbols)}
        for m in f.peerGroup.get("members", [])]}
    return {"sampleData": sample, "asOf": asof, "instrument": instrument, "answers": build_answers(si), "facts": build_facts(si),
            "priceHistory": ph, "drawdown": dd, "peers": peers}
