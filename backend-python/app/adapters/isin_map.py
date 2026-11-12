"""Map statement entries to scheme codes via the fund-meta adapter and build the contract B.11 payload."""
from __future__ import annotations

import re
from typing import Any

from .base import ParsedStatement
from .cas_text_parser import ParsedText

NOT_FOUND = "Fund not found in fund list."


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def match_fund(fund_meta: Any, isin: str | None, name: str):
    """ISIN first (find_by_isin); then a unique exact normalised-name match from search(). None if unknown."""
    if fund_meta is None:
        return None
    if isin:
        try:
            m = fund_meta.find_by_isin(isin)
        except Exception:  # an unavailable lookup must not lose the whole statement
            m = None
        if m is not None:
            return m
    try:
        hits = [h for h in fund_meta.search(name, 5) if _norm(h.name) == _norm(name)] if name else []
    except Exception:
        hits = []
    return hits[0] if len(hits) == 1 else None


def build_statement(parsed: ParsedText, fund_meta: Any, parser_name: str) -> ParsedStatement:
    funds: list[dict] = []
    unmatched: list[dict] = []
    seen: dict[str, dict] = {}
    for e in parsed.entries:
        meta = match_fund(fund_meta, e.isin, e.name)
        if meta is None:
            unmatched.append({"name": e.name, "isin": e.isin, "reason": NOT_FOUND})
            continue
        avg = round(e.cost_inr / e.units, 4) if e.cost_inr and e.units else None
        row = {
            "schemeCode": meta.schemeCode, "isin": meta.isin or e.isin, "name": meta.name,
            "amc": meta.amc or e.amc or "", "units": e.units, "nav": e.nav, "navDate": e.nav_date,
            "valueInr": e.value_inr, "avgCostNav": avg,
        }
        prev = seen.get(meta.schemeCode)
        if prev is not None:  # same scheme in several folios: merge
            tot = prev["units"] + row["units"]
            if prev["avgCostNav"] is not None and row["avgCostNav"] is not None and tot:
                prev["avgCostNav"] = round((prev["avgCostNav"] * prev["units"] + row["avgCostNav"] * row["units"]) / tot, 4)
            else:
                prev["avgCostNav"] = None
            prev["units"] = round(tot, 3)
            if prev["valueInr"] is not None and row["valueInr"] is not None:
                prev["valueInr"] = round(prev["valueInr"] + row["valueInr"], 2)
            continue
        seen[meta.schemeCode] = row
        funds.append(row)
    sample = getattr(fund_meta, "mode", "mock") == "mock"
    return ParsedStatement(parser=parser_name, statementType=parsed.statement_type,
                           statementDate=parsed.statement_date, funds=funds, unmatched=unmatched,
                           sampleData=sample)
