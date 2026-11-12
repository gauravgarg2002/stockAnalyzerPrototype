"""Adapter Protocols and dataclasses (PLAN section 3.3, contract B.10/B.11).

Conventions (shared with the live adapters):
  * Every adapter module exposes ``build(config: dict, deps: dict) -> adapter`` where ``config`` is the
    full loaded config and ``deps`` holds already-built adapters keyed by
    "broker", "fundamentals", "prices", "surveillance", "fund_nav", "fund_meta", "fund_holdings".
  * Every adapter has a ``mode`` str attribute: "mock" or a live name (e.g. "screener", "mfapi").
  * Dates are ``datetime.date`` objects inside dataclasses; JSON-ish dicts (annual rows etc.) use the
    camelCase keys and ISO date strings of contract section D exactly.
  * ``source`` fields hold a SourceLabel string from ``app.sources``.
  * Adapters raise ``app.errors.ApiError`` for contract errors; a missing instrument is ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional, Protocol, runtime_checkable

# (date, close, volume or None), sorted ascending by date
PricePoint = tuple[date, float, Optional[int]]

INDEX_NAMES: dict[str, str] = {
    "NIFTY50": "Nifty 50",
    "NIFTY50_TRI": "Nifty 50 TRI",
    "NIFTY100_TRI": "Nifty 100 TRI",
    "NIFTY500_TRI": "Nifty 500 TRI",
    "NIFTY_MIDCAP150_TRI": "Nifty Midcap 150 TRI",
    "NIFTY_SMALLCAP250_TRI": "Nifty Smallcap 250 TRI",
    "CRISIL_HYBRID_35_65": "CRISIL Hybrid 35+65 Aggressive Index",
    "CRISIL_SHORT_DURATION_DEBT": "CRISIL Short Duration Debt Index",
}


@dataclass
class StockFundamentals:
    """Mirrors contract section D StockRecord (nested lists are dicts with the contract's keys)."""
    symbol: str
    name: str
    isin: Optional[str]
    sector: str
    industry: str
    sizeBand: str  # LARGE | MID | SMALL | MICRO
    marketCapRank: Optional[int]
    isFinancial: bool
    sharesOutstanding: Optional[float]
    about: str
    revenueSegments: list[dict] = field(default_factory=list)
    peerGroup: dict = field(default_factory=dict)  # {name, members:[{name,symbol}], medians:{...}}
    annual: list[dict] = field(default_factory=list)  # latest first or oldest first: engines sort by periodEnd
    quarterly: list[dict] = field(default_factory=list)
    shareholding: list[dict] = field(default_factory=list)
    valuationHistory: list[dict] = field(default_factory=list)
    dividendYieldPct: Optional[float] = None
    events: list[dict] = field(default_factory=list)
    source: str = "Sample data"
    asOf: str = ""  # ISO date of the data
    exchange: str = "NSE"
    fictional: bool = False
    lastPrice: Optional[float] = None


@dataclass
class PriceSeries:
    id: str
    points: list[PricePoint]
    source: str
    asOf: str  # ISO date


@dataclass
class NavSeries:
    id: str  # scheme code
    points: list[tuple[date, float]]
    source: str
    asOf: str


@dataclass
class SurveillanceEntry:
    symbol: str
    list: str  # ASM | GSM | ESM
    stage: str
    since: str  # ISO date or ""
    name: str = ""


@dataclass
class FundMeta:
    schemeCode: str
    isin: Optional[str]
    name: str
    shortName: str
    amc: str
    category: str
    categoryGroup: str  # EQUITY | HYBRID | DEBT
    planType: str  # DIRECT | REGULAR
    twinSchemeCode: Optional[str]
    launchDate: Optional[date]
    aumInr: Optional[float]
    aumInr1yAgo: Optional[float]
    terPct: Optional[float]
    terAsOf: Optional[str]
    exitLoad: Optional[dict]  # {text, pct, days}
    lockInYears: Optional[float]
    benchmarkId: Optional[str]
    managers: list[dict] = field(default_factory=list)  # [{name, since}]
    source: str = "Sample data"
    asOf: str = ""


@dataclass
class FundPortfolio:
    schemeCode: str
    portfolioDate: str  # ISO date
    assetMix: dict  # {equityPct, debtPct, cashPct, otherPct}
    holdings: list[dict]  # [{symbol, isin, name, sector, sizeBand, weightPct}] equity constituents only
    previousTop10: list[dict] = field(default_factory=list)  # [{symbol, name, weightPct}]
    events: list[dict] = field(default_factory=list)  # [{date, type, text}]
    source: str = "Sample data"


@dataclass
class BrokerPortfolio:
    """Contract B.10 portfolio response (without sampleData; derived from adapter mode)."""
    source: str
    asOf: str
    accountLabel: Optional[str]
    stocks: list[dict]  # {symbol, isin, quantity, avgPrice, lastPrice, firstBuyDate}
    funds: list[dict]  # {schemeCode, isin, name, units, avgNav, lastNav, firstBuyDate}
    idleCashInr: Optional[float]
    unmatched: list[dict] = field(default_factory=list)  # {name, isin, reason}
    sampleData: bool = False


@dataclass
class ParsedStatement:
    """Contract B.11 response."""
    parser: str  # casparser | fallback
    statementType: str  # CAMS | KFINTECH | UNKNOWN
    statementDate: Optional[str]
    funds: list[dict]  # {schemeCode, isin, name, amc, units, nav, navDate, valueInr, avgCostNav}
    unmatched: list[dict]
    sampleData: bool = False


@runtime_checkable
class BrokerAdapter(Protocol):
    mode: str

    def login_start(self) -> dict:
        """Contract B.10 'start' body: {sampleData, brokerMode, status, loginUrl, message}."""

    def login_status(self) -> dict:
        """{sampleData, brokerMode, status, accountLabel, message}."""

    def login_complete(self, request_token: str) -> dict:
        """kite_connect only; same shape as status. Other modes raise BAD_REQUEST."""

    def logout(self) -> dict:
        """Same shape as start with status NOT_CONNECTED."""

    def portfolio(self) -> BrokerPortfolio:
        """Raises BROKER_NOT_CONNECTED when not connected."""

    def historical(self, symbol: str, start: date, end: date) -> list[PricePoint]:
        """Daily candles from the connected broker; [] when unavailable."""


@runtime_checkable
class FundamentalsAdapter(Protocol):
    mode: str

    def get(self, symbol: str) -> Optional[StockFundamentals]: ...

    def search_stocks(self, query: str, limit: int) -> list[dict]:
        """[{symbol, name, sector, sizeBand, checkAvailable}] matching query (case-insensitive)."""

    def universe(self) -> list[dict]:
        """[{symbol, name, sector, sizeBand}] of checkable stocks."""


@runtime_checkable
class PriceAdapter(Protocol):
    mode: str

    def stock_series(self, symbol: str) -> Optional[PriceSeries]: ...

    def index_series(self, index_id: str) -> Optional[PriceSeries]: ...


@runtime_checkable
class SurveillanceAdapter(Protocol):
    mode: str

    def lookup(self, symbol: str) -> Optional[list[SurveillanceEntry]]:
        """Entries for the symbol ([] = on no list). None when the source is unavailable."""


@runtime_checkable
class FundNavAdapter(Protocol):
    mode: str

    def nav_series(self, scheme_code: str) -> Optional[NavSeries]: ...


@runtime_checkable
class FundMetaAdapter(Protocol):
    mode: str

    def get(self, scheme_code: str) -> Optional[FundMeta]: ...

    def find_by_isin(self, isin: str) -> Optional[FundMeta]: ...

    def search(self, query: str, limit: int) -> list[FundMeta]: ...

    def category(self, category_name: str) -> Optional[dict]:
        """CategoryRecord (contract D) or None."""

    def all_codes(self) -> list[str]: ...


@runtime_checkable
class FundHoldingsAdapter(Protocol):
    mode: str

    def portfolio(self, scheme_code: str) -> Optional[FundPortfolio]: ...


@runtime_checkable
class StatementParser(Protocol):
    name: str  # "casparser" | "fallback"

    def parse(self, pdf_bytes: bytes, password: str, filename: str = "") -> ParsedStatement:
        """Raises ApiError STATEMENT_PASSWORD_INVALID / STATEMENT_UNREADABLE."""


Any = Any  # re-export convenience
