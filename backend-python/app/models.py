"""Pydantic v2 models for every contract shape (sections 0, B). extra='forbid'; nullable fields are required-but-nullable."""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Unit = Literal["INR", "INR_PRICE", "PCT", "PCT_CHANGE", "TIMES", "YEARS", "MONTHS", "DAYS", "COUNT", "TEXT"]
CompKind = Literal["OWN_HISTORY", "PEERS", "CATEGORY", "BENCHMARK", "INDEX", "PLAN_TWIN", "THRESHOLD", "PREVIOUS_PERIOD"]
SourceLabel = Literal["Company filings", "NSE", "AMFI", "Fund factsheet", "Your Zerodha account",
                      "Your account statement", "Added by you", "Calculated from your holdings", "Sample data"]


class M(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Comparison(M):
    kind: CompKind
    label: str
    value: Union[float, int, str, None]
    unit: Unit
    display: str


class Figure(M):
    id: str
    label: str
    value: Union[float, int, str, None]
    unit: Unit
    display: str
    source: SourceLabel
    asOf: str
    comparisons: list[Comparison]
    termId: Optional[str]


class Sentence(M):
    text: str
    templateId: str
    generator: Literal["template", "llm"]


class DetailTable(M):
    title: str
    columns: list[str]
    rows: list[list[str]]


class Answer(M):
    id: str
    order: int
    question: str
    sentences: list[Sentence]
    figures: list[Figure]
    details: Optional[DetailTable]


class Fact(M):
    id: str
    order: int
    title: str
    termId: Optional[str]
    available: bool
    sentences: list[Sentence]
    figures: list[Figure]
    details: Optional[DetailTable]


class SeriesPoint(M):
    date: str
    value: float


class Benchmark(M):
    id: str
    name: str
    points: list[SeriesPoint]


class PriceHistory(M):
    frequency: Literal["WEEKLY"]
    from_: str = Field(alias="from")
    to: str
    points: list[SeriesPoint]
    benchmark: Benchmark
    source: SourceLabel
    asOf: str


class Drawdown(M):
    window: Literal["5Y", "10Y", "SINCE_LAUNCH"]
    worstFall: Figure
    peakDate: Optional[str]
    troughDate: Optional[str]
    recoveryDate: Optional[str]
    recoveryDays: Optional[float]
    sentences: list[Sentence]


class InstrumentRef(M):
    kind: Literal["STOCK", "FUND"]
    id: str
    name: str
    subtitle: str


class SearchResult(InstrumentRef):
    checkPath: str


class SearchResponse(M):
    sampleData: bool
    query: str
    results: list[SearchResult]


class StockInstrument(M):
    kind: Literal["STOCK"]
    symbol: str
    name: str
    exchange: str
    isin: Optional[str]
    sector: str
    industry: str
    sizeBand: Literal["LARGE", "MID", "SMALL", "MICRO"]
    fictional: bool
    lastPrice: Figure
    marketCap: Figure


class PeerMember(M):
    name: str
    symbol: Optional[str]
    checkAvailable: bool


class Peers(M):
    groupName: str
    members: list[PeerMember]


class StockCheck(M):
    sampleData: bool
    asOf: str
    instrument: StockInstrument
    answers: list[Answer]
    facts: list[Fact]
    priceHistory: PriceHistory
    drawdown: Drawdown
    peers: Peers


class RefIdName(M):
    id: str
    name: str


class TwinRef(M):
    schemeCode: str
    name: str
    planType: Literal["DIRECT", "REGULAR"]


class FundInstrument(M):
    kind: Literal["FUND"]
    schemeCode: str
    isin: Optional[str]
    name: str
    shortName: str
    amc: str
    category: str
    categoryGroup: Literal["EQUITY", "HYBRID", "DEBT"]
    planType: Literal["DIRECT", "REGULAR"]
    twin: Optional[TwinRef]
    benchmark: RefIdName
    nav: Figure


class AmountOut(M):
    amountInr: float
    display: str
    basis: Literal["HOLDING", "ILLUSTRATIVE", "USER_INPUT"]


class FundCheck(M):
    sampleData: bool
    asOf: str
    instrument: FundInstrument
    amount: AmountOut
    answers: list[Answer]
    facts: list[Fact]
    priceHistory: PriceHistory
    drawdown: Drawdown


class CompareInstrument(SearchResult):
    pass


class CompareCell(M):
    instrumentId: str
    sentences: list[Sentence]
    figures: list[Figure]


class CompareRow(M):
    id: str
    order: int
    question: str
    cells: list[CompareCell]


class Compare(M):
    sampleData: bool
    asOf: str
    kind: Literal["STOCK", "FUND"]
    instruments: list[CompareInstrument]
    rows: list[CompareRow]


class GlossaryTerm(M):
    id: str
    term: str
    aliases: list[str]
    meaning: str
    appliesTo: list[Literal["STOCK", "FUND", "PORTFOLIO"]]
    figureIds: list[str]


class Glossary(M):
    sampleData: bool
    terms: list[GlossaryTerm]


class Explain(M):
    sampleData: bool
    term: GlossaryTerm
    instrument: Optional[InstrumentRef]
    thisFigure: Optional[Figure]
    typical: Optional[Comparison]
    sentence: Optional[Sentence]


class BundleStock(M):
    symbol: str
    name: str
    isin: Optional[str]
    sector: str
    industry: str
    sizeBand: Literal["LARGE", "MID", "SMALL", "MICRO"]
    subtitle: str
    lastPrice: Optional[float]
    lastPriceDate: Optional[str]
    priceOneYearAgo: Optional[float]
    source: SourceLabel
    checkAvailable: bool


class AssetMix(M):
    equityPct: float
    debtPct: float
    cashPct: float
    otherPct: float


class BundleHolding(M):
    key: str
    symbol: Optional[str]
    isin: Optional[str]
    name: str
    sector: Optional[str]
    sizeBand: Optional[Literal["LARGE", "MID", "SMALL", "MICRO"]]
    weightPct: float
    checkAvailable: bool


class BundleFund(M):
    schemeCode: str
    isin: Optional[str]
    name: str
    subtitle: str
    amc: str
    category: str
    categoryGroup: Literal["EQUITY", "HYBRID", "DEBT"]
    planType: Literal["DIRECT", "REGULAR"]
    terPct: Optional[float]
    categoryMedianTerPct: Optional[float]
    twinSchemeCode: Optional[str]
    twinName: Optional[str]
    twinTerPct: Optional[float]
    nav: Optional[float]
    navDate: Optional[str]
    navOneYearAgo: Optional[float]
    assetMix: AssetMix
    portfolioDate: Optional[str]
    holdings: list[BundleHolding]
    source: SourceLabel


class NotFound(M):
    kind: Literal["STOCK", "FUND"]
    id: str


class Bundle(M):
    sampleData: bool
    asOf: str
    stocks: list[BundleStock]
    funds: list[BundleFund]
    notFound: list[NotFound]


class PointValue(M):
    requestedDate: str
    date: Optional[str]
    value: Optional[float]


class PointsItem(M):
    kind: Literal["STOCK", "FUND", "INDEX"]
    id: str
    values: list[PointValue]


class Points(M):
    sampleData: bool
    asOf: str
    items: list[PointsItem]


class Health(M):
    status: str
    sampleData: bool
    asOf: str
    version: str
    adapters: dict[str, str]
    statementParser: Literal["casparser", "fallback"]
    llmEnabled: bool


class BrokerStart(M):
    sampleData: bool
    brokerMode: str
    status: str
    loginUrl: Optional[str]
    message: str


class BrokerStatus(M):
    sampleData: bool
    brokerMode: str
    status: str
    accountLabel: Optional[str]
    message: str


class Unmatched(M):
    name: str
    isin: Optional[str]
    reason: str


class BrokerStock(M):
    symbol: str
    isin: Optional[str]
    quantity: float
    avgPrice: float
    lastPrice: Optional[float]
    firstBuyDate: Optional[str]


class BrokerFund(M):
    schemeCode: str
    isin: Optional[str]
    name: str
    units: float
    avgNav: Optional[float]
    lastNav: Optional[float]
    firstBuyDate: Optional[str]


class BrokerPortfolioOut(M):
    sampleData: bool
    source: SourceLabel
    asOf: str
    accountLabel: Optional[str]
    stocks: list[BrokerStock]
    funds: list[BrokerFund]
    idleCashInr: Optional[float]
    unmatched: list[Unmatched]


class StatementFund(M):
    schemeCode: str
    isin: Optional[str]
    name: str
    amc: Optional[str]
    units: float
    nav: Optional[float]
    navDate: Optional[str]
    valueInr: Optional[float]
    avgCostNav: Optional[float]


class StatementOut(M):
    sampleData: bool
    parser: Literal["casparser", "fallback"]
    statementType: Literal["CAMS", "KFINTECH", "UNKNOWN"]
    statementDate: Optional[str]
    funds: list[StatementFund]
    unmatched: list[Unmatched]


class NarrateOutItem(M):
    key: str
    sentence: Sentence


class NarrateOut(M):
    sampleData: bool
    items: list[NarrateOutItem]
