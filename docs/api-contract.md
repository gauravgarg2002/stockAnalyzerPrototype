# API contract — single source for all three services

Sections:
- §0 shared conventions and shapes
- §A public API (browser → Java, `/api`)
- §B internal API (Java → Python, `/internal`)
- §C config file schema
- §D sample-data file formats

Example values are illustrative. Tests use the generated sample data, not these numbers.
Agents MUST NOT add, rename or omit fields. Every field listed is always present; nullable fields are present as `null`.

---
## §0 Conventions and shared shapes

### 0.1 General
- JSON keys are camelCase. Dates are `"YYYY-MM-DD"`. Timestamps are ISO-8601 with offset (`"2026-10-30T18:42:10+05:30"`).
- Percent values use percent units (`12.34` = 12.34%). Rupee values are in rupees.
- Every top-level response object (public and internal, except errors and 204s) contains `"sampleData": boolean`. It is true if any figure in the payload came from a mock adapter or sample holdings.
- Kinds: `"STOCK" | "FUND"`. Index ids: `NIFTY50, NIFTY50_TRI, NIFTY100_TRI, NIFTY500_TRI, NIFTY_MIDCAP150_TRI, NIFTY_SMALLCAP250_TRI, CRISIL_HYBRID_35_65, CRISIL_SHORT_DURATION_DEBT`.
- Size bands: `"LARGE" | "MID" | "SMALL" | "MICRO"`. Plan types: `"DIRECT" | "REGULAR"`. Category groups: `"EQUITY" | "HYBRID" | "DEBT"`.

### 0.2 Error shape (all non-2xx, public and internal)
```json
{ "error": { "code": "NOT_FOUND", "message": "No stock found for symbol XYZ.", "details": { "symbol": "XYZ" } } }
```

| code | HTTP |
|---|---|
| `BAD_REQUEST` | 400 |
| `NOT_FOUND` | 404 |
| `BROKER_NOT_CONNECTED` | 409 |
| `BROKER_FORBIDDEN_CALL` | 403 |
| `STATEMENT_PASSWORD_INVALID` | 422 |
| `STATEMENT_UNREADABLE` | 422 |
| `UPSTREAM_UNAVAILABLE` | 502 |
| `INTERNAL` | 500 |

Java re-emits Python error bodies unchanged (same status). If Python is unreachable, Java returns 502 `UPSTREAM_UNAVAILABLE`. `details` is an object or `null`.

### 0.3 Shared shapes

**Unit** = `"INR" | "INR_PRICE" | "PCT" | "PCT_CHANGE" | "TIMES" | "YEARS" | "MONTHS" | "DAYS" | "COUNT" | "TEXT"`

**SourceLabel** (only these strings ever reach the UI):
`"Company filings" | "NSE" | "AMFI" | "Fund factsheet" | "Your Zerodha account" | "Your account statement" | "Added by you" | "Calculated from your holdings" | "Sample data"`.
- In mock mode every Python-sourced figure uses `"Sample data"`.
- Java-computed portfolio figures use `"Calculated from your holdings"`.
- The word "Screener" must never appear in any response.

**Comparison**
```json
{ "kind": "OWN_HISTORY", "label": "5-year median", "value": 27.4, "unit": "TIMES", "display": "27.4x" }
```
- `kind` ∈ `OWN_HISTORY | PEERS | CATEGORY | BENCHMARK | INDEX | PLAN_TWIN | THRESHOLD | PREVIOUS_PERIOD`.
- `value` is number|null; `unit` is a Unit; `display` is a string.

**Figure**
```json
{
  "id": "pe", "label": "Price to yearly profit (P/E)", "value": 29.8, "unit": "TIMES", "display": "29.8x",
  "source": "Sample data", "asOf": "2026-10-30",
  "comparisons": [
    { "kind": "OWN_HISTORY", "label": "5-year median", "value": 27.4, "unit": "TIMES", "display": "27.4x" },
    { "kind": "PEERS", "label": "Median of IT services peers", "value": 25.1, "unit": "TIMES", "display": "25.1x" }
  ],
  "termId": "pe_ratio"
}
```
- `value` is a number|null for numeric units and a string|null for `TEXT`.
- `display` is always a string; it is `"Not available"` when value is null.
- `comparisons` must be non-empty for every numeric Figure inside an Answer or Fact. The only exceptions are ids matching `overlap_*`. Python tests enforce this.
- `termId` is a glossary id or null.

**Sentence**
```json
{ "text": "Revenue rose from ₹1.9 lakh crore to ₹2.6 lakh crore in three years.", "templateId": "stk.growth.revenue", "generator": "template" }
```
`generator` ∈ `"template" | "llm"`.

**DetailTable** (behind "Show details"; already formatted strings)
```json
{ "title": "Revenue by business", "columns": ["Business", "Share of revenue", "A year earlier"], "rows": [["Banking and financial services", "31.5%", "32.1%"], ["Retail", "15.2%", "14.8%"]] }
```

**Answer**
```json
{ "id": "growth", "order": 2, "question": "Is it growing and profitable?", "sentences": [Sentence, Sentence], "figures": [Figure], "details": DetailTable }
```
`details` is DetailTable|null; `sentences` has length 2–3.

**Fact**
```json
{ "id": "promoter_pledge", "order": 2, "title": "Promoter pledge", "termId": "promoter_pledge", "available": true, "sentences": [Sentence], "figures": [Figure], "details": null }
```
`sentences` has length 1–2. When `available` is false, figures may be empty and the sentence says why.

**SeriesPoint** `{ "date": "2026-10-30", "value": 3925.4 }`

**PriceHistory**
```json
{ "frequency": "WEEKLY", "from": "2021-11-05", "to": "2026-10-30", "points": [SeriesPoint],
  "benchmark": { "id": "NIFTY50", "name": "Nifty 50", "points": [SeriesPoint] },
  "source": "Sample data", "asOf": "2026-10-30" }
```
- Points are last-business-day-of-week closes. The final point is always `asOf`.
- `benchmark.points` share the same dates and are rebased so the first value equals the instrument's first value.
- Stock: 5 years, benchmark NIFTY50. Fund: up to 10 years (from launch), benchmark = the fund's benchmark index.

**Drawdown**
```json
{ "window": "5Y", "worstFall": Figure, "peakDate": "2024-09-26", "troughDate": "2025-03-03", "recoveryDate": null, "recoveryDays": null, "sentences": [Sentence] }
```
- `worstFall` is a Figure with id `worst_fall`, unit PCT_CHANGE, value negative (e.g. -31.4) and comparisons [BENCHMARK same window].
- `recoveryDays` is calendar days from trough to the first close ≥ the peak close; null means not recovered by asOf.
- `window` is `"5Y"` for stocks; `"10Y"` for funds, or `"SINCE_LAUNCH"` if the fund is younger.

**InstrumentRef**
```json
{ "kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap" }
```

**ExposureLine** (Java computes)
```json
{
  "key": "HDFCBANK", "name": "HDFC Bank Ltd", "kind": "COMPANY", "symbol": "HDFCBANK", "checkAvailable": true,
  "totalInr": 151230, "directInr": 98940, "throughFundsInr": 52290,
  "totalPct": 11.84, "directPct": 7.75, "throughFundsPct": 4.09,
  "display": "₹1.5 lakh (11.8%)", "directDisplay": "₹98,940 (7.7%)", "throughFundsDisplay": "₹52,290 (4.1%)",
  "viaFunds": [ { "schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "inr": 31880 } ]
}
```
- `kind` ∈ `COMPANY | SECTOR | SIZE | DEBT_CASH | OTHER`.
- `key` for SECTOR is the sector name; for SIZE it is `LARGE|MID|SMALL|MICRO`; buckets use `DEBT_CASH` and `OTHER`.
- `name` for buckets is `"Debt & cash"` and `"Other / undisclosed"`; for sizes it is `"Large cap"`, `"Mid cap"`, `"Small cap"`, `"Micro cap"`.
- `symbol` is null unless kind is COMPANY with a known symbol. `checkAvailable` is false for non-companies.
- `viaFunds` is sorted by inr descending; it is empty when there is no fund exposure.

**ExposureBreakdown**
```json
{ "dimension": "COMPANY", "totalInr": 1277410, "lines": [ExposureLine], "sentences": [Sentence] }
```
- `dimension` ∈ `COMPANY | SECTOR | SIZE`.
- Σ `lines[].totalPct` = 100 exactly (basis points), and Σ `totalInr` = `totalInr`.
- Lines are sorted by totalInr descending, with buckets (DEBT_CASH, OTHER) last.

**MixLine** `{ "key": "EQUITY", "label": "Shares", "valueInr": 1010230, "pct": 79.08, "display": "₹10.1 lakh (79.1%)" }`
Keys: EQUITY/DEBT_CASH/OTHER (equity-debt mix); STOCKS/FUNDS (stocks-funds mix). Labels: "Shares", "Debt & cash", "Other assets", "Stocks held directly", "Mutual funds".

**WatchlistItem** (public only)
```json
{ "id": 3, "kind": "STOCK", "instrumentId": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap",
  "note": "Want to understand the IT services business.", "createdAt": "2026-10-28T10:02:11+05:30", "updatedAt": "2026-10-28T10:02:11+05:30",
  "latest": Figure, "checkPath": "/stock/TCS" }
```
`latest` is the last price (stock, INR_PRICE, id `last_price`) or NAV (fund, INR_PRICE, id `nav`), or null if unavailable. Its comparisons are [PREVIOUS_PERIOD: 1 year ago].

**ImportLogEntry**
```json
{ "id": 7, "source": "KITE", "status": "SUCCESS", "startedAt": "2026-10-30T18:40:02+05:30", "finishedAt": "2026-10-30T18:40:03+05:30",
  "stockCount": 6, "fundCount": 4, "unmatchedCount": 0, "message": "Imported 6 stocks, 4 funds and idle cash.", "sampleData": true }
```
`source` ∈ `KITE | STATEMENT | MANUAL`. `status` ∈ `SUCCESS | PARTIAL | FAILED`.

