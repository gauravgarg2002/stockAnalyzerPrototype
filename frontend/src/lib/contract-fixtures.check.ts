// Compile-time (and, under tsx, run-time) check that the Python contract fixtures fit src/lib/api-types.ts.
//   tsc -p tsconfig.fixtures.json      structural check of keys, nullability and arrays
//   tsx src/lib/contract-fixtures.check.ts   additionally checks enum-valued strings
// JSON imports widen string-literal unions to `string`, so the structural check compares against
// Widen<T> (same shape, every string literal union widened). The enum values are then validated at run time.

import stockTcs from '../../../backend-python/tests/fixtures/contract/stock-check-tcs.json';
import stockHdfc from '../../../backend-python/tests/fixtures/contract/stock-check-hdfcbank.json';
import stockShiv from '../../../backend-python/tests/fixtures/contract/stock-check-shivagro.json';
import fund101 from '../../../backend-python/tests/fixtures/contract/fund-check-900101.json';
import fund201 from '../../../backend-python/tests/fixtures/contract/fund-check-900201.json';
import fund801 from '../../../backend-python/tests/fixtures/contract/fund-check-900801.json';
import compareFunds from '../../../backend-python/tests/fixtures/contract/compare-funds.json';
import compareStocks from '../../../backend-python/tests/fixtures/contract/compare-stocks.json';
import search from '../../../backend-python/tests/fixtures/contract/search.json';
import glossary from '../../../backend-python/tests/fixtures/contract/glossary.json';
import explainPe from '../../../backend-python/tests/fixtures/contract/explain-pe.json';
import type {
  CompareResponse,
  ExplainResponse,
  FundCheckResponse,
  GlossaryResponse,
  SearchResponse,
  StockCheckResponse,
} from './api-types';

type Widen<T> = T extends string
  ? string
  : T extends number
    ? number
    : T extends boolean
      ? boolean
      : T extends null | undefined
        ? T
        : T extends readonly (infer U)[]
          ? Widen<U>[]
          : T extends object
            ? { [K in keyof T]: Widen<T[K]> }
            : T;

// Java adds the `user` block to the two check payloads.
type PythonStockCheck = Widen<Omit<StockCheckResponse, 'user'>>;
type PythonFundCheck = Widen<Omit<FundCheckResponse, 'user'>>;

export const stockFixtures: Record<string, PythonStockCheck> = {
  tcs: stockTcs,
  hdfcbank: stockHdfc,
  shivagro: stockShiv,
};
export const fundFixtures: Record<string, PythonFundCheck> = {
  f900101: fund101,
  f900201: fund201,
  f900801: fund801,
};
export const compareFixtures: Record<string, Widen<CompareResponse>> = {
  funds: compareFunds,
  stocks: compareStocks,
};
export const searchFixture: Widen<SearchResponse> = search;
export const glossaryFixture: Widen<GlossaryResponse> = glossary;
export const explainFixture: Widen<ExplainResponse> = explainPe;

// ------------------------------------------------------------ run-time enum validation

const UNITS = ['INR', 'INR_PRICE', 'PCT', 'PCT_CHANGE', 'TIMES', 'YEARS', 'MONTHS', 'DAYS', 'COUNT', 'TEXT'];
const SOURCES = [
  'Company filings', 'NSE', 'AMFI', 'Fund factsheet', 'Your Zerodha account',
  'Your account statement', 'Added by you', 'Calculated from your holdings', 'Sample data',
];
const CMP_KINDS = ['OWN_HISTORY', 'PEERS', 'CATEGORY', 'BENCHMARK', 'INDEX', 'PLAN_TWIN', 'THRESHOLD', 'PREVIOUS_PERIOD'];
const ENUMS: Record<string, string[]> = {
  unit: UNITS,
  source: SOURCES,
  generator: ['template', 'llm'],
  sizeBand: ['LARGE', 'MID', 'SMALL', 'MICRO'],
  planType: ['DIRECT', 'REGULAR'],
  categoryGroup: ['EQUITY', 'HYBRID', 'DEBT'],
  basis: ['HOLDING', 'ILLUSTRATIVE', 'USER_INPUT'],
  window: ['5Y', '10Y', 'SINCE_LAUNCH'],
  appliesTo: ['STOCK', 'FUND', 'PORTFOLIO'],
};

function walk(v: unknown, path: string, errors: string[]): void {
  if (Array.isArray(v)) {
    v.forEach((x, i) => walk(x, `${path}[${i}]`, errors));
    return;
  }
  if (typeof v !== 'object' || v === null) return;
  const o = v as Record<string, unknown>;
  for (const [k, val] of Object.entries(o)) {
    const allowed = ENUMS[k];
    const values = Array.isArray(val) ? val : [val];
    if (allowed && values.every((x) => typeof x === 'string') && values.some((x) => !allowed.includes(x as string))) {
      errors.push(`${path}.${k} = ${JSON.stringify(val)}`);
    }
    if (k === 'kind' && typeof val === 'string') {
      const ok = /\.(comparisons\[\d+\]|typical)$/.test(path)
        ? CMP_KINDS.includes(val)
        : ['STOCK', 'FUND', 'PORTFOLIO'].includes(val);
      if (!ok) errors.push(`${path}.kind = ${val}`);
    }
    walk(val, `${path}.${k}`, errors);
  }
}

export function validateEnums(): string[] {
  const errors: string[] = [];
  const all: Record<string, unknown> = {
    ...stockFixtures, ...fundFixtures, ...compareFixtures,
    search: searchFixture, glossary: glossaryFixture, explain: explainFixture,
  };
  for (const [name, payload] of Object.entries(all)) walk(payload, name, errors);
  return errors;
}

const proc = (globalThis as { process?: { argv: string[]; exit(code: number): void } }).process;
if (proc?.argv[1]?.endsWith('contract-fixtures.check.ts')) {
  const errs = validateEnums();
  if (errs.length > 0) {
    console.error(errs.join('\n'));
    proc.exit(1);
  } else {
    console.log('fixture enums ok');
  }
}
