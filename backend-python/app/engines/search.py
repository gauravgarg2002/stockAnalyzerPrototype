"""Prefix/substring search over symbols, names, scheme names (max 10)."""
from __future__ import annotations

from typing import Optional

from .fund_check import fund_subtitle
from .stock_check import stock_subtitle


def _rank(q: str, primary: str, *others: str) -> Optional[int]:
    """0 exact (primary), 1 prefix, 2 substring; None if no match."""
    p = primary.lower()
    if p == q:
        return 0
    cands = [p] + [o.lower() for o in others]
    if any(c.startswith(q) for c in cands):
        return 1
    if any(q in c for c in cands):
        return 2
    return None


def search(query: str, stocks: list[dict], funds: list, limit: int = 10) -> list[dict]:
    """stocks: dicts with symbol,name,sector,sizeBand. funds: FundMeta objects."""
    q = query.strip().lower()
    scored = []
    for s in stocks:
        r = _rank(q, s["symbol"], s["name"])
        if r is not None:
            scored.append((r, 0, s["name"].lower(), {"kind": "STOCK", "id": s["symbol"], "name": s["name"], "subtitle": stock_subtitle(s["sector"], s["sizeBand"]),
                                                      "checkPath": f"/stock/{s['symbol']}"}))
    for m in funds:
        r = _rank(q, m.schemeCode, m.name, m.shortName, m.amc)
        if r is not None:
            scored.append((r, 1, m.name.lower(), {"kind": "FUND", "id": m.schemeCode, "name": m.name, "subtitle": fund_subtitle(m.category, m.planType),
                                                   "checkPath": f"/fund/{m.schemeCode}"}))
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    return [t[3] for t in scored[:limit]]