### 0.4 Indian formatting (identical in Python, Java, TypeScript)
**Rounding:** round HALF_UP on the shortest decimal string of the double. That is Python `Decimal(str(x))`, Java `BigDecimal.valueOf(x)`, JS: parse `String(x)` and expand any exponent. "Drop .0" means a trailing `.0` is removed. Negative values get a leading ASCII `-` before `₹`.

| Function / unit | Rule |
|---|---|
| INR (amount) | Round to whole rupees. < 1,00,000 → `₹` + Indian grouping. Else lakh = r/1e5 rounded to 1 dp; if < 100 → `₹{x} lakh` (drop .0). Else crore = r/1e7 rounded to 1 dp; if < 1000 → `₹{x} crore` (drop .0); else whole crore with Indian grouping → `₹{n} crore` |
| INR_PRICE | 2 dp with Indian grouping: `₹2,410.50` |
| PCT | 1 dp + `%` (no sign; negative keeps `-`) |
| PCT_CHANGE | 1 dp, sign always: `+14.3%`, `-4.1%`, `0.0%` |
| TIMES | 1 dp + `x` |
| YEARS / MONTHS / DAYS | 1 dp (drop .0) + ` year(s)` / ` month(s)` / ` day(s)`; singular when the formatted number is exactly `1` |
| COUNT | Integer with Indian grouping |
| Date | `30 Oct 2026` (3-letter English month, no leading zero on day) |

**Test vectors (all three languages):**
- `formatInr`: 0→`₹0`; 999→`₹999`; 42350.75→`₹42,351`; 99999.4→`₹99,999`; 99999.6→`₹1 lakh`; 120000→`₹1.2 lakh`; 1243500→`₹12.4 lakh`; 1250000→`₹12.5 lakh`; 9999999→`₹1 crore`; 34000000→`₹3.4 crore`; 8453000000→`₹845.3 crore`; 19321000000000→`₹19,32,100 crore`; -45000→`-₹45,000`.
- `formatPrice`: 2410.5→`₹2,410.50`; 2.675→`₹2.68`; 1234567.891→`₹12,34,567.89`.
- `formatPct`: 12.345→`12.3%`; 0.05→`0.1%`; 1.25→`1.3%`.
- `formatPctChange`: 14.25→`+14.3%`; -4.1→`-4.1%`; 0→`0.0%`.
- `formatTimes`: 24.06→`24.1x`.
- `formatCount`: 1234567→`12,34,567`.
- `formatYears`: 1→`1 year`; 3→`3 years`; 7.25→`7.3 years`.
- `formatDays`: 1→`1 day`; 143→`143 days`.
- `formatDate`: `2026-10-30`→`30 Oct 2026`.

### 0.5 Sentence templates: placeholder syntax
- `{key}` inserts the display string of fact `key` (formatted per its unit; TEXT inserted verbatim).
- `{key|one|many}` inserts `"<n> one"` if the COUNT value is 1, else `"<n> many"` (e.g. `{stockCount|stock|stocks}` → `6 stocks`).

### 0.6 Banned verdict words (one regex, case-insensitive, applied with names masked)
```
\b(buy|buys|buying|sell|sells|selling|avoid|avoids|avoided|avoiding|overvalued|undervalued|cheap|expensive|good|bad|recommend|recommends|recommended|recommending|recommendation|recommendations|should|target\s+prices?)\b
```
- Python: `re.compile(PATTERN, re.IGNORECASE)`. JS: `new RegExp(PATTERN, 'i')`.
- Before scanning a rendered sentence, every TEXT fact whose key ends in `Name`, and every instrument/fund/company name in it, is replaced with `NAME`.
- **Collisions to avoid in all copy:**
  - "buy-back" → write "buyback" or "share repurchase".
  - "sell-off" → "fall".
  - "bad loans" → "non-performing loans".
  - "sold"/"selling price" → "realised price".
  - "goods" → write "products"; the sector is named "FMCG", and "Capital Goods" becomes "Construction & Engineering".
  - "good"/"bad" in any idiom.
  - "should" anywhere (use "can", "may", "is").
  - "cheap"/"expensive" → "lower-cost", "higher-cost".
  - "target price" never.
  - "recommended" (e.g. "recommended dividend") → "proposed dividend".

---
## §A Public REST API (browser → Java, base `/api`)

Java adds or computes everything not marked "pass-through". Pass-through endpoints return the Python body unchanged, except where a `user` block is added.

### A.1 GET /api/meta
Header badge, footer and adapter modes. No params.
```json
{
  "sampleData": true, "asOf": "2026-10-30",
  "adapters": { "broker": "mock", "fundamentals": "mock", "prices": "mock", "surveillance": "mock", "fundNav": "mock", "fundMeta": "mock", "fundHoldings": "mock", "statement": "auto" },
  "llmEnabled": false,
  "disclaimer": "Information only, not investment advice.",
  "defaultIllustrativeAmountInr": 100000
}
```
Built from Python `/internal/health` plus config.

### A.2 GET /api/home
```json
{
  "sampleData": true, "asOf": "2026-10-30", "connected": true, "hasHoldings": true,
  "summary": [
    { "text": "Your holdings are worth ₹12.8 lakh across 6 stocks and 4 mutual funds.", "templateId": "pf.summary.value", "generator": "template" },
    { "text": "Your largest single company exposure is HDFC Bank Ltd at 11.8% of your holdings, 7.7% held directly and 4.1% through funds.", "templateId": "pf.summary.top_exposure", "generator": "template" },
    { "text": "Over the last 1 year, your current holdings moved +12.6% while the Nifty 50 moved +8.9%.", "templateId": "pf.summary.returns", "generator": "template" }
  ],
  "topExposures": [ExposureLine],
  "facts": [PortfolioFact, PortfolioFact, PortfolioFact],
  "watchlist": [WatchlistItem],
  "lastImport": ImportLogEntry
}
```
- `topExposures`: the first 5 COMPANY lines (buckets excluded).
- `watchlist`: at most 5, newest first.
- `lastImport`: ImportLogEntry|null.
- When `hasHoldings` is false: `summary` = [`pf.summary.empty`], `topExposures` = [], and `facts` = [].

**PortfolioFact**
```json
{ "id": "overlap", "sentence": Sentence, "figures": [Figure] }
```
- `id` ∈ `overlap | cost | idle_cash` (always in this order).
- overlap figures: [`overlap_top_pair` PCT]. cost figures: [`yearly_fund_cost` INR, `regular_plan_gap` INR]. idle_cash figures: [`idle_cash` INR].

### A.3 GET /api/portfolio
```json
{
  "sampleData": true, "asOf": "2026-10-30", "connected": true, "hasHoldings": true,
  "totals": {
    "holdingsValue": { "id": "holdings_value", "label": "Value of your holdings", "value": 1277410, "unit": "INR", "display": "₹12.8 lakh", "source": "Calculated from your holdings", "asOf": "2026-10-30", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "Amount you put in", "value": 1068930, "unit": "INR", "display": "₹10.7 lakh" } ], "termId": null },
    "invested": Figure,
    "idleCash": Figure,
    "totalWithCash": Figure
  },
  "summary": [Sentence, Sentence, Sentence],
  "facts": [PortfolioFact, PortfolioFact, PortfolioFact],
  "exposure": { "company": ExposureBreakdown, "sector": ExposureBreakdown, "size": ExposureBreakdown },
  "concentration": {
    "largestCompany": Figure, "top5Companies": Figure, "topSector": Figure, "companyCount": Figure, "holdingCount": Figure,
    "sentences": [Sentence]
  },
  "overlap": {
    "pairs": [ {
      "fundA": { "schemeCode": "900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth" },
      "fundB": { "schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth" },
      "overlap": { "id": "overlap_900101_900201", "label": "Overlap", "value": 41.37, "unit": "PCT", "display": "41.4%", "source": "Calculated from your holdings", "asOf": "2026-09-30", "comparisons": [], "termId": "fund_overlap" },
      "commonCount": 27,
      "topCommon": [ { "key": "HDFCBANK", "name": "HDFC Bank Ltd", "weightA": 8.12, "weightB": 12.95, "minWeight": 8.12 } ]
    } ],
    "sentences": [Sentence]
  },
  "costs": {
    "totalYearly": Figure, "regularGapYearly": Figure,
    "funds": [ {
      "schemeCode": "900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "planType": "REGULAR",
      "value": Figure, "expenseRatio": Figure, "yearlyCost": Figure,
      "directTwin": { "schemeCode": "900102", "name": "Kaveri Flexi Cap Fund - Direct Plan - Growth", "terPct": 0.68 },
      "yearlyGap": Figure
    } ],
    "sentences": [Sentence]
  },
  "mix": { "equityDebt": [MixLine], "stocksFunds": [MixLine], "sentences": [Sentence, Sentence] },
  "returns": {
    "benchmarkName": "Nifty 50",
    "portfolio": ReturnRow,
    "holdings": [ReturnRow],
    "sentences": [Sentence, Sentence]
  },
  "holdings": [ HoldingRow ]
}
```
- `invested`: id `invested`, INR. `idleCash`: id `idle_cash`, INR, comparison PREVIOUS_PERIOD = holdings value. `totalWithCash`: id `total_with_cash`.
- Concentration figure ids: `largest_company` PCT, `top5_companies` PCT, `top_sector` PCT, `company_count` COUNT, `holding_count` COUNT. Comparison kind THRESHOLD: "Equal split across your holdings" = 100/holdingCount.
- `overlap.pairs`: all pairs sorted by overlap descending; empty if fewer than 2 funds. The overlap figure's asOf is the oldest portfolioDate of the two funds.
- Cost figure ids: totalYearly `yearly_fund_cost`, regularGapYearly `regular_plan_gap`; per fund `fund_value`, `expense_ratio` (PCT, comparison PLAN_TWIN when a twin exists, else CATEGORY via bundle `categoryMedianTerPct`), `yearly_cost`, `yearly_gap`. `yearlyGap` is null unless REGULAR with a twin. `directTwin` is null unless REGULAR with a twin.
- Mix: `equityDebt` keys are always EQUITY, DEBT_CASH, OTHER (all present, pct may be 0). `stocksFunds` keys are STOCKS, FUNDS.
- Returns: `holdings` follows the same order as `holdings`. `sentences` = [`pf.summary.returns` or `_unavailable`, `pf.returns.since_buy` or `_unavailable`].

