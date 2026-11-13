"""Instrument bundle entries for Java (contract B.8)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from ..adapters.base import FundMeta, FundPortfolio, NavSeries, PriceSeries, StockFundamentals
from .fund_check import fund_subtitle
from .series import fast_on_or_before, years_before
from .stock_check import stock_subtitle


def holding_key(symbol: Optional[str], isin: Optional[str], name: str) -> str:
    return symbol or isin or "NAME:" + name.strip().upper()


def stock_entry(f: StockFundamentals, prices: Optional[PriceSeries], as_of: date, source: str) -> dict:
    pts = [(p[0], p[1]) for p in prices.points] if prices else []
    last = pts[-1] if pts else None
    ago = fast_on_or_before([p[0] for p in pts], pts, years_before(as_of, 1)) if pts else None
    return {"symbol": f.symbol, "name": f.name, "isin": f.isin, "sector": f.sector, "industry": f.industry, "sizeBand": f.sizeBand,
            "subtitle": stock_subtitle(f.sector, f.sizeBand), "lastPrice": last[1] if last else f.lastPrice,
            "lastPriceDate": last[0].isoformat() if last else None, "priceOneYearAgo": ago[1] if ago else None,
            "source": source, "checkAvailable": True}


def fund_entry(m: FundMeta, nav: Optional[NavSeries], p: Optional[FundPortfolio], twin: Optional[FundMeta], cat: Optional[dict],
               as_of: date, checkable: frozenset, universe: dict[str, dict]) -> dict:
    pts = list(nav.points) if nav else []
    last = pts[-1] if pts else None
    ago = fast_on_or_before([x[0] for x in pts], pts, years_before(as_of, 1)) if pts else None
    key = "terPctDirect" if m.planType == "DIRECT" else "terPctRegular"
    med = ((cat or {}).get("medians") or {}).get(key)
    mix = p.assetMix if p else {"equityPct": 0.0, "debtPct": 100.0, "cashPct": 0.0, "otherPct": 0.0}
    amix = {k: round(float(mix.get(k, 0.0)), 2) for k in ("equityPct", "debtPct", "cashPct", "otherPct")}
    holdings = []
    for h in (p.holdings if p else []):
        sym = h.get("symbol")
        u = universe.get(sym or "", {})
        holdings.append({"key": holding_key(sym, h.get("isin"), h["name"]), "symbol": sym, "isin": h.get("isin"), "name": h["name"],
                         "sector": h.get("sector") or u.get("sector"), "sizeBand": h.get("sizeBand") or u.get("sizeBand"),
                         "weightPct": round(float(h["weightPct"]), 4), "checkAvailable": bool(sym and sym in checkable)})
    return {"schemeCode": m.schemeCode, "isin": m.isin, "name": m.name, "subtitle": fund_subtitle(m.category, m.planType), "amc": m.amc,
            "category": m.category, "categoryGroup": m.categoryGroup, "planType": m.planType, "terPct": m.terPct, "categoryMedianTerPct": med,
            "twinSchemeCode": twin.schemeCode if twin else None, "twinName": twin.name if twin else None, "twinTerPct": twin.terPct if twin else None,
            "nav": last[1] if last else None, "navDate": last[0].isoformat() if last else None, "navOneYearAgo": ago[1] if ago else None,
            "assetMix": amix, "portfolioDate": p.portfolioDate if p else None, "holdings": holdings, "source": m.source}
