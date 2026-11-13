// Every type here mirrors docs/api-contract.md (§0 shared shapes, §A public API).
// Do not add, rename or drop fields. Nullable fields are present as null.

export type Kind = 'STOCK' | 'FUND';
export type SizeBand = 'LARGE' | 'MID' | 'SMALL' | 'MICRO';
export type PlanType = 'DIRECT' | 'REGULAR';
export type CategoryGroup = 'EQUITY' | 'HYBRID' | 'DEBT';

export type Unit =
  | 'INR'
  | 'INR_PRICE'
  | 'PCT'
  | 'PCT_CHANGE'
  | 'TIMES'
  | 'YEARS'
  | 'MONTHS'
  | 'DAYS'
  | 'COUNT'
  | 'TEXT';

export type SourceLabel =
  | 'Company filings'
  | 'NSE'
  | 'AMFI'
  | 'Fund factsheet'
  | 'Your Zerodha account'
  | 'Your account statement'
  | 'Added by you'
  | 'Calculated from your holdings'
  | 'Sample data';

export type ComparisonKind =
  | 'OWN_HISTORY'
  | 'PEERS'
  | 'CATEGORY'
  | 'BENCHMARK'
  | 'INDEX'
  | 'PLAN_TWIN'
  | 'THRESHOLD'
  | 'PREVIOUS_PERIOD';

export interface Comparison {
  kind: ComparisonKind;
  label: string;
  value: number | string | null;
  unit: Unit;
  display: string;
}

export interface Figure {
  id: string;
  label: string;
  value: number | string | null;
  unit: Unit;
  display: string;
  source: SourceLabel;
  asOf: string;
  comparisons: Comparison[];
  termId: string | null;
}

export type SentenceGenerator = 'template' | 'llm';

export interface Sentence {
  text: string;
  templateId: string;
  generator: SentenceGenerator;
}

export interface DetailTable {
  title: string;
  columns: string[];
  rows: string[][];
}

export interface Answer {
  id: string;
  order: number;
  question: string;
  sentences: Sentence[];
  figures: Figure[];
  details: DetailTable | null;
}