**ReturnRow**
```json
{ "kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd",
  "oneYear": { "id": "return_1y", "label": "Change in the last 1 year", "value": -6.42, "unit": "PCT_CHANGE", "display": "-6.4%", "source": "Calculated from your holdings", "asOf": "2026-10-30", "comparisons": [ { "kind": "INDEX", "label": "Nifty 50, same dates", "value": 8.91, "unit": "PCT_CHANGE", "display": "+8.9%" } ], "termId": null },
  "sinceBuy": Figure,
  "gain": Figure }
```
- `kind` ∈ STOCK|FUND|PORTFOLIO; for the portfolio row `id` = `"PORTFOLIO"` and `name` = `"All your holdings"`.
- `oneYear` is a Figure with null value when there is under 1 year of history.
- `sinceBuy`: id `return_since_buy`, PCT_CHANGE, comparison INDEX "Nifty 50, same dates"; null when firstBuyDate is unknown.
- `gain`: id `gain`, INR = value − cost.

**HoldingRow**
```json
{ "holdingIds": [12], "kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap",
  "quantity": 15, "avgPrice": 3410.0, "lastPrice": Figure, "value": Figure, "weightPct": 4.61,
  "sources": ["KITE"], "firstBuyDate": "2023-06-05", "checkPath": "/stock/TCS" }
```
- `lastPrice`: id `last_price` (stock) or `nav` (fund), INR_PRICE, comparison PREVIOUS_PERIOD 1 year ago. `value`: id `holding_value`.
- `weightPct` is the share of holdings value (largest remainder, Σ = 100).
- `checkPath` is `/stock/{SYM}` or `/fund/{code}`.

### A.4 GET /api/search?q={text}
- `q` must be ≥ 1 char (trimmed). Returns ≤ 10 results. Pass-through of B.2.
```json
{ "sampleData": true, "query": "tata", "results": [ { "kind": "STOCK", "id": "TATASTEEL", "name": "Tata Steel Ltd", "subtitle": "Metals & Mining · Large cap", "checkPath": "/stock/TATASTEEL" } ] }
```

### A.5 GET /api/stocks/{symbol}/check
Pass-through of B.3 plus a `user` block added by Java:
```json
"user": { "holds": true, "quantity": 15, "holdingValue": Figure, "watchlistItemId": null, "note": null }
```
- When not held: `holdingValue` is null and `quantity` is null.
- `note` is the watchlist note if the item is in the watchlist.

### A.6 GET /api/funds/{schemeCode}/check?amount={rupees}
- `amount` is optional.
- Java chooses the amount: the query amount (basis `USER_INPUT`) if given; else the user's holding value in this fund (`HOLDING`); else `defaultIllustrativeAmountInr` (`ILLUSTRATIVE`).
- Java computes the overlap of this fund with every other held fund (OverlapEngine), then POSTs B.4.
- Response = B.4 body plus the same `user` block as A.5 (quantity = units).

### A.7 GET /api/compare?kind={STOCK|FUND}&ids={id1,id2[,id3]}&amount={rupees}
- 2–3 ids, comma-separated. `amount` applies only to funds (same default rules as A.6, using ILLUSTRATIVE when absent).
- Pass-through of B.5.

### A.8 POST /api/try-it-on
Request:
```json
{ "kind": "FUND", "id": "900701", "mode": "SIP", "amountInr": 5000, "months": 12 }
```
- `mode` ∈ LUMP_SUM|SIP. `amountInr` > 0 and ≤ 1e9. `months` is SIP only, 1–60, default 12; for LUMP_SUM it is ignored and echoed as null.

Response:
```json
{
  "sampleData": true, "asOf": "2026-10-30",
  "instrument": { "kind": "FUND", "id": "900701", "name": "Sindhu Large Cap Fund - Direct Plan - Growth", "subtitle": "Large Cap Fund · Direct plan" },
  "input": { "mode": "SIP", "amountInr": 5000, "months": 12, "addedValueInr": 60000, "addedValueDisplay": "₹60,000", "alreadyHeld": false },
  "assumption": { "text": "This shows your portfolio with ₹5,000 a month added to Sindhu Large Cap Fund - Direct Plan - Growth for 12 months (₹60,000 in all), assuming prices stay where they are today.", "templateId": "tio.assumption.sip", "generator": "template" },
  "metrics": {
    "largestCompany": { "before": { "name": "HDFC Bank Ltd", "figure": Figure }, "after": { "name": "HDFC Bank Ltd", "figure": Figure } },
    "topSector": { "before": { "name": "Financial Services", "figure": Figure }, "after": { "name": "Financial Services", "figure": Figure } },
    "sizeMix": { "before": [MixLine], "after": [MixLine] },
    "holdingsCount": { "before": Figure, "after": Figure },
    "overlap": {
      "candidateKind": "FUND",
      "fundOverlaps": [ { "schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "overlap": Figure } ],
      "stockInFunds": [],
      "exposureToCandidate": null
    },
    "yearlyCost": { "before": Figure, "after": Figure, "change": Figure }
  },
  "sentences": [Sentence]
}
```
- `sizeMix` lines use keys LARGE, MID, SMALL, MICRO, DEBT_CASH, OTHER (all six present), with labels "Large cap", "Mid cap", "Small cap", "Micro cap", "Debt & cash", "Other / undisclosed".
- Figure ids: `largest_company`, `top_sector` (PCT); `holding_count` (COUNT); `yearly_fund_cost` before/after (INR) and `yearly_fund_cost_change` (INR).
- Every before/after figure has comparisons [PREVIOUS_PERIOD "Before"], pointing at the before value; a "before" figure compares to itself.
- Stock candidate:
  - `fundOverlaps` = [].
  - `stockInFunds` = [ { "schemeCode", "name", "weight": Figure(PCT id `weight_in_fund`, comparisons []) } ].
  - `exposureToCandidate` = { "before": Figure, "after": Figure } (PCT ids `candidate_exposure`).
- Fund candidate: `stockInFunds` = [], `exposureToCandidate` = null, and `fundOverlaps` excludes the candidate itself.
- `sentences` come in this fixed order: largest_company, top_sector, size_mix, holdings_count (or holdings_count_same), overlap (fund/stock/none variant), cost (or cost_stock).

### A.9 GET /api/glossary
Pass-through of B.6.

### A.10 GET /api/explain?term={termId}&kind={STOCK|FUND}&id={id}
- `kind` and `id` are optional; both or neither.
- Pass-through of B.7.

### A.11 Watchlist
| Method | Path | Request / response |
|---|---|---|
| GET | `/api/watchlist` | `{ "sampleData": true, "items": [WatchlistItem] }` (newest first) |
| POST | `/api/watchlist` | body `{ "kind": "STOCK", "instrumentId": "TCS", "note": "..." }` (note 0–1000 chars). Response 201 = WatchlistItem plus `sampleData`. If the item already exists, returns 200 with the existing item and its note updated |
| PATCH | `/api/watchlist/{id}` | body `{ "note": "..." }` → 200 WatchlistItem plus `sampleData` |
| DELETE | `/api/watchlist/{id}` | 204 |

Java resolves `name`/`subtitle`/`latest` via B.8. Unknown instrument → 404.

### A.12 Connection and Kite login
**GET /api/connection**
```json
{
  "sampleData": true, "brokerMode": "mock", "status": "CONNECTED", "accountLabel": "Your Zerodha account (sample)",
  "loginUrl": null, "lastImportAt": "2026-10-30T18:40:03+05:30",
  "imports": [ImportLogEntry],
  "holdingsSummary": { "stockCount": 6, "fundCount": 4, "bySource": { "KITE": 10, "STATEMENT": 0, "MANUAL": 0 } }
}
```
- `brokerMode` ∈ mock|kite_mcp|kite_connect. `status` ∈ NOT_CONNECTED|PENDING_LOGIN|CONNECTED|FAILED.
- `accountLabel` is string|null. `imports` holds the last 10, newest first.

**POST /api/connect/kite/start** (no body) → `{ "sampleData": true, "brokerMode": "mock", "status": "CONNECTED", "loginUrl": null, "message": "Sample account connected." }`
- **mock:** status CONNECTED immediately.
- **kite_mcp:** status PENDING_LOGIN with `loginUrl` (from the MCP `login` tool). The FE opens it in a new tab and polls the status endpoint every 2 s until CONNECTED, FAILED or `kite.loginTimeoutSeconds`.
- **kite_connect:** PENDING_LOGIN with `loginUrl` = `https://kite.zerodha.com/connect/login?v=3&api_key={apiKey}`. The FE navigates to it in the same tab.

**GET /api/connect/kite/status** → `{ "sampleData": false, "brokerMode": "kite_mcp", "status": "PENDING_LOGIN", "accountLabel": null, "message": "Waiting for you to finish logging in to Kite." }`

**GET /api/connect/kite/callback?request_token=...&action=login&status=success** (kite_connect only; this is `kite.redirectUrl`)
- Java calls B.10 `login/complete`, then responds `302 Location: {services.frontendBaseUrl}/connect?kite=connected`, or `?kite=failed` on error or when `status` ≠ success.

**POST /api/connect/kite/disconnect** → `{ "sampleData": false, "brokerMode": "kite_mcp", "status": "NOT_CONNECTED", "loginUrl": null, "message": "Disconnected. Imported holdings are kept." }`

