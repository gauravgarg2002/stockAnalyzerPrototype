"""Statement parser backed by the optional `casparser` library.

build() raises ImportError when casparser is not installed so the factory falls back to statement_fallback.
UNVERIFIED AGAINST LIVE SERVICE / REAL LIBRARY: the dict shape consumed by map_casparser_dict follows
casparser's documented `read_cas_pdf(..., output="dict")` result (statement_period, file_type, folios[].schemes[]
with isin, close, valuation{date, nav, value, cost}); casparser is not installed in this sandbox.
"""
from __future__ import annotations

import io
from typing import Any

from ..errors import ApiError
from .base import ParsedStatement
from .cas_text_parser import ParsedEntry, ParsedText, to_iso, to_num
from .isin_map import build_statement


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v)[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return to_iso(s)


def map_casparser_dict(data: dict) -> ParsedText:
    """Pure mapping from casparser's dict output to ParsedText (investor info, PAN and folios are dropped)."""
    ftype = str(data.get("file_type") or "").upper()
    stype = ftype if ftype in ("CAMS", "KFINTECH") else "UNKNOWN"
    period = data.get("statement_period") or {}
    sdate = _iso(period.get("to"))
    entries: list[ParsedEntry] = []
    for folio in data.get("folios") or []:
        for sc in folio.get("schemes") or []:
            units = to_num(str(sc.get("close") if sc.get("close") is not None else sc.get("close_calculated") or 0)) or 0.0
            if units <= 0:
                continue
            val = sc.get("valuation") or {}
            nav = to_num(str(val["nav"])) if val.get("nav") is not None else None
            value = to_num(str(val["value"])) if val.get("value") is not None else None
            cost = to_num(str(val["cost"])) if val.get("cost") is not None else None
            entries.append(ParsedEntry(amc=folio.get("amc"), name=str(sc.get("scheme") or "").strip(),
                                       isin=sc.get("isin"), units=units, nav=nav, nav_date=_iso(val.get("date")),
                                       value_inr=value, cost_inr=cost))
    return ParsedText(stype, sdate, entries)


class CasparserStatementParser:
    name = "casparser"

    def __init__(self, fund_meta: Any, module: Any):
        self.fund_meta = fund_meta
        self._cp = module

    def parse(self, pdf_bytes: bytes, password: str, filename: str = "") -> ParsedStatement:
        cp = self._cp
        try:
            data = cp.read_cas_pdf(io.BytesIO(pdf_bytes), password or "", output="dict")
        except Exception as e:
            exc_mod = getattr(cp, "exceptions", None)
            bad_pw = getattr(exc_mod, "IncorrectPasswordError", None)
            if bad_pw is not None and isinstance(e, bad_pw):
                raise ApiError("STATEMENT_PASSWORD_INVALID",
                               "The password did not open this statement. Please check it and try again.")
            raise ApiError("STATEMENT_UNREADABLE",
                           "We could not read this statement. Please upload the PDF as downloaded from CAMS or KFintech.",
                           {"reason": type(e).__name__})
        if not isinstance(data, dict):
            raise ApiError("STATEMENT_UNREADABLE", "We could not read this statement.")
        parsed = map_casparser_dict(data)
        if not parsed.entries:
            raise ApiError("STATEMENT_UNREADABLE", "No mutual fund holdings were found in this statement.")
        return build_statement(parsed, self.fund_meta, self.name)


def build(config: dict, deps: dict) -> CasparserStatementParser:
    import casparser  # raises ImportError when not installed

    return CasparserStatementParser(deps.get("fund_meta"), casparser)
