"""Source labels (contract 0.3). Only these strings ever reach the UI."""
from __future__ import annotations

COMPANY_FILINGS = "Company filings"
NSE = "NSE"
AMFI = "AMFI"
FUND_FACTSHEET = "Fund factsheet"
ZERODHA = "Your Zerodha account"
STATEMENT = "Your account statement"
ADDED_BY_YOU = "Added by you"
CALCULATED = "Calculated from your holdings"
SAMPLE = "Sample data"

ALL_LABELS = (COMPANY_FILINGS, NSE, AMFI, FUND_FACTSHEET, ZERODHA, STATEMENT, ADDED_BY_YOU, CALCULATED, SAMPLE)

_LIVE = {
    "fundamentals": COMPANY_FILINGS,
    "prices": NSE,
    "surveillance": NSE,
    "fund_nav": AMFI,
    "fund_meta": AMFI,
    "fund_holdings": FUND_FACTSHEET,
    "broker": ZERODHA,
    "statement": STATEMENT,
}


def label_for(adapter_mode: str, kind: str) -> str:
    """Source label for an adapter kind running in the given mode."""
    if adapter_mode == "mock":
        return SAMPLE
    return _LIVE.get(kind, NSE)