**FE rule:** after status CONNECTED (any mode), or on `/connect?kite=connected`, call A.13 `POST /api/import/kite`.

### A.13 Imports and holdings
**POST /api/import/kite** (no body). Requires CONNECTED, else 409 BROKER_NOT_CONNECTED. Calls B.10 portfolio.
```json
{ "sampleData": true, "importId": 7, "source": "KITE", "status": "SUCCESS", "importedAt": "2026-10-30T18:40:03+05:30",
  "stockCount": 6, "fundCount": 4, "idleCashInr": 42350.75, "unmatched": [], "message": "Imported 6 stocks, 4 funds and idle cash." }
```
- `unmatched` items: `{ "name": "Example Gilt Fund - Direct Growth", "isin": "INF000X01ABC", "reason": "Fund not found in fund list." }`.
- Status is PARTIAL when unmatched is non-empty.

**POST /api/import/statement** (multipart/form-data): `file` (PDF, ≤ 10 MB), `password` (string).
- Java base64-encodes and calls B.11.
- Response has the same shape as /api/import/kite, with `source` = "STATEMENT" and `idleCashInr` = null.
- Errors: 422 STATEMENT_PASSWORD_INVALID or STATEMENT_UNREADABLE.

**GET /api/holdings**
```json
{ "sampleData": true, "holdings": [ { "id": 12, "kind": "STOCK", "instrumentId": "TCS", "name": "Tata Consultancy Services Ltd", "quantity": 15, "avgPrice": 3410.0, "firstBuyDate": "2023-06-05", "source": "KITE", "importedAt": "2026-10-30T18:40:03+05:30" } ] }
```

**POST /api/holdings** (manual add): body `{ "kind": "FUND", "instrumentId": "900401", "quantity": 120.5, "avgPrice": 88.1, "firstBuyDate": "2025-01-15" }`
- `firstBuyDate` is nullable. quantity > 0, avgPrice > 0.
- Validated via B.8 (404 if unknown). Response 201 = one holding object (the same as a `holdings[]` item) plus `"sampleData"`.

**DELETE /api/holdings/{id}** → 204.

---
### A.14 Live quote and today's account activity (added 13 Nov 2026)

Both are passed through from Python **uncached**, because they are only useful when fresh.

`GET /api/stocks/{symbol}/quote` → `Quote`:
`{sampleData, available, symbol, reason?, source, asOf (ISO datetime), lastPrice, lastPriceDisplay, open, openDisplay, high, highDisplay, low, lowDisplay, prevClose, prevCloseDisplay, changeDisplay, volume, volumeDisplay, rangePosition (0..1 within today's low–high, or null)}`.
When no live price can be had (not connected, symbol unknown, broker error) the body is `{sampleData, available: false, symbol, reason}` with HTTP 200.

`GET /api/account/activity` → `Activity`:
`{sampleData, connected, source, asOf, sentences: Sentence[], positions: [{symbol, exchange, product, quantity, avgPrice, avgPriceDisplay, lastPrice, lastPriceDisplay, pnl, pnlDisplay}], orders: {total, complete, open, cancelled} | null, tradesToday: number | null, gtts: [{symbol, kind: SINGLE|TWO_LEG, triggerPrices, triggerDisplays, lastPriceAtSetup, quantity, status, createdAt}]}`.
A part the broker could not return is `null` (orders, tradesToday) or empty. Direction of a price trigger (add or reduce) is deliberately not shown.

Internal: `GET /internal/broker/quote?symbol=` and `GET /internal/broker/activity` (B.10), same bodies. Kite MCP tools used: `get_quotes`, `get_positions`, `get_orders`, `get_trades`, `get_gtts`; Kite Connect: `GET /quote`, `/portfolio/positions`, `/orders`, `/trades`, `/gtt/triggers`. With `prices: broker_then_nse_eod`, Nifty 50 history also comes from the broker (`get_historical_data`, NIFTY 50 index token).

## §B Internal REST API (Java → Python, base `/internal`)

Python listens on `ports.python`. Bodies are JSON. Errors follow §0.2. Timeouts: Java uses 10 s, except `/internal/broker/*` and `/internal/statements/parse` which use 60 s.

### B.1 GET /internal/health
```json
{ "status": "ok", "sampleData": true, "asOf": "2026-10-30", "version": "0.1.0",
  "adapters": { "broker": "mock", "fundamentals": "mock", "prices": "mock", "surveillance": "mock", "fundNav": "mock", "fundMeta": "mock", "fundHoldings": "mock", "statement": "auto" },
  "statementParser": "fallback", "llmEnabled": false }
```
`statementParser` ∈ casparser|fallback (the one actually in use).

### B.2 GET /internal/search?q={text}&limit={1..10, default 10}
```json
{ "sampleData": true, "query": "tata", "results": [ { "kind": "STOCK", "id": "TATASTEEL", "name": "Tata Steel Ltd", "subtitle": "Metals & Mining · Large cap", "checkPath": "/stock/TATASTEEL" } ] }
```
- Matching is case-insensitive over symbol, name, scheme name and AMC.
- Ranking: exact symbol, then prefix, then substring; stocks before funds on ties; then name ascending.
- Stock subtitle: `{sector} · {Large|Mid|Small|Micro} cap`. Fund subtitle: `{category} · {Direct|Regular} plan`.

### B.3 GET /internal/stocks/{symbol}/check → StockCheck
Unknown symbol → 404.
```json
{
  "sampleData": true, "asOf": "2026-10-30",
  "instrument": {
    "kind": "STOCK", "symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE", "isin": "INESMP000002",
    "sector": "Information Technology", "industry": "IT Services", "sizeBand": "LARGE", "fictional": false,
    "lastPrice": { "id": "last_price", "label": "Last price", "value": 3925.4, "unit": "INR_PRICE", "display": "₹3,925.40", "source": "Sample data", "asOf": "2026-10-30", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "1 year ago", "value": 4194.2, "unit": "INR_PRICE", "display": "₹4,194.20" } ], "termId": null },
    "marketCap": { "id": "market_cap", "label": "Market value of the company", "value": 14202000000000, "unit": "INR", "display": "₹14,20,200 crore", "source": "Sample data", "asOf": "2026-10-30", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "1 year ago", "value": 15175000000000, "unit": "INR", "display": "₹15,17,500 crore" } ], "termId": "market_cap" }
  },
  "answers": [
    {
      "id": "business", "order": 1, "question": "What does the company do and how does it earn money?",
      "sentences": [
        { "text": "Tata Consultancy Services Ltd builds and runs software and technology systems for large companies around the world.", "templateId": "stk.business.about", "generator": "template" },
        { "text": "It earned ₹2,55,300 crore in revenue in FY2026, up from ₹1,91,800 crore in FY2023.", "templateId": "stk.business.revenue", "generator": "template" },
        { "text": "Banking and financial services clients bring in 31.5% of revenue, the largest single business.", "templateId": "stk.business.segment", "generator": "template" }
      ],
      "figures": [
        { "id": "revenue_fy", "label": "Revenue, FY2026 (Apr 2025–Mar 2026)", "value": 2553000000000, "unit": "INR", "display": "₹2,55,300 crore", "source": "Sample data", "asOf": "2026-03-31", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "FY2023", "value": 1918000000000, "unit": "INR", "display": "₹1,91,800 crore" } ], "termId": "revenue" },
        { "id": "top_segment_share", "label": "Largest business, share of revenue", "value": 31.5, "unit": "PCT", "display": "31.5%", "source": "Sample data", "asOf": "2026-03-31", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "A year earlier", "value": 32.1, "unit": "PCT", "display": "32.1%" } ], "termId": null }
      ],
      "details": { "title": "Revenue by business", "columns": ["Business", "Share of revenue", "A year earlier"], "rows": [["Banking and financial services", "31.5%", "32.1%"], ["Retail and consumer", "15.2%", "14.8%"]] }
    }
  ],
  "facts": [
    {
      "id": "promoter_holding", "order": 1, "title": "Promoter holding", "termId": "promoter_holding", "available": true,
      "sentences": [ { "text": "Promoters own 71.8% of the company, unchanged from 71.8% four quarters ago.", "templateId": "stk.fact.promoter_holding", "generator": "template" } ],
      "figures": [ { "id": "promoter_holding", "label": "Promoter holding", "value": 71.77, "unit": "PCT", "display": "71.8%", "source": "Sample data", "asOf": "2026-09-30", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "Four quarters ago", "value": 71.77, "unit": "PCT", "display": "71.8%" } ], "termId": "promoter_holding" } ],
      "details": { "title": "Promoter holding by quarter", "columns": ["Quarter end", "Promoter holding", "Pledged (of promoter shares)"], "rows": [["30 Sep 2026", "71.8%", "0.0%"], ["30 Jun 2026", "71.8%", "0.0%"]] }
    }
  ],
  "priceHistory": PriceHistory,
  "drawdown": Drawdown,
  "peers": { "groupName": "IT services", "members": [ { "name": "Infosys Ltd", "symbol": "INFY", "checkAvailable": true }, { "name": "HCL Technologies Ltd", "symbol": "HCLTECH", "checkAvailable": false } ] }
}
```
The example truncates `answers` (always 5) and `facts` (always 8); each item has the full Answer/Fact shape.

**Stock answers (fixed ids and order).**