export interface Fact {
  id: string;
  order: number;
  title: string;
  termId: string | null;
  available: boolean;
  sentences: Sentence[];
  figures: Figure[];
  details: DetailTable | null;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface PriceHistory {
  frequency: string;
  from: string;
  to: string;
  points: SeriesPoint[];
  benchmark: { id: string; name: string; points: SeriesPoint[] };
  source: SourceLabel;
  asOf: string;
}

export interface Drawdown {
  window: '5Y' | '10Y' | 'SINCE_LAUNCH';
  worstFall: Figure;
  peakDate: string | null;
  troughDate: string | null;
  recoveryDate: string | null;
  recoveryDays: number | null;
  sentences: Sentence[];
}

export interface InstrumentRef {
  kind: Kind;
  id: string;
  name: string;
  subtitle: string;
}

export type ExposureKind = 'COMPANY' | 'SECTOR' | 'SIZE' | 'DEBT_CASH' | 'OTHER';

export interface ExposureViaFund {
  schemeCode: string;
  name: string;
  inr: number;
}

export interface ExposureLine {
  key: string;
  name: string;
  kind: ExposureKind;
  symbol: string | null;
  checkAvailable: boolean;
  totalInr: number;
  directInr: number;
  throughFundsInr: number;
  totalPct: number;
  directPct: number;
  throughFundsPct: number;
  display: string;
  directDisplay: string;
  throughFundsDisplay: string;
  viaFunds: ExposureViaFund[];
}

export interface ExposureBreakdown {
  dimension: 'COMPANY' | 'SECTOR' | 'SIZE';
  totalInr: number;
  lines: ExposureLine[];
  sentences: Sentence[];
}

export interface MixLine {
  key: string;
  label: string;
  valueInr: number;
  pct: number;
  display: string;
}

export interface WatchlistItem {
  id: number;
  kind: Kind;
  instrumentId: string;
  name: string;
  subtitle: string;
  note: string;
  createdAt: string;
  updatedAt: string;
  latest: Figure | null;
  checkPath: string;
}

export type ImportSource = 'KITE' | 'STATEMENT' | 'MANUAL';
export type ImportStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED';

export interface ImportLogEntry {
  id: number;
  source: ImportSource;
  status: ImportStatus;
  startedAt: string;
  finishedAt: string;
  stockCount: number;
  fundCount: number;
  unmatchedCount: number;
  message: string;
  sampleData: boolean;
}

// ---------------------------------------------------------------- errors

export type ApiErrorCode =
  | 'BAD_REQUEST'
  | 'NOT_FOUND'
  | 'BROKER_NOT_CONNECTED'
  | 'BROKER_FORBIDDEN_CALL'
  | 'STATEMENT_PASSWORD_INVALID'
  | 'STATEMENT_UNREADABLE'
  | 'UPSTREAM_UNAVAILABLE'
  | 'INTERNAL';

/** Codes the client itself can raise (not part of the wire contract). */
export type ClientErrorCode = 'NETWORK_ERROR' | 'INVALID_RESPONSE';

export interface ApiErrorBody {
  error: {
    code: ApiErrorCode;
    message: string;
    details: Record<string, unknown> | null;
  };
}

// ---------------------------------------------------------------- A.1 meta

export interface AdapterModes {
  broker: string;
  fundamentals: string;
  prices: string;
  surveillance: string;
  fundNav: string;
  fundMeta: string;
  fundHoldings: string;
  statement: string;
}

export interface MetaResponse {
  sampleData: boolean;
  asOf: string;
  adapters: AdapterModes;
  llmEnabled: boolean;
  disclaimer: string;
  defaultIllustrativeAmountInr: number;
}

// ---------------------------------------------------------------- A.2 home

export interface PortfolioFact {
  id: 'overlap' | 'cost' | 'idle_cash';
  sentence: Sentence;
  figures: Figure[];
}

export interface HomeResponse {
  sampleData: boolean;
  asOf: string;
  connected: boolean;
  hasHoldings: boolean;
  summary: Sentence[];
  topExposures: ExposureLine[];
  facts: PortfolioFact[];
  watchlist: WatchlistItem[];
  lastImport: ImportLogEntry | null;
}

// ---------------------------------------------------------------- A.3 portfolio

export interface PortfolioTotals {
  holdingsValue: Figure;
  invested: Figure;
  idleCash: Figure;
  totalWithCash: Figure;
}

export interface PortfolioConcentration {
  largestCompany: Figure;
  top5Companies: Figure;
  topSector: Figure;
  companyCount: Figure;
  holdingCount: Figure;
  sentences: Sentence[];
}

export interface OverlapFundRef {
  schemeCode: string;
  name: string;
}

export interface OverlapCommon {
  key: string;
  name: string;
  weightA: number;
  weightB: number;
  minWeight: number;
}

export interface OverlapPair {
  fundA: OverlapFundRef;
  fundB: OverlapFundRef;
  overlap: Figure;
  commonCount: number;
  topCommon: OverlapCommon[];
}

export interface PortfolioOverlap {
  pairs: OverlapPair[];
  sentences: Sentence[];
}

export interface DirectTwin {
  schemeCode: string;
  name: string;
  terPct: number;
}

export interface FundCostRow {
  schemeCode: string;
  name: string;
  planType: PlanType;
  value: Figure;
  expenseRatio: Figure;
  yearlyCost: Figure;
  directTwin: DirectTwin | null;
  yearlyGap: Figure | null;
}

export interface PortfolioCosts {
  totalYearly: Figure;
  regularGapYearly: Figure;
  funds: FundCostRow[];
  sentences: Sentence[];
}

export interface PortfolioMix {
  equityDebt: MixLine[];
  stocksFunds: MixLine[];
  sentences: Sentence[];
}

export interface ReturnRow {
  kind: 'STOCK' | 'FUND' | 'PORTFOLIO';
  id: string;
  name: string;
  oneYear: Figure;
  sinceBuy: Figure | null;
  gain: Figure;
}

export interface PortfolioReturns {
  benchmarkName: string;
  portfolio: ReturnRow;
  holdings: ReturnRow[];
  sentences: Sentence[];
}

export interface HoldingRow {
  holdingIds: number[];
  kind: Kind;
  id: string;
  name: string;
  subtitle: string;
  quantity: number;
  avgPrice: number;
  lastPrice: Figure;
  value: Figure;
  weightPct: number;
  sources: ImportSource[];
  firstBuyDate: string | null;
  checkPath: string;
}

export interface PortfolioResponse {
  sampleData: boolean;
  asOf: string;
  connected: boolean;
  hasHoldings: boolean;
  totals: PortfolioTotals;
  summary: Sentence[];
  facts: PortfolioFact[];
  exposure: { company: ExposureBreakdown; sector: ExposureBreakdown; size: ExposureBreakdown };
  concentration: PortfolioConcentration;
  overlap: PortfolioOverlap;
  costs: PortfolioCosts;
  mix: PortfolioMix;
  returns: PortfolioReturns;
  holdings: HoldingRow[];
}

// ---------------------------------------------------------------- A.4 search

export interface SearchResult extends InstrumentRef {
  checkPath: string;
}

export interface SearchResponse {
  sampleData: boolean;
  query: string;
  results: SearchResult[];
}

// ---------------------------------------------------------------- A.5 / A.6 checks

export interface UserBlock {
  holds: boolean;
  quantity: number | null;
  holdingValue: Figure | null;
  watchlistItemId: number | null;
  note: string | null;
}

export interface StockInstrument {
  kind: 'STOCK';
  symbol: string;
  name: string;
  exchange: string;
  isin: string;
  sector: string;
  industry: string;
  sizeBand: SizeBand;
  fictional: boolean;
  lastPrice: Figure;
  marketCap: Figure;
}

export interface PeerMember {
  name: string;
  symbol: string;
  checkAvailable: boolean;
}

export interface StockPeers {
  groupName: string;
  members: PeerMember[];
}

export interface StockCheckResponse {
  sampleData: boolean;
  asOf: string;
  instrument: StockInstrument;
  answers: Answer[];
  facts: Fact[];
  priceHistory: PriceHistory;
  drawdown: Drawdown;
  peers: StockPeers;
  user: UserBlock;
}

export interface FundTwinRef {
  schemeCode: string;
  name: string;
  planType: PlanType;
}

export interface FundInstrument {
  kind: 'FUND';
  schemeCode: string;
  isin: string;
  name: string;
  shortName: string;
  amc: string;
  category: string;
  categoryGroup: CategoryGroup;
  planType: PlanType;
  twin: FundTwinRef | null;
  benchmark: { id: string; name: string };
  nav: Figure;
}

export type AmountBasis = 'HOLDING' | 'ILLUSTRATIVE' | 'USER_INPUT';

export interface FundAmount {
  amountInr: number;
  display: string;
  basis: AmountBasis;
}

export interface FundCheckResponse {
  sampleData: boolean;
  asOf: string;
  instrument: FundInstrument;
  amount: FundAmount;
  answers: Answer[];
  facts: Fact[];
  priceHistory: PriceHistory;
  drawdown: Drawdown;
  user: UserBlock;
}

// ---------------------------------------------------------------- A.7 compare

export interface CompareInstrument extends InstrumentRef {
  checkPath: string;
}

export interface CompareCell {
  instrumentId: string;
  sentences: Sentence[];
  figures: Figure[];
}

export interface CompareRow {
  id: string;
  order: number;
  question: string;
  cells: CompareCell[];
}

export interface CompareResponse {
  sampleData: boolean;
  asOf: string;
  kind: Kind;
  instruments: CompareInstrument[];
  rows: CompareRow[];
}

// ---------------------------------------------------------------- A.8 try it on

export type TryMode = 'LUMP_SUM' | 'SIP';

export interface TryItOnRequest {
  kind: Kind;
  id: string;
  mode: TryMode;
  amountInr: number;
  months?: number | null;
}

export interface BeforeAfterNamed {
  name: string;
  figure: Figure;
}

export interface BeforeAfterPair<T> {
  before: T;
  after: T;
}

export interface TryItOnFundOverlap {
  schemeCode: string;
  name: string;
  overlap: Figure;
}

export interface TryItOnStockInFund {
  schemeCode: string;
  name: string;
  weight: Figure;
}

export interface TryItOnResponse {
  sampleData: boolean;
  asOf: string;
  instrument: InstrumentRef;
  input: {
    mode: TryMode;
    amountInr: number;
    months: number | null;
    addedValueInr: number;
    addedValueDisplay: string;
    alreadyHeld: boolean;
  };
  assumption: Sentence;
  metrics: {
    largestCompany: BeforeAfterPair<BeforeAfterNamed>;
    topSector: BeforeAfterPair<BeforeAfterNamed>;
    sizeMix: BeforeAfterPair<MixLine[]>;
    holdingsCount: BeforeAfterPair<Figure>;
    overlap: {
      candidateKind: Kind;
      fundOverlaps: TryItOnFundOverlap[];
      stockInFunds: TryItOnStockInFund[];
      exposureToCandidate: BeforeAfterPair<Figure> | null;
    };
    yearlyCost: { before: Figure; after: Figure; change: Figure };
  };
  sentences: Sentence[];
}

// ---------------------------------------------------------------- A.9 / A.10 glossary

export interface GlossaryTerm {
  id: string;
  term: string;
  aliases: string[];
  meaning: string;
  appliesTo: Array<'STOCK' | 'FUND' | 'PORTFOLIO'>;
  figureIds: string[];
}

export interface GlossaryResponse {
  sampleData: boolean;
  terms: GlossaryTerm[];
}

export interface ExplainResponse {
  sampleData: boolean;
  term: GlossaryTerm;
  instrument: InstrumentRef | null;
  thisFigure: Figure | null;
  typical: Comparison | null;
  sentence: Sentence | null;
}

// ---------------------------------------------------------------- A.11 watchlist

export interface WatchlistResponse {
  sampleData: boolean;
  items: WatchlistItem[];
}

export type WatchlistItemResponse = WatchlistItem & { sampleData: boolean };

export interface WatchlistAddRequest {
  kind: Kind;
  instrumentId: string;
  note: string;
}

// ---------------------------------------------------------------- A.12 connection

export type BrokerMode = 'mock' | 'kite_mcp' | 'kite_connect';
export type ConnectionStatus = 'NOT_CONNECTED' | 'PENDING_LOGIN' | 'CONNECTED' | 'FAILED';

export interface ConnectionResponse {
  sampleData: boolean;
  brokerMode: BrokerMode;
  status: ConnectionStatus;
  accountLabel: string | null;
  loginUrl: string | null;
  lastImportAt: string | null;
  imports: ImportLogEntry[];
  holdingsSummary: {
    stockCount: number;
    fundCount: number;
    bySource: { KITE: number; STATEMENT: number; MANUAL: number };
  };
}

export interface KiteStartResponse {
  sampleData: boolean;
  brokerMode: BrokerMode;
  status: ConnectionStatus;
  loginUrl: string | null;
  message: string;
}

export interface KiteStatusResponse {
  sampleData: boolean;
  brokerMode: BrokerMode;
  status: ConnectionStatus;
  accountLabel: string | null;
  message: string;
}

export type KiteDisconnectResponse = KiteStartResponse;

// ---------------------------------------------------------------- A.13 imports / holdings

export interface UnmatchedItem {
  name: string;
  isin: string | null;
  reason: string;
}

export interface ImportResponse {
  sampleData: boolean;
  importId: number;
  source: ImportSource;
  status: ImportStatus;
  importedAt: string;
  stockCount: number;
  fundCount: number;
  idleCashInr: number | null;
  unmatched: UnmatchedItem[];
  message: string;
}

export interface HoldingItem {
  id: number;
  kind: Kind;
  instrumentId: string;
  name: string;
  quantity: number;
  avgPrice: number;
  firstBuyDate: string | null;
  source: ImportSource;
  importedAt: string;
}

export interface HoldingsResponse {
  sampleData: boolean;
  holdings: HoldingItem[];
}

export type HoldingCreated = HoldingItem & { sampleData: boolean };

export interface ManualHoldingRequest {
  kind: Kind;
  instrumentId: string;
  quantity: number;
  avgPrice: number;
  firstBuyDate: string | null;
}

// ---------------------------------------------------------------- A.14 live quote and account activity

export interface QuoteResponse {
  sampleData: boolean;
  available: boolean;
  symbol: string;
  reason?: string;
  source?: string;
  asOf?: string | null;
  lastPrice?: number | null;
  lastPriceDisplay?: string;
  open?: number | null;
  openDisplay?: string;
  high?: number | null;
  highDisplay?: string;
  low?: number | null;
  lowDisplay?: string;
  prevClose?: number | null;
  prevCloseDisplay?: string;
  changeDisplay?: string;
  volume?: number | null;
  volumeDisplay?: string;
  rangePosition?: number | null;
}

export interface ActivityPosition {
  symbol: string;
  exchange: string;
  product: string;
  quantity: number;
  avgPrice: number | null;
  avgPriceDisplay: string;
  lastPrice: number | null;
  lastPriceDisplay: string;
  pnl: number | null;
  pnlDisplay: string;
}

export interface ActivityTrigger {
  symbol: string;
  kind: 'SINGLE' | 'TWO_LEG';
  triggerPrices: number[];
  triggerDisplays: string[];
  lastPriceAtSetup: number | null;
  quantity: number | null;
  status: string;
  createdAt: string | null;
}

export interface ActivityResponse {
  sampleData: boolean;
  connected: boolean;
  source: string;
  asOf: string;
  sentences: Sentence[];
  positions: ActivityPosition[];
  orders: { total: number; complete: number; open: number; cancelled: number } | null;
  tradesToday: number | null;
  gtts: ActivityTrigger[];
}