| order | id | question (exact) | figures (id: unit; comparison kinds) | details |
|---|---|---|---|---|
| 1 | business | What does the company do and how does it earn money? | revenue_fy: INR; PREVIOUS_PERIOD(3 yrs earlier) · top_segment_share: PCT; PREVIOUS_PERIOD | Revenue by business |
| 2 | growth | Is it growing and profitable? | revenue_cagr_3y: PCT; PEERS · profit_cagr_3y: PCT; PEERS · operating_margin: PCT; OWN_HISTORY(5-yr median), PEERS · roe: PCT; PEERS | Five years: revenue, operating profit, net profit, margin |
| 3 | safety | Is it financially safe? | non-financial: total_debt: INR; PREVIOUS_PERIOD · debt_to_equity: TIMES; OWN_HISTORY, PEERS · interest_coverage: TIMES; PEERS · cash: INR; PREVIOUS_PERIOD. isFinancial: net_worth: INR; PREVIOUS_PERIOD · roe: PCT; PEERS | Five years: debt, cash, net worth, interest |
| 4 | price | How is it priced against its own history and its peers? | pe: TIMES; OWN_HISTORY, PEERS (null if loss) · pb: TIMES; OWN_HISTORY, PEERS · market_cap: INR; PREVIOUS_PERIOD · dividend_yield: PCT; PEERS | Monthly P/E and P/B, last 5 years (yearly rows) |
| 5 | recent | What changed recently? | quarter_revenue_yoy: PCT_CHANGE; PREVIOUS_PERIOD · quarter_profit_yoy: PCT_CHANGE; PREVIOUS_PERIOD · price_change_90d: PCT_CHANGE; INDEX | Recent events (date, event) |

**Stock facts (fixed ids and order).**

| order | id | title (exact) | figures (id: unit; comparison) | available=false when |
|---|---|---|---|---|
| 1 | promoter_holding | Promoter holding | promoter_holding: PCT; PREVIOUS_PERIOD(4 quarters ago). Sentence states direction: rose / fell / unchanged (abs change < 0.1) | no shareholding data |
| 2 | promoter_pledge | Promoter pledge | promoter_pledge: PCT (of promoter shares); PREVIOUS_PERIOD | no shareholding data |
| 3 | profit_last_3y | Profit or loss in each of the last three years | net_profit_y1, net_profit_y2, net_profit_y3: INR (oldest→latest; label "FY2024 (Apr 2023–Mar 2024)"); PREVIOUS_PERIOD(previous year) | < 3 annual rows |
| 4 | debt_to_earnings | Debt against yearly earnings | debt_to_profit: TIMES (= total debt / latest yearly net profit); OWN_HISTORY(3 yrs earlier), PEERS. Latest profit ≤ 0 → value null, sentence states the loss and the debt in ₹ (still available) | isFinancial (sentence explains deposits are the bank's raw material) |
| 5 | price_move_30d | Price move in the last 30 days | price_change_30d: PCT_CHANGE; INDEX(Nifty 50 same dates) · results_in_window: TEXT ("Yes, on 9 Oct 2026" / "No") | < 30 days of prices |
| 6 | avg_traded_value | Average daily trading value | avg_daily_traded_value: INR (mean of close×volume, last 20 sessions); OWN_HISTORY(same 20 sessions a year earlier), PEERS | no volume data |
| 7 | size_band | Size band | market_cap: INR; THRESHOLD(lower cut-off of its band) · size_band: TEXT ("Large cap, rank 2 by market value") | — |
| 8 | surveillance | NSE surveillance lists (ASM, GSM, ESM) | surveillance_status: TEXT ("ASM long-term stage II since 14 Aug 2026" / "Not on ASM, GSM or ESM lists") | surveillance source unavailable |

### B.4 POST /internal/funds/{schemeCode}/check → FundCheck
Request:
```json
{ "amountInr": 115448.0, "amountBasis": "HOLDING",
  "userFunds": [ { "schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "overlapPct": 41.37, "commonCount": 27 } ] }
```
- `amountBasis` ∈ HOLDING|ILLUSTRATIVE|USER_INPUT.
- `userFunds` lists the other held funds with overlap already computed by Java; it may be empty.

Response:
```json
{
  "sampleData": true, "asOf": "2026-10-30",
  "instrument": {
    "kind": "FUND", "schemeCode": "900101", "isin": "INFSMP900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "shortName": "Kaveri Flexi Cap (Regular)",
    "amc": "Kaveri Mutual Fund", "category": "Flexi Cap Fund", "categoryGroup": "EQUITY", "planType": "REGULAR",
    "twin": { "schemeCode": "900102", "name": "Kaveri Flexi Cap Fund - Direct Plan - Growth", "planType": "DIRECT" },
    "benchmark": { "id": "NIFTY500_TRI", "name": "Nifty 500 TRI" },
    "nav": { "id": "nav", "label": "NAV (price of one unit)", "value": 62.4012, "unit": "INR_PRICE", "display": "₹62.40", "source": "Sample data", "asOf": "2026-10-30", "comparisons": [ { "kind": "PREVIOUS_PERIOD", "label": "1 year ago", "value": 56.1803, "unit": "INR_PRICE", "display": "₹56.18" } ], "termId": "nav" }
  },
  "amount": { "amountInr": 115448.0, "display": "₹1.2 lakh", "basis": "HOLDING" },
  "answers": [Answer],
  "facts": [Fact],
  "priceHistory": PriceHistory,
  "drawdown": Drawdown
}
```
- `twin` is null if there is no twin.
- `answers` always has 5 entries and `facts` always 8 (per the tables below).

**Fund answers.**

| order | id | question (exact) | figures (id: unit; comparisons) | details |
|---|---|---|---|---|
| 1 | holdings | What does it invest in and who runs it? | equity_share: PCT; THRESHOLD(category minimum) · holdings_count: COUNT; CATEGORY · manager_tenure: YEARS; CATEGORY | Top 10 holdings (name, sector, weight); asset mix; managers (name, since) |
| 2 | performance | How has it done against its benchmark and category over 3, 5 and 10 years? | return_3y, return_5y, return_10y: PCT (yearly average, CAGR); BENCHMARK, CATEGORY. value null + display "Not available" when the fund is younger than the period | Period table + calendar-year returns 2021–2025 (fund, benchmark) |
| 3 | bumpiness | How bumpy has the ride been? | worst_fall: PCT_CHANGE; BENCHMARK, CATEGORY · recovery_time: DAYS; BENCHMARK (null if not recovered) | Five largest falls (peak, trough, fall, recovered on) |
| 4 | cost | What does it cost per year on your amount? | expense_ratio: PCT; CATEGORY(median, same plan type) · yearly_cost: INR (amount × TER); PLAN_TWIN (twin's cost; else CATEGORY) · twin_gap: INR (null if no twin); PLAN_TWIN | — |
| 5 | recent | What changed recently? | aum: INR; PREVIOUS_PERIOD(1 year ago) · aum_change_1y: PCT_CHANGE; PREVIOUS_PERIOD | Changes in top 10 since last month; events (manager, benchmark, expense changes) |

**Fund facts.**

| order | id | title (exact) | figures |
|---|---|---|---|
| 1 | plan_type | Direct or regular plan, and the yearly cost difference | plan_type: TEXT ("Regular plan") · plan_cost_gap: INR on amount; PLAN_TWIN (available=false if no twin is known; the sentence says so) |
| 2 | expense_vs_category | Expense ratio against the category | expense_ratio: PCT; CATEGORY(median, same plan type) |
| 3 | age_and_size | Fund age and size | fund_age: YEARS; CATEGORY · aum: INR; CATEGORY |
| 4 | years_trailed_benchmark | Years out of the last five it trailed its benchmark | years_trailed: COUNT (calendar 2021–2025); CATEGORY(average). details: per-year fund vs benchmark. available=false if < 5 full calendar years (the sentence gives the count over the available years) |
| 5 | category_mandate | Category and what it may hold | category: TEXT · equity_share: PCT; THRESHOLD(category minimum) |
| 6 | top10_share | Share of the fund in its top ten holdings | top10_share: PCT; CATEGORY(median). Debt fund: share of the top 10 papers if available, else available=false |
| 7 | exit_load_lockin | Exit load and lock-in | exit_load: TEXT ("1% if you take money out within 365 days" / "None") · lock_in: YEARS; THRESHOLD("ELSS lock-in set by law: 3 years") for ELSS, else CATEGORY |
| 8 | overlap_with_holdings | Overlap with funds you already hold | one figure per userFunds item: id `overlap_{schemeCode}`, PCT, label = fund name, comparisons []. Empty userFunds → available=true, figures [], template `fnd.fact.overlap_none` |

### B.5 GET /internal/compare?kind={STOCK|FUND}&ids={a,b[,c]}&amountInr={n}
`amountInr` is required for FUND and ignored for STOCK. If any id is unknown → 404.
```json
{
  "sampleData": true, "asOf": "2026-10-30", "kind": "STOCK",
  "instruments": [ { "kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap", "checkPath": "/stock/TCS" } ],
  "rows": [
    { "id": "growth", "order": 2, "question": "Is it growing and profitable?",
      "cells": [ { "instrumentId": "TCS", "sentences": [Sentence], "figures": [Figure] } ] }
  ]
}
```
- `rows` has exactly 5 entries (the answer ids for the kind, in order).
- Each row has one cell per instrument in request order. Cells reuse the same Answer content as the checks.
- Fund compare uses empty `userFunds`.

### B.6 GET /internal/glossary
```json
{ "sampleData": false, "terms": [ { "id": "pe_ratio", "term": "P/E (price to earnings)", "aliases": ["PE", "price to earnings"], "meaning": "How many rupees investors pay today for each rupee of the company's yearly profit.", "appliesTo": ["STOCK"], "figureIds": ["pe"] } ] }
```
- `appliesTo` ⊆ {STOCK, FUND, PORTFOLIO}. `figureIds` lists Figure ids in check payloads that show this term's value (may be empty).
- At least these 48 ids must exist:
  - `market_cap, size_band, large_cap, mid_cap, small_cap, micro_cap, revenue, operating_margin, net_profit, eps, pe_ratio, pb_ratio, roe, debt, debt_to_equity, debt_to_profit, interest_coverage, promoter_holding, promoter_pledge, fii_holding, dividend_yield, avg_daily_traded_value, surveillance_asm, surveillance_gsm, surveillance_esm, cagr, worst_fall, recovery_time, nifty_50, peers`
  - `nav, expense_ratio, direct_plan, regular_plan, aum, exit_load, lock_in, elss, index_fund, benchmark, tri, category_average, top10_share, fund_overlap, fund_manager, sip`
  - `look_through_exposure, idle_cash`

### B.7 GET /internal/explain?term={id}&kind={STOCK|FUND}&id={id}
```json
{
  "sampleData": true,
  "term": { "id": "pe_ratio", "term": "P/E (price to earnings)", "aliases": ["PE", "price to earnings"], "meaning": "How many rupees investors pay today for each rupee of the company's yearly profit.", "appliesTo": ["STOCK"], "figureIds": ["pe"] },
  "instrument": { "kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap" },
  "thisFigure": Figure,
  "typical": { "kind": "PEERS", "label": "Median of IT services peers", "value": 25.1, "unit": "TIMES", "display": "25.1x" },
  "sentence": { "text": "For Tata Consultancy Services Ltd this is 29.8x; the median for its IT services peers is 25.1x.", "templateId": "glossary.explain.with_typical", "generator": "template" }
}
```
- `instrument`, `thisFigure`, `typical` and `sentence` are null when no kind/id is given or the term has no figure for that kind.
- `typical` is the figure's PEERS or CATEGORY comparison, else null.

### B.8 POST /internal/instruments/bundle
Request: `{ "stocks": ["TCS", "HDFCBANK"], "funds": ["900101", "900201"] }`
```json
{
  "sampleData": true, "asOf": "2026-10-30",
  "stocks": [ { "symbol": "TCS", "name": "Tata Consultancy Services Ltd", "isin": "INESMP000002", "sector": "Information Technology", "industry": "IT Services", "sizeBand": "LARGE", "subtitle": "Information Technology · Large cap", "lastPrice": 3925.4, "lastPriceDate": "2026-10-30", "priceOneYearAgo": 4194.2, "source": "Sample data", "checkAvailable": true } ],
  "funds": [ {
    "schemeCode": "900101", "isin": "INFSMP900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "subtitle": "Flexi Cap Fund · Regular plan",
    "amc": "Kaveri Mutual Fund", "category": "Flexi Cap Fund", "categoryGroup": "EQUITY", "planType": "REGULAR",
    "terPct": 1.72, "categoryMedianTerPct": 1.61, "twinSchemeCode": "900102", "twinName": "Kaveri Flexi Cap Fund - Direct Plan - Growth", "twinTerPct": 0.68,
    "nav": 62.4012, "navDate": "2026-10-30", "navOneYearAgo": 56.1803,
    "assetMix": { "equityPct": 96.5, "debtPct": 0.0, "cashPct": 3.5, "otherPct": 0.0 },
    "portfolioDate": "2026-09-30",
    "holdings": [ { "key": "HDFCBANK", "symbol": "HDFCBANK", "isin": null, "name": "HDFC Bank Ltd", "sector": "Financial Services", "sizeBand": "LARGE", "weightPct": 8.12, "checkAvailable": true } ],
    "source": "Sample data"
  } ],
  "notFound": [ { "kind": "STOCK", "id": "XYZ" } ]
}
```
- `assetMix` sums to 100.00. Holdings are equity constituents only, with weightPct in percent of the fund.
- `key` = symbol ?? isin ?? "NAME:" + upper(name). `sizeBand` is nullable.
- Missing ids go to `notFound` (no error).

### B.9 POST /internal/prices/points
Request:
```json
{ "items": [ { "kind": "STOCK", "id": "TCS", "dates": ["2025-10-30", "2023-06-05", "2026-10-30"] }, { "kind": "INDEX", "id": "NIFTY50", "dates": ["2025-10-30", "2026-10-30"] } ] }
```
`kind` ∈ STOCK|FUND|INDEX. FUND values are NAV.

Response:
```json
{ "sampleData": true, "asOf": "2026-10-30",
  "items": [ { "kind": "STOCK", "id": "TCS", "values": [ { "requestedDate": "2025-10-30", "date": "2025-10-30", "value": 4194.2 }, { "requestedDate": "2023-06-05", "date": "2023-06-05", "value": 3288.15 }, { "requestedDate": "2026-10-30", "date": "2026-10-30", "value": 3925.4 } ] } ] }
```
- `date` is the last available on or before `requestedDate`. If no such point exists, `date` and `value` are null.
- An unknown id gives values with nulls (no error).

### B.10 Broker (session state lives in Python memory)
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/internal/broker/login/start` | — | `{ "sampleData": true, "brokerMode": "mock", "status": "CONNECTED", "loginUrl": null, "message": "Sample account connected." }` |
| GET | `/internal/broker/login/status` | — | `{ "sampleData": false, "brokerMode": "kite_mcp", "status": "CONNECTED", "accountLabel": "Your Zerodha account (AB1234)", "message": "Connected." }` |
| POST | `/internal/broker/login/complete` | `{ "requestToken": "abc123" }` | same shape as status. Only kite_connect; other modes → 400 |
| POST | `/internal/broker/logout` | — | same shape as start, status NOT_CONNECTED |
| GET | `/internal/broker/portfolio` | — | see below; 409 BROKER_NOT_CONNECTED if not connected |

- **mock:** start → CONNECTED. `accountLabel` = "Your Zerodha account (sample)".
- **kite_mcp:**
  - start opens an MCP streamable-HTTP session to `kite.mcpUrl` (held open in a background thread) and calls the tool `login`. The first URL in the returned text is `loginUrl`; status is PENDING_LOGIN.
  - status calls `get_profile`: success → CONNECTED; an auth error → PENDING_LOGIN; after `loginTimeoutSeconds` → FAILED.
- **kite_connect:**
  - start → PENDING_LOGIN with `https://kite.zerodha.com/connect/login?v=3&api_key={apiKey}`.
  - complete: checksum = sha256(apiKey + requestToken + apiSecret); `POST https://api.kite.trade/session/token` (form: api_key, request_token, checksum); the access token is kept in memory only → CONNECTED.
- **Read-only guard:** every MCP `call_tool` and every Kite Connect request passes through `broker_guard`. Anything not listed below raises BROKER_FORBIDDEN_CALL (403) before any network I/O.
  - MCP allow-list (exact): `login, get_profile, get_margins, get_holdings, get_mf_holdings, get_positions, get_quotes, get_ltp, get_ohlc, get_historical_data, search_instruments, get_orders, get_trades, get_gtts`.
  - Kite Connect allow-list (method + path regex): `GET /user/profile`, `GET /user/margins(/equity)?`, `GET /portfolio/holdings`, `GET /portfolio/positions`, `GET /mf/holdings`, `GET /quote`, `GET /quote/ltp`, `GET /quote/ohlc`, `GET /instruments(/NSE)?`, `GET /instruments/historical/\d+/(day|minute)`, `GET /orders`, `GET /trades`, `GET /gtt/triggers`, `POST /session/token`, `DELETE /session/token`.

Portfolio response:
```json
{ "sampleData": true, "source": "Your Zerodha account", "asOf": "2026-10-30",
  "accountLabel": "Your Zerodha account (sample)",
  "stocks": [ { "symbol": "TCS", "isin": "INESMP000002", "quantity": 15, "avgPrice": 3410.0, "lastPrice": 3925.4, "firstBuyDate": "2023-06-05" } ],
  "funds": [ { "schemeCode": "900101", "isin": "INFSMP900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "units": 1850.234, "avgNav": 62.4, "lastNav": 62.4012, "firstBuyDate": "2021-12-01" } ],
  "idleCashInr": 42350.75,
  "unmatched": [ { "name": "Example Gilt Fund - Direct Growth", "isin": "INF000X01ABC", "reason": "Fund not found in fund list." } ] }
```
- `firstBuyDate` is null for live Kite data.
- `schemeCode` is never null in `funds`; unmapped ISINs go to `unmatched`.
- Idle cash = `get_margins` equity available cash (`equity.available.live_balance`).
- Stocks with quantity 0 (including t1_quantity) are skipped.

### B.11 POST /internal/statements/parse
Request: `{ "filename": "cas_oct2026.pdf", "fileBase64": "JVBERi0xLjcK...", "password": "ABCDE1234F" }`
```json
{ "sampleData": false, "parser": "fallback", "statementType": "CAMS", "statementDate": "2026-10-15",
  "funds": [ { "schemeCode": "900701", "isin": "INFSMP900701", "name": "Sindhu Large Cap Fund - Direct Plan - Growth", "amc": "Sindhu Mutual Fund", "units": 812.441, "nav": 48.2201, "navDate": "2026-10-14", "valueInr": 39176.5, "avgCostNav": null } ],
  "unmatched": [ { "name": "Example Gilt Fund - Direct Growth", "isin": "INF000X01ABC", "reason": "Fund not found in fund list." } ] }
```
- `parser` ∈ casparser|fallback. `statementType` ∈ CAMS|KFINTECH|UNKNOWN. `avgCostNav` is number|null (cost value / units if the statement shows cost).
- Investor name, PAN, email and folio are never returned or stored.
- Errors: wrong password → 422 STATEMENT_PASSWORD_INVALID; no funds found → 422 STATEMENT_UNREADABLE.
- Java stores each fund as a holding with quantity = units, avgPrice = avgCostNav ?? nav, firstBuyDate = null.

### B.12 POST /internal/narrate
Request:
```json
{ "items": [
    { "key": "summary.0", "templateId": "pf.summary.value", "facts": { "totalValueInr": { "value": 1277410, "unit": "INR" }, "stockCount": { "value": 6, "unit": "COUNT" }, "fundCount": { "value": 4, "unit": "COUNT" } } },
    { "key": "fact.overlap", "templateId": "pf.fact.overlap", "facts": { "fundA": { "value": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "unit": "TEXT" }, "fundB": { "value": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "unit": "TEXT" }, "overlapPct": { "value": 41.37, "unit": "PCT" }, "commonCount": { "value": 27, "unit": "COUNT" } } }
  ],
  "useLlm": true }
```
Response:
```json
{ "sampleData": false, "items": [
    { "key": "summary.0", "sentence": { "text": "Your holdings are worth ₹12.8 lakh across 6 stocks and 4 mutual funds.", "templateId": "pf.summary.value", "generator": "template" } },
    { "key": "fact.overlap", "sentence": { "text": "Kaveri Flexi Cap Fund - Regular Plan - Growth and Narmada Nifty 50 Index Fund - Direct Plan - Growth hold 27 companies in common, adding up to an overlap of 41.4%.", "templateId": "pf.fact.overlap", "generator": "template" } }
  ] }
```
- `key` is chosen by Java and echoed; response items keep request order.
- An unknown templateId, a missing fact key or a wrong unit → 400 BAD_REQUEST with `details.key` and `details.missing`. Extra keys are ignored.
- **LLM path:** used only if `useLlm` is true and `llm.provider` ≠ none. The prompt contains only the rendered template sentence and the facts' display strings. The output is rejected (falling back to the template, `generator: "template"`) if any of these hold: it matches the banned regex; it contains a number token not present in the facts' displays or the template text; it is longer than 2× the template length; the call fails or times out.

**Template list (Java chooses ids; fact keys and units are exact; Python stores this text).**

| templateId | fact keys (unit) | text |
|---|---|---|
| pf.summary.value | totalValueInr INR, stockCount COUNT, fundCount COUNT | Your holdings are worth {totalValueInr} across {stockCount\|stock\|stocks} and {fundCount\|mutual fund\|mutual funds}. |
| pf.summary.empty | — | You have not added any holdings yet. Connect your Zerodha account or add a statement to see what you own. |
| pf.summary.top_exposure | companyName TEXT, companyPct PCT, directPct PCT, throughFundsPct PCT | Your largest single company exposure is {companyName} at {companyPct} of your holdings, {directPct} held directly and {throughFundsPct} through funds. |
| pf.summary.returns | windowLabel TEXT, portfolioReturnPct PCT_CHANGE, niftyReturnPct PCT_CHANGE | Over the last {windowLabel}, your current holdings moved {portfolioReturnPct} while the Nifty 50 moved {niftyReturnPct}. |
| pf.summary.returns_unavailable | windowLabel TEXT | There is not enough price history yet to compare your holdings with the Nifty 50 over the last {windowLabel}. |
| pf.fact.overlap | fundA TEXT, fundB TEXT, overlapPct PCT, commonCount COUNT | {fundA} and {fundB} hold {commonCount\|company\|companies} in common, adding up to an overlap of {overlapPct}. |
| pf.fact.overlap_none | fundCount COUNT | With {fundCount\|fund\|funds}, there is no pair of funds to compare for overlap. |
| pf.fact.cost | yearlyCostInr INR, regularGapInr INR | Your funds cost about {yearlyCostInr} a year in fees. Regular plans add {regularGapInr} a year compared with the direct plans of the same funds. |
| pf.fact.cost_direct_only | yearlyCostInr INR | Your funds cost about {yearlyCostInr} a year in fees, and all of them are direct plans. |
| pf.fact.cost_none | — | You hold no mutual funds, so there is no yearly fund fee. |
| pf.fact.idle_cash | idleCashInr INR, idleCashPct PCT | {idleCashInr} is sitting as cash in your trading account, {idleCashPct} of your holdings plus cash. |
| pf.fact.idle_cash_none | — | No idle cash was reported in your trading account. |
| pf.exposure.company | companyName TEXT, companyPct PCT, directPct PCT, throughFundsPct PCT, companyCount COUNT | {companyName} is your largest company exposure at {companyPct}: {directPct} direct and {throughFundsPct} through funds. You own pieces of {companyCount\|company\|companies} in all. |
| pf.exposure.sector | sectorName TEXT, sectorPct PCT, sectorCount COUNT | {sectorName} is your largest sector at {sectorPct}, out of {sectorCount\|sector\|sectors}. |
| pf.exposure.size | largePct PCT, midPct PCT, smallPct PCT, microPct PCT, debtCashPct PCT | By company size: large {largePct}, mid {midPct}, small {smallPct}, micro {microPct}; debt and cash {debtCashPct}. |
| pf.exposure.other | otherPct PCT | {otherPct} of your money sits in fund holdings that are not disclosed company by company, shown as Other / undisclosed. |
| pf.concentration | top5Pct PCT, holdingCount COUNT | Your five largest company exposures add up to {top5Pct} of your holdings, across {holdingCount\|holding\|holdings}. |
| pf.mix.equity_debt | equityPct PCT, debtCashPct PCT, otherPct PCT | {equityPct} of your money is in shares, {debtCashPct} in debt and cash, and {otherPct} in other assets. |
| pf.mix.stocks_funds | stocksPct PCT, fundsPct PCT | {stocksPct} is in stocks you hold directly and {fundsPct} is in mutual funds. |
| pf.returns.since_buy | portfolioGainPct PCT_CHANGE, niftySameDatesPct PCT_CHANGE, coveredCount COUNT | Since you first invested, {coveredCount\|holding\|holdings} with known purchase dates moved {portfolioGainPct}; the same money put into the Nifty 50 on the same dates would have moved {niftySameDatesPct}. |
| pf.returns.since_buy_unavailable | — | Purchase dates are not available for your holdings, so a same-period comparison with the Nifty 50 is not shown. |
| tio.assumption.lump_sum | instrumentName TEXT, amountInr INR | This shows your portfolio with a one-time {amountInr} added to {instrumentName} at today's price. |
| tio.assumption.sip | instrumentName TEXT, amountInr INR, months COUNT, totalInr INR | This shows your portfolio with {amountInr} a month added to {instrumentName} for {months\|month\|months} ({totalInr} in all), assuming prices stay where they are today. |
| tio.largest_company | beforeName TEXT, beforePct PCT, afterName TEXT, afterPct PCT | Largest company exposure: {beforeName} at {beforePct} before, {afterName} at {afterPct} after. |
| tio.top_sector | beforeName TEXT, beforePct PCT, afterName TEXT, afterPct PCT | Largest sector: {beforeName} at {beforePct} before, {afterName} at {afterPct} after. |
| tio.size_mix | bandName TEXT, beforePct PCT, afterPct PCT | {bandName} share: {beforePct} before, {afterPct} after. |
| tio.holdings_count | beforeCount COUNT, afterCount COUNT | Number of holdings: {beforeCount} before, {afterCount} after. |
| tio.holdings_count_same | count COUNT | Number of holdings stays at {count}, because you already hold it. |
| tio.overlap_fund | instrumentName TEXT, fundName TEXT, overlapPct PCT | {instrumentName} overlaps most with {fundName}, at {overlapPct}. |
| tio.overlap_stock | instrumentName TEXT, fundsHoldingCount COUNT, beforePct PCT, afterPct PCT | {instrumentName} is already inside {fundsHoldingCount\|fund\|funds} you hold; your total exposure to it goes from {beforePct} to {afterPct}. |
| tio.overlap_none_fund | instrumentName TEXT | {instrumentName} has no companies in common with the funds you hold. |
| tio.overlap_none_stock | instrumentName TEXT, beforePct PCT, afterPct PCT | {instrumentName} is not inside any fund you hold; your exposure to it goes from {beforePct} to {afterPct}. |
| tio.cost | beforeInr INR, afterInr INR | Yearly fund fees: {beforeInr} before, {afterInr} after. |
| tio.cost_stock | beforeInr INR | Adding a stock adds no yearly fund fee; it stays at {beforeInr}. |

**Choice rules (Java):**
- `windowLabel` = "1 year".
- tio.size_mix uses the band with the largest absolute change; `bandName` is "Large cap", "Mid cap", "Small cap", "Micro cap", "Debt & cash" or "Other / undisclosed".
- pf.exposure.other is only sent when OTHER > 0.
- Portfolio `sentences` arrays use:
  - exposure.company: [pf.exposure.company]
  - exposure.sector: [pf.exposure.sector]
  - exposure.size: [pf.exposure.size, (pf.exposure.other)]
  - concentration: [pf.concentration]
  - overlap: [pf.fact.overlap | pf.fact.overlap_none]
  - costs: [pf.fact.cost | cost_direct_only | cost_none]
  - mix: [pf.mix.equity_debt, pf.mix.stocks_funds]
  - Home/portfolio `facts`: overlap, cost, idle_cash variants.
- Java sends all of a page's items in one narrate call.

---
## §C Config file `config/app-config.yaml` (example committed as `config/app-config.example.yaml`; real file git-ignored)

**Loading:**
- Path comes from env `APP_CONFIG`, default `../config/app-config.yaml` relative to the service's working directory. A missing file means defaults.
- Defaults are exactly the example file below. Python embeds them as `config.DEFAULTS` (a test asserts equality with the example file); Java mirrors them in `application.yml`.
- The user file is deep-merged over the defaults.
- Java uses `spring.config.import: optional:file:${APP_CONFIG:../config/app-config.yaml}` and binds with `@ConfigurationProperties`. Env overrides use Spring relaxed binding (e.g. `SERVICES_PYTHONBASEURL`).
- Python additionally honours env `HOST` (bind address, default 127.0.0.1).

```yaml
# Stock & fund checker — configuration. Copy to config/app-config.yaml (git-ignored). All values optional.
app:
  sampleAsOf: "2026-10-30"            # "today" used whenever any adapter is mock; live-only mode uses the real date (Asia/Kolkata)
  defaultIllustrativeAmountInr: 100000 # amount used for fund cost when the user does not hold the fund
  disclaimer: "Information only, not investment advice."
ports:
  frontend: 5173
  java: 8080
  python: 8000
services:
  pythonBaseUrl: "http://localhost:8000"     # Java -> Python
  frontendBaseUrl: "http://localhost:5173"   # Java redirects here after Kite login; CORS allowed origin
adapters:
  broker: mock            # mock | kite_mcp | kite_connect
  fundamentals: mock      # mock | screener
  prices: mock            # mock | broker_then_nse_eod | nse_eod
  surveillance: mock      # mock | nse
  fundNav: mock           # mock | mfapi
  fundMeta: mock          # mock | amfi
  fundHoldings: mock      # mock | mfdata
  statement: auto         # auto (casparser if installed, else fallback) | casparser | fallback
kite:
  mcpUrl: "https://mcp.kite.trade/mcp"
  apiKey: ""              # kite_connect only
  apiSecret: ""           # kite_connect only; never commit
  redirectUrl: "http://localhost:8080/api/connect/kite/callback"  # must match the Kite developer console
  loginTimeoutSeconds: 300
screener:
  baseUrl: "https://www.screener.in"
  sessionCookie: ""       # optional; never commit
  minIntervalSeconds: 3
nse:
  baseUrl: "https://www.nseindia.com"
  asmCsvUrl: "https://nsearchives.nseindia.com/content/equities/asm_lt.csv"
  gsmCsvUrl: "https://nsearchives.nseindia.com/content/equities/gsm.csv"
  esmCsvUrl: "https://nsearchives.nseindia.com/content/equities/esm.csv"
  minIntervalSeconds: 2
mfapi:
  baseUrl: "https://api.mfapi.in"
amfi:
  navAllUrl: "https://www.amfiindia.com/spages/NAVAll.txt"
mfdata:
  baseUrl: "https://mfdata.in/api/v1"
llm:
  provider: none          # none | anthropic | openai
  model: ""
  apiKey: ""              # never commit
  timeoutSeconds: 20
cache:
  dir: ".cache"           # Python disk cache, relative to backend-python
  fundamentalsHours: 24
  pricesHours: 12
  fundDataHours: 24
  surveillanceHours: 24
  javaResponseMinutes: 30
storage:
  h2Path: "./data/stockanalyzer"   # Java H2 file (without .mv.db), relative to backend-java
sizeBands:                # live mode only; mock uses the stored band. Approximate cut-offs by market value, in crore
  largeMinCrore: 100000
  midMinCrore: 33000
  smallMinCrore: 6000
```

---
## §D Bundled sample data — `backend-python/app/data/sample/`

Generated by `backend-python/scripts/generate_sample_data.py` (stdlib only, seed 20261030). All files are committed. Encoding UTF-8; JSON is pretty-printed with fixed key order; CSV has a header row and `\n` line endings.

| File | Content |
|---|---|
| `manifest.json` | `{ "asOf": "2026-10-30", "seed": 20261030, "generator": "scripts/generate_sample_data.py", "generatorVersion": 1, "note": "Illustrative sample data, not real figures." }` |
| `stocks.json` | array of StockRecord (15) |
| `universe.json` | array `{ "symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Financial Services", "sizeBand": "LARGE" }` (~80, fund constituents only) |
| `prices/stocks/{SYMBOL}.csv` | `date,close,volume` — business days 2021-11-01..2026-10-30; close 2 dp; volume integer |
| `prices/indices/{INDEX_ID}.csv` | `date,close` — business days 2016-10-31..2026-10-30; 2 dp |
| `indices.json` | array `{ "id": "NIFTY50", "name": "Nifty 50", "kind": "PRICE" }` (kind PRICE\|TRI) |
| `funds.json` | array of FundRecord (9) |
| `navs/{schemeCode}.csv` | `date,nav` — business days from max(launchDate, 2016-10-31) to 2026-10-30; 4 dp |
| `fund_categories.json` | object keyed by category name → CategoryRecord |
| `sample_user.json` | SampleUser |
| `surveillance/asm.csv`, `gsm.csv`, `esm.csv` | `symbol,name,stage,since` (e.g. `SHIVAGRO,Shivalik Agro Polymers Ltd,Long-term ASM Stage II,2026-08-14`) |
| `sample_cas.pdf` | made by `scripts/make_sample_cas_pdf.py` (unencrypted; tests encrypt with password `SAMPLE1234`) |

**StockRecord**
```json
{
  "symbol": "TCS", "name": "Tata Consultancy Services Ltd", "isin": "INESMP000002", "exchange": "NSE", "fictional": false,
  "sector": "Information Technology", "industry": "IT Services", "sizeBand": "LARGE", "marketCapRank": 2, "isFinancial": false,
  "sharesOutstanding": 3618087518, "lastPrice": 3925.4,
  "about": "builds and runs software and technology systems for large companies around the world.",
  "revenueSegments": [ { "name": "Banking and financial services", "sharePct": 31.5, "prevSharePct": 32.1 } ],
  "peerGroup": { "name": "IT services", "members": [ { "name": "Infosys Ltd", "symbol": "INFY" }, { "name": "HCL Technologies Ltd", "symbol": "HCLTECH" } ],
    "medians": { "pe": 25.1, "pb": 7.2, "roePct": 27.9, "operatingMarginPct": 22.4, "revenueCagr3yPct": 8.6, "profitCagr3yPct": 7.9, "debtToEquity": 0.08, "interestCoverage": 38.5, "debtToProfit": 0.4, "dividendYieldPct": 2.1, "avgDailyTradedValueInr": 6200000000 } },
  "annual": [ { "fy": "FY2026", "periodStart": "2025-04-01", "periodEnd": "2026-03-31", "revenueInr": 2553000000000, "operatingProfitInr": 664000000000, "netProfitInr": 487000000000, "totalDebtInr": 81000000000, "cashInr": 420000000000, "netWorthInr": 945000000000, "interestInr": 8100000000, "eps": 134.6 } ],
  "quarterly": [ { "label": "July–September 2026", "periodEnd": "2026-09-30", "resultsDate": "2026-10-09", "revenueInr": 664000000000, "netProfitInr": 125000000000 } ],
  "shareholding": [ { "quarterEnd": "2026-09-30", "promoterPct": 71.77, "pledgedPctOfPromoter": 0.0, "fiiPct": 11.9, "diiPct": 11.2, "publicPct": 5.13 } ],
  "valuationHistory": [ { "monthEnd": "2026-09-30", "pe": 29.1, "pb": 14.6 } ],
  "dividendYieldPct": 1.9,
  "events": [ { "date": "2026-10-09", "type": "RESULTS", "text": "Results for July–September 2026 announced." } ]
}
```
- `annual` has 5 rows (FY2022..FY2026), `quarterly` 8 rows (latest first), `shareholding` 5 rows (2025-09-30..2026-09-30, latest first), `valuationHistory` 60 month-ends (oldest first).
- `about` follows the company name in a sentence. Peer members may be outside the sample set.
- Event `type` ∈ RESULTS|DIVIDEND|BUYBACK_ANNOUNCED|MANAGEMENT_CHANGE|ORDER_WIN|OTHER.

**FundRecord**
```json
{
  "schemeCode": "900101", "isin": "INFSMP900101", "name": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "shortName": "Kaveri Flexi Cap (Regular)",
  "amc": "Kaveri Mutual Fund", "category": "Flexi Cap Fund", "categoryGroup": "EQUITY", "planType": "REGULAR", "twinSchemeCode": "900102",
  "launchDate": "2013-01-01", "aumInr": 182400000000, "aumInr1yAgo": 159800000000, "terPct": 1.72, "terAsOf": "2026-09-30",
  "exitLoad": { "text": "1% if you take money out within 365 days", "pct": 1.0, "days": 365 }, "lockInYears": 0,
  "benchmarkId": "NIFTY500_TRI", "managers": [ { "name": "Ananya Rao", "since": "2019-04-01" } ],
  "assetMix": { "equityPct": 96.5, "debtPct": 0.0, "cashPct": 3.5, "otherPct": 0.0 }, "portfolioDate": "2026-09-30",
  "holdings": [ { "symbol": "HDFCBANK", "isin": null, "name": "HDFC Bank Ltd", "sector": "Financial Services", "sizeBand": "LARGE", "weightPct": 8.12 } ],
  "previousTop10": [ { "symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "weightPct": 8.31 } ],
  "events": [ { "date": "2026-07-01", "type": "MANAGER_CHANGE", "text": "Ananya Rao joined as co-manager." } ]
}
```
- `exitLoad` has text "None", pct 0 and days 0 when there is none.
- Fund event `type` ∈ MANAGER_CHANGE|BENCHMARK_CHANGE|TER_CHANGE|MERGER|OTHER.
- `holdings` may be empty (debt fund). Twins share identical `holdings`, `assetMix`, `portfolioDate`, `managers`, `benchmarkId`, `launchDate` and AUM.

**CategoryRecord** (key = category name)
```json
{ "group": "EQUITY", "mayHold": "Shares of companies of any size, at least 65% of the money; the rest can be in debt and cash.", "minEquityPct": 65,
  "medians": { "terPctDirect": 0.72, "terPctRegular": 1.61, "ageYears": 11.5, "aumInr": 95000000000, "top10SharePct": 46.2, "holdingsCount": 58, "managerTenureYears": 5.1 },
  "averageReturns": { "3Y": 15.8, "5Y": 17.2, "10Y": 13.9 }, "averageWorstFallPct": -32.5, "averageYearsTrailed": 2.2 }
```
`minEquityPct` is a number or null (debt).

**SampleUser**
```json
{ "accountLabel": "Your Zerodha account (sample)", "idleCashInr": 42350.75,
  "stocks": [ { "symbol": "TCS", "quantity": 15, "avgPrice": 3410.0, "firstBuyDate": "2023-06-05" } ],
  "funds": [ { "schemeCode": "900101", "units": 1850.234, "avgNav": 62.4, "firstBuyDate": "2021-12-01" } ] }
```
Exactly 6 stocks and 4 funds (see PLAN §4).
