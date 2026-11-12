# PLAN — Stock & fund checker prototype (beginner investor, India)

Source of truth: `docs/brief.md`. Contracts: `docs/api-contract.md` (every field, every endpoint).
This plan covers module boundaries, file trees, data models, sample data, build order, tests and how each part is verified.
Three agents build in parallel: **PY** (backend-python), **JV** (backend-java), **FE** (frontend).
None of them may add fields or endpoints that are not in the contract. If something is missing, write it to `QUESTIONS.md` and pick the most conservative reading.

## 0. Fixed facts

| Item | Value |
|---|---|
| Sample "today" (mock as-of) | `2026-10-30` (Friday). Live mode: today's date in Asia/Kolkata |
| Generator seed | `20261030` |
| Ports | frontend 5173, java 8080, python 8000 |
| Config | `APP_CONFIG` env var, default `../config/app-config.yaml` (relative to each service's working dir). Missing file → built-in defaults, which equal `config/app-config.example.yaml` (all mock) |
| JSON | camelCase keys; null fields present (never omitted); dates `YYYY-MM-DD`; timestamps ISO-8601 with offset |
| Percent values | percent units (`12.34` = 12.34%) |
| Rupee values | rupees as JSON numbers. Amounts are rounded to whole rupees in Java outputs; prices/NAV keep 2–4 dp |
| Ids | stock = NSE symbol (upper case); fund = AMFI scheme code (string); index = `NIFTY50` etc. |
| Single user | no auth; one implicit user row in Java |

## 1. Module boundaries

```
Browser ──/api/*──▶ backend-java (Spring Boot) ──/internal/*──▶ backend-python (FastAPI)
                     owns: H2 user data, ALL portfolio maths,           owns: adapters (broker, fundamentals,
                     orchestration, response cache, Kite callback       prices, surveillance, fund nav/meta/holdings,
                                                                        statement), stock/fund check engines, compare,
                                                                        search, glossary/explain, ALL sentence text
```
- **Java never writes user-facing English sentences**. It gets them from Python (`/internal/narrate`, or embedded in check payloads). The only text Java writes is error messages, plus labels copied from Python data (names, sector names).
- **Python never sees user holdings in full**. It receives instrument ids (for bundles and prices), already-computed portfolio facts (narrate), the user's overlap results and an amount (fund check).
- **The frontend contains no finance maths.** It formats display-ready strings it receives, and uses `lib/format.ts` only for user input echo, chart axes and tooltips.

## 2. Directory trees (file level)

### 2.1 Root (written by the integrating session after the agents finish; agents must not edit these files)
```
.gitignore              # config/app-config.yaml, **/target, **/node_modules, **/dist, **/.venv, **/__pycache__,
                        # backend-java/data/, backend-python/.cache/, *.mv.db, *.trace.db, .env
config/app-config.example.yaml   # verbatim from contract §C (PY agent writes this one file)
docker-compose.yml
run-dev.sh
Makefile
README.md               # what it is, quick start (mock), switching adapters live, config reference, Mermaid diagram,
                        # verified / not verified, known limits
DECISIONS.md  QUESTIONS.md  PLAN.md
docs/brief.md  docs/api-contract.md
```

### 2.2 backend-python (PY)
```
backend-python/
  requirements.txt            # fastapi, uvicorn[standard], pydantic>=2, PyYAML, requests, pdfplumber, pypdf, mcp
  requirements-optional.txt   # casparser
  Dockerfile                  # python:3.13-slim; CMD python -m app.serve
  pytest.ini                  # testpaths=tests
  app/
    __init__.py
    serve.py                  # entry: reads port from config; uses FastAPI app if importable, else asgi_fallback; uvicorn.run
    main.py                   # FastAPI only: builds app from routes.ROUTES; maps ApiError -> JSON error; nothing else
    asgi_fallback.py          # Starlette app from the same ROUTES (dev/verification here; no fastapi needed)
    routes.py                 # ROUTES: list[Route(method, path, handler, kind)]; kind in {query, json_body}
    handlers.py               # plain functions (params/body dict -> dict); the only place adapters meet engines
    context.py                # AppContext: config + adapter instances built from config (singleton, lazy)
    config.py                 # DEFAULTS dict (== example yaml), load(path) deep-merge, env APP_CONFIG
    errors.py                 # ApiError(status, code, message, details)
    models.py                 # pydantic v2 models for every contract shape (model_config extra="forbid")
    asof.py                   # today(): mock -> config app.sampleAsOf; live -> date in Asia/Kolkata
    formatting.py             # Indian formatting (contract §0.4); Decimal ROUND_HALF_UP on str(x)
    verdict_scan.py           # BANNED_RE, scan(text, allow_names=()) -> list[str]
    sources.py                # source label constants; label_for(adapter_mode, kind)
    adapters/
      __init__.py
      base.py                 # Protocols + dataclasses: BrokerAdapter, FundamentalsAdapter, PriceAdapter,
                              # SurveillanceAdapter, FundNavAdapter, FundMetaAdapter, FundHoldingsAdapter, StatementParser
      sample_store.py         # loads app/data/sample/* once (lru_cache); typed accessors
      http_util.py            # requests.Session factory, RateLimiter(min_interval), DiskCache(dir, ttl_hours)
      broker_guard.py         # MCP_ALLOWED_TOOLS, KITE_CONNECT_ALLOWED (method, path-regex); assert_allowed_*()
      broker_mock.py          # instant connect; portfolio from sample_user.json + sample prices
      broker_kite_mcp.py      # MCP client in a dedicated thread with its own anyio loop; guard before every call_tool
      broker_kite_connect.py  # REST via requests; login URL, session/token exchange (sha256 checksum); guard on every call
      fundamentals_mock.py
      fundamentals_screener.py   # fetch+parse public company page; 24h DiskCache; RateLimiter; optional cookie
      screener_parse.py          # html.parser-based table extraction (pure; unit-tested on fixture HTML)
      prices_mock.py
      prices_broker.py        # get_historical_data / historical candles via active broker adapter
      prices_nse_eod.py       # NSE historical JSON with cookie warm-up; yearly chunks; cache
      prices_chain.py         # broker_then_nse_eod composition
      surveillance_mock.py  surveillance_nse.py
      fund_nav_mock.py  fund_nav_mfapi.py
      fund_meta_mock.py  fund_meta_amfi.py      # amfi: NAVAll.txt (code, isin, name, category headers); other fields from
                                                # bundled starter meta when the scheme is known; else null + "not available"
      fund_holdings_mock.py  fund_holdings_mfdata.py   # mfdata: base URL in config; falls back to bundled starter set
      statement_casparser.py  # optional import casparser; raises ImportError -> factory picks fallback
      statement_fallback.py   # pypdf decrypt(password) -> pdfplumber text -> cas_text_parser
      cas_text_parser.py      # pure regex parser over text lines (CAMS + KFintech layouts)
      isin_map.py             # ISIN -> schemeCode via fund meta adapter
    engines/
      __init__.py
      series.py               # on_or_before(series, date), pct_change, cagr, max_drawdown(series)->(peak,trough,recovery),
                              # weekly_resample, rebase, calendar_year_returns, avg_daily_traded_value
      peers.py                # peer/category median helpers
      stock_answers.py        # 5 answer builders (ids fixed, order fixed)
      stock_facts.py          # 8 fact builders (ids fixed, order fixed)
      stock_check.py          # assembles StockCheck (instrument, answers, facts, priceHistory, drawdown, peers)
      fund_answers.py  fund_facts.py  fund_check.py
      compare.py              # rows of answers across 2–3 instruments
      search.py               # prefix/substring over symbols, names, scheme names; max 10
      instruments.py          # bundle for Java (stock meta, fund meta + holdings + mix + TER + twin)
      price_points.py         # /internal/prices/points
      figures.py              # make_figure(id, label, value, unit, source, as_of, comparisons, term_id)
    narrative/
      __init__.py
      templates.py            # TEMPLATES: id -> (text, {key: unit}) for pf.*, tio.* (contract §B.12) and stk.*, fnd.*
      render.py               # render(template_id, facts) -> Sentence; placeholder {key} / {key|one|many}; scan
      narrate.py              # handler logic for /internal/narrate; LLM path + fallback
      llm.py                  # providers: none | anthropic | openai via requests; prompt contains only computed facts
    content/
      glossary.json           # >= 40 terms (contract §B.9 ids)
      glossary.py             # list_terms(), explain(term, kind, id, ctx)
      categories.json         # SEBI category -> plain-words "may hold" text + minimum equity share
    data/sample/              # generated; committed (see §4)
  scripts/
    generate_sample_data.py   # stdlib only; deterministic
    make_sample_cas_pdf.py    # stdlib only: writes unencrypted data/sample/sample_cas.pdf (text PDF)
    smoke_internal.py         # starts asgi_fallback via uvicorn on a free port; hits every /internal route with requests
    dump_contract_fixtures.py # writes tests/fixtures/contract/*.json from handlers in mock mode
  tests/
    conftest.py               # ctx fixture: mock config, sampleAsOf
    fixtures/screener_tcs.html  fixtures/cas_cams.txt  fixtures/cas_kfintech.txt  fixtures/contract/*.json
    test_formatting.py  test_verdict_scan.py  test_sample_data.py  test_series.py
    test_stock_facts.py  test_stock_answers.py  test_fund_facts.py  test_fund_answers.py
    test_overlap_inputs.py  test_compare_search.py  test_glossary.py  test_narrate.py
    test_broker_guard.py  test_broker_mock.py  test_statement_parser.py  test_screener_parse.py
    test_config.py  test_handlers_contract.py  test_routes.py
```

### 2.3 backend-java (JV)
Package root `com.stockanalyzer`. No Lombok. Spring Boot 3.3.x parent, Java 21.
```
backend-java/
  pom.xml                     # spring-boot-starter-web, -data-jpa, -validation, h2 (runtime), -test; surefire
  Dockerfile                  # maven:3.9-eclipse-temurin-21 build -> eclipse-temurin:21-jre run
  tools/junit-shim/org/junit/jupiter/api/{Test.java,DisplayName.java,Assertions.java}  # LOCAL VERIFICATION ONLY
  tools/EngineTestRunner.java # reflection runner: runs @Test methods of given classes, prints pass/fail, exit code
  tools/engine-check.sh       # javac engine + shim + engine tests -> out/; java EngineTestRunner <classes>
  src/main/resources/application.yml   # spring.config.import: optional:file:${APP_CONFIG:../config/app-config.yaml}
                                       # + defaults mirroring example yaml; spring.datasource h2 file ${storage.h2Path}
  src/main/java/com/stockanalyzer/
    StockAnalyzerApplication.java
    engine/                   # PURE JAVA — imports java.* only. No Spring, Jackson, JPA.
      model/ Kind.java (STOCK, FUND) SizeBand.java (LARGE, MID, SMALL, MICRO)
             StockInfo.java        record(symbol, name, sector, sizeBand, lastPrice, checkAvailable)
             FundConstituent.java  record(key, symbol, name, sector, sizeBand, weightPct, checkAvailable)
             AssetMix.java         record(equityPct, debtPct, cashPct, otherPct)
             FundInfo.java         record(schemeCode, name, category, planType, terPct, twinSchemeCode, twinTerPct,
                                          nav, assetMix, constituents)
             Position.java         record(kind, id, quantity, avgPrice, firstBuyDate /*LocalDate|null*/)
             PortfolioInput.java   record(positions, stocks Map, funds Map, idleCashInr, asOf)
      Bp.java                 # basis-point helpers; largestRemainder(long[] rawScaled, long target)
      Money.java              # roundRupees(double) HALF_UP via BigDecimal.valueOf
      ExposureEngine.java     # company/sector/size breakdowns with direct vs through-funds split
      ExposureLine.java  ExposureBreakdown.java
      OverlapEngine.java      # overlap(FundInfo a, FundInfo b) -> OverlapResult(pct, commonCount, topCommon)
      CostEngine.java         # per-fund yearly cost, regular-vs-direct gap
      MixEngine.java          # equity/debt/other and stocks/funds
      ConcentrationEngine.java
      ReturnsEngine.java      # 1Y, since-buy, Nifty same-dates; needs PricePoints lookup interface
      PricePoints.java        # interface: OptionalDouble value(kind, id, LocalDate requested)
      TryItOnEngine.java      # before/after metrics; SIP = months × amount at today's price
      PortfolioEngine.java    # facade: compute(PortfolioInput, PricePoints) -> PortfolioResult
      PortfolioResult.java    # all numbers needed for /api/portfolio, /api/home
      NarrationPlan.java      # builds List<NarrateItem(key, templateId, Map<String, FactValue>)> from results
      FactValue.java          # record(Object value, String unit)
      IndianFormat.java       # contract §0.4 (same vectors as PY/FE)
    config/ AppProperties.java (@ConfigurationProperties, records) WebConfig.java (CORS frontendBaseUrl)
            HttpClientConfig.java (RestClient to services.pythonBaseUrl, timeouts 10s; 60s for broker/statement)
    python/ PythonClient.java  # typed calls for bundle, prices/points, narrate, broker/*, statements/parse;
                               # JsonNode pass-through for checks/compare/search/glossary/explain/health
            dto/*.java         # records mirroring contract §B.5, B.6, B.7, B.10, B.11
    domain/ HoldingEntity.java WatchlistItemEntity.java ImportLogEntity.java AccountCashEntity.java
            CachedResponseEntity.java + *Repository.java (Spring Data JPA)
    service/ PortfolioService.java   # holdings -> bundle + points -> engine -> narrate -> view DTOs
             HomeService.java CheckService.java (adds `user` block; computes overlaps for fund check)
             TryItOnService.java WatchlistService.java ConnectService.java ImportService.java
             HoldingsService.java ResponseCache.java MetaService.java
    web/    HomeController PortfolioController CheckController (stocks, funds, compare, search, glossary, explain)
            TryItOnController WatchlistController ConnectController ImportController HoldingsController MetaController
            ApiExceptionHandler.java  dto/*.java (public response records, contract §A)
  src/test/java/com/stockanalyzer/engine/
    ExposureEngineTest OverlapEngineTest CostEngineTest MixEngineTest ConcentrationEngineTest ReturnsEngineTest
    TryItOnEngineTest BpTest IndianFormatTest NarrationPlanTest  EngineFixtures.java (hand-built inputs)
  src/test/java/com/stockanalyzer/web/ PortfolioControllerTest.java ConnectControllerTest.java  # Spring; not runnable here
```
Engine tests may use only `@Test`, `@DisplayName`, `Assertions.{assertEquals(long,long), assertEquals(double,double,double), assertEquals(Object,Object), assertTrue, assertFalse, assertNull, assertNotNull, assertThrows}`. This keeps them runnable with the shim.

### 2.4 frontend (FE)
```
frontend/
  package.json         # react, react-dom, react-router-dom@6, recharts; dev: vite, @vitejs/plugin-react, typescript,
                       # tailwindcss@3, postcss, autoprefixer, tsx. scripts: dev, build, preview, test (tsx --test src/lib/*.test.ts),
                       # typecheck:lib (tsc -p tsconfig.lib.json)
  vite.config.ts       # server/preview proxy '/api' -> process.env.VITE_API_TARGET ?? 'http://localhost:8080'
  tsconfig.json  tsconfig.lib.json (strict; include src/lib/**/*.ts excluding *.test.ts; lib es2022+dom; noEmit)
  tailwind.config.js  postcss.config.js  index.html  Dockerfile (node:22 -> npm ci, build, preview --host)
  src/
    main.tsx  App.tsx (BrowserRouter + routes)  index.css (tailwind layers; neutral palette tokens)
    lib/                      # DEPENDENCY-FREE (no react, no imports outside lib); checked by global tsc here
      api-types.ts            # every contract type (§0 shared shapes, §A responses/requests)
      api-client.ts           # fetch wrapper: get/post/patch/del, ApiError parsing; endpoint functions per §A
      format.ts               # formatInr, formatPrice, formatPct, formatPctChange, formatTimes, formatCount,
                              # formatYears, formatDays (contract §0.4 vectors)
      dates.ts                # formatDate('2026-10-30') -> '30 Oct 2026', formatTimestamp
      routes.ts               # path builders: stockPath(sym), fundPath(code), comparePath(kind, ids), tryPath(kind,id)
      verdict.ts              # BANNED_RE (identical to contract §0.6) + scan()
      copy.ts                 # ALL static UI strings (labels, empty states, errors, footer disclaimer)
      format.test.ts dates.test.ts verdict.test.ts (scans every string in copy.ts) contract-fixtures.check.ts
    hooks/ useApi.ts (data/loading/error/reload)  useDebounce.ts
    components/ui/            # own component library
      AppShell.tsx (header: logo, GlobalSearch, nav, SampleDataBadge) Footer.tsx (disclaimer) Button.tsx Card.tsx
      Badge.tsx SampleDataBadge.tsx Skeleton.tsx EmptyState.tsx ErrorState.tsx ShowDetails.tsx (disclosure toggle)
      DataTable.tsx (renders DetailTable) SentenceList.tsx FigureChip.tsx (value, comparison, source · as-of)
      AnswerCard.tsx FactCard.tsx ExplainPopover.tsx (button "Explain this", keyboard: Enter/Esc, focus trap)
      GlobalSearch.tsx (combobox, arrow keys) SegmentedControl.tsx Input.tsx MoneyInput.tsx TextArea.tsx
      Drawer.tsx (Try-it-on panel) PageHeader.tsx Tabs.tsx
    components/charts/ PriceChart.tsx (Recharts LineChart, instrument + rebased benchmark)
      ExposureBars.tsx (stacked horizontal: direct / through funds) MixBar.tsx BeforeAfter.tsx
    pages/ HomePage ConnectPage PortfolioPage StockCheckPage FundCheckPage ComparePage WatchlistPage
           TryItOnPage (also rendered inside Drawer on check pages) NotFoundPage
```
Colours are neutral only: slate/stone greys plus one accent (indigo-700) for focus and links. Charts use slate-700 for the instrument and slate-400 dashed for the benchmark. There is no red or green anywhere, and signs carry direction. Text contrast is at least 4.5:1.

## 3. Data models

### 3.1 Java H2 (JPA entities; `spring.jpa.hibernate.ddl-auto=update`)
| Entity / table | Fields |
|---|---|
| `HoldingEntity` / `holding` | id (long PK), kind (STOCK/FUND), instrumentId, name, quantity (double; units for funds), avgPrice (double), firstBuyDate (LocalDate null), source (KITE/STATEMENT/MANUAL), sampleData (bool), importedAt (OffsetDateTime) |
| `AccountCashEntity` / `account_cash` | id=1, idleCashInr (double), asOf (LocalDate), source (KITE), sampleData |
| `WatchlistItemEntity` / `watchlist_item` | id, kind, instrumentId (unique with kind), name, subtitle, note (≤ 1000 chars), createdAt, updatedAt |
| `ImportLogEntity` / `import_log` | id, source, status (SUCCESS/PARTIAL/FAILED), startedAt, finishedAt, stockCount, fundCount, unmatchedCount, message, sampleData |
| `CachedResponseEntity` / `cached_response` | cacheKey (PK, ≤ 512), json (CLOB), expiresAt |

Import semantics: a KITE import deletes the KITE rows and the cash row, then inserts new ones. A STATEMENT import deletes and reinserts STATEMENT rows. MANUAL rows are never touched by an import. The engine aggregates positions by (kind, instrumentId): it sums quantity, takes a quantity-weighted avgPrice and keeps the earliest non-null firstBuyDate.

Cache keys and TTL (`cache.javaResponseMinutes`):
- `stock-check:{SYM}`, `compare:{kind}:{ids}:{amount}`, `search:{q}`, `glossary`, `explain:{term}:{kind}:{id}`, `bundle:{sorted ids}`, `points:{hash}`.
- Fund check: `fund-check:{code}:{amount}:{hash(user fund ids)}`.
- Portfolio, home and try-it-on are not cached; their Python sub-calls are.
- All cache rows are cleared on any import or holdings change.

### 3.2 Engine maths (Java, pure)
- **Position value:** stock = quantity × lastPrice. Fund = units × nav. Portfolio value V = Σ position values. Idle cash is excluded from V and reported separately, along with `totalWithCash`.
- **Look-through:** a stock position s adds value_s to company key `symbol` (direct). A fund position f with value_f adds, for each constituent c, value_f × w_c/100 to key c.key (through funds). DEBT_CASH gets value_f × (debtPct + cashPct)/100. OTHER gets value_f × (100 − Σw_c − debtPct − cashPct)/100. If the bracket is negative (disclosed weights overshoot), constituents are scaled so that Σw_c = equityPct + otherPct and OTHER = 0. Company key = `symbol` ?? `isin` ?? `"NAME:" + upper(trimmed name)`.
- **Sector breakdown** = the same allocations grouped by sector. **Size breakdown** is grouped by sizeBand; a constituent with null sizeBand goes to OTHER. Bucket keys are `DEBT_CASH` and `OTHER`.
- **Rounding:**
  - Each line's raw value is converted to basis points: raw_bp = value/V × 10000. Largest-remainder rounding to integers makes Σ = 10000 exactly. Ties are broken by larger value, then by key ascending.
  - Rupees: each line's total is rounded with largest remainder at whole rupees so that Σ = round(V).
  - directBp is rounded HALF_UP from raw, then capped to [0, totalBp]; throughFundsBp = totalBp − directBp. Rupee direct/through are split the same way.
  - JSON pct = bp/100.0.
- **Concentration:** largest company bp; top-5 companies bp sum; top sector bp; distinct company count (excluding buckets); holding count = distinct positions.
- **Overlap(A, B)** = Σ over keys present in both of min(wA, wB), using constituent weightPct (percent of fund). The result is rounded HALF_UP to 2 dp; commonCount and topCommon (top 5 by min weight) are also returned. Pairs cover every unordered pair of distinct held funds, sorted by overlap descending. A regular/direct twin pair returns about the full disclosed equity, which is correct.
- **Cost:** yearlyCost_f = value_f × terPct/100. regularGap_f = value_f × (terPct − twinTerPct)/100, only for planType REGULAR with a twin. Totals are summed and rounded to rupees at the end.
- **Mix:**
  - Equity = Σ stocks + Σ value_f × equityPct/100.
  - Debt & cash = Σ value_f × (debtPct + cashPct)/100.
  - Other = Σ value_f × otherPct/100.
  - Stocks/funds = Σ stock values vs Σ fund values.
  - Each mix is rounded with largest remainder to 10000 bp.
- **Returns:**
  - Price/NAV return excludes dividends; the benchmark is the NIFTY50 price index.
  - 1Y for a holding: p(asOf)/p(asOf − 1 year, on-or-before) − 1.
  - Portfolio 1Y = Σ value_i / Σ (value_i/(1 + r_i)) − 1 over holdings that have 1Y history ("today's holdings, held for the full year"). It is compared with the Nifty 1Y on the same dates.
  - Since-buy (only where firstBuyDate is known): gain = value/(qty × avgPrice) − 1. The Nifty same-dates figure for one holding = nifty(asOf)/nifty(firstBuyDate) − 1. For the portfolio, invest each holding's cost in Nifty on its buy date: niftyValue = Σ cost_i × nifty(asOf)/nifty(buy_i), compared with Σ value_i.
  - All results are rounded to 2 dp HALF_UP.
- **Try-it-on:**
  - LUMP_SUM adds `amountInr` to the candidate. SIP adds `amountInr × months` (default 12, allowed 1–60), all at today's price/NAV. This assumes no price change and that the money is new money, not taken from other holdings.
  - If the candidate is already held, it increases that position.
  - The before snapshot is computed with exactly the same code path as /api/portfolio. The after snapshot reruns the engine on positions plus the candidate.
  - Metrics: largest company, top sector, size mix (six buckets), holdings count, overlap (fund candidate: overlap with each held fund other than itself; stock candidate: its weight inside each held fund, plus total exposure to it before and after), yearly fund cost.
- **Empty portfolio** (V = 0): breakdowns have empty lines, pcts are 0, and narration uses the `*_none` / `pf.summary.empty` templates.

### 3.3 Python domain (dataclasses in `adapters/base.py`)
- `StockFundamentals(symbol, name, isin, sector, industry, sizeBand, marketCapRank, isFinancial, sharesOutstanding, about, revenueSegments, peerGroup, annual[5], quarterly[8], shareholding[5], valuationHistory[60], dividendYieldPct, events, source, asOf)`
- `PriceSeries(id, points[(date, close, volume|None)], source, asOf)`
- `SurveillanceEntry(symbol, list ASM|GSM|ESM, stage, since)`
- `FundMeta(schemeCode, isin, name, shortName, amc, category, categoryGroup, planType, twinSchemeCode, launchDate, aumInr, aumInr1yAgo, terPct, terAsOf, exitLoad, lockInYears, benchmarkId, managers, source, asOf)`
- `FundPortfolio(schemeCode, portfolioDate, assetMix, holdings[], previousTop10[], events[], source)`
- `NavSeries`
- `BrokerPortfolio`, `ParsedStatement` (contract §B.10, §B.11)

## 4. Sample data design (PY owns; `scripts/generate_sample_data.py`, stdlib only)

**Determinism rules:**
- One master `random.Random(20261030)`. Each instrument gets a sub-RNG `random.Random(20261030 ^ zlib.crc32(id.encode()))`.
- Never iterate over sets, and never use `hash()`.
- Write JSON with `sort_keys=False`, a fixed field order, `indent=1`, `ensure_ascii=False` and a trailing newline. CSV uses `\n` line endings, prices with 2 dp and NAV with 4 dp.
- A test regenerates the data into `tmp_path` and asserts byte-equality with the committed files.

**Calendar and series:**
- Business days are Mon–Fri (no holiday calendar).
- Stocks: 2021-11-01 → 2026-10-30. Funds and indices: 2016-10-31 → 2026-10-30, or from the fund's launch date.
- Prices follow geometric Brownian motion with per-stock drift and volatility, plus one shared market shock (−18% over 2022-01-17 → 2022-06-17, then a recovery). The series is rescaled so the last close equals the configured `lastPrice`.
- Volume is lognormal around a per-stock mean that matches the size band.

**Stocks (15)** — real names, illustrative figures. `fictional: true` marks the two made-up companies.

| Symbol | Sector | Band | Non-trivial case covered |
|---|---|---|---|
| RELIANCE | Oil Gas & Consumable Fuels | LARGE | |
| TCS | Information Technology | LARGE | results on 2026-10-09 (inside 30-day window) |
| HDFCBANK | Financial Services | LARGE | isFinancial → debt fact not applicable |
| INFY | Information Technology | LARGE | |
| ITC | FMCG | LARGE | |
| LT | Construction & Engineering | LARGE | |
| SUNPHARMA | Healthcare | LARGE | |
| MARUTI | Automobile & Auto Components | LARGE | no results in last 30 days |
| ASIANPAINT | Consumer Durables | LARGE | promoter holding falling 4 quarters |
| TATASTEEL | Metals & Mining | LARGE | high debt-to-profit |
| BHARTIARTL | Telecommunication | LARGE | |
| VOLTAS | Consumer Durables | MID | |
| FEDERALBNK | Financial Services | MID | isFinancial |
| DECCANINF (Deccan Infra Projects Ltd, fictional) | Construction & Engineering | SMALL | promoter pledge 38.4% of promoter shares |
| SHIVAGRO (Shivalik Agro Polymers Ltd, fictional) | Chemicals | MICRO | ASM long-term stage II since 2026-08-14; loss in FY2025 |

Each stock has a `peerGroup` with a name, 3–5 member names (members in the sample set are marked `checkAvailable`) and precomputed medians.

**Universe:** about 80 further listed companies (symbol, name, sector, sizeBand) are used only as fund constituents.

**Funds (9)** — fictional fund houses; scheme codes 900xxx so they never collide with real AMFI codes; ISIN `INFSMP` + code.

| Code | Name (short) | Category | Plan | TER% | Notes |
|---|---|---|---|---|---|
| 900101 | Kaveri Flexi Cap (Regular) | Flexi Cap Fund | REGULAR | 1.72 | twin 900102; launched 2013 |
| 900102 | Kaveri Flexi Cap (Direct) | Flexi Cap Fund | DIRECT | 0.68 | twin 900101; same portfolio |
| 900201 | Narmada Nifty 50 Index | Index Fund | DIRECT | 0.18 | launched 2019-07-01 (10Y return not available); 50 Nifty-like weights |
| 900301 | Godavari Midcap | Mid Cap Fund | DIRECT | 0.74 | |
| 900401 | Tapti Small Cap | Small Cap Fund | DIRECT | 0.71 | exit load 1% within 365 days |
| 900501 | Krishna ELSS Tax Saver | ELSS | DIRECT | 0.82 | lock-in 3 years, no exit load |
| 900601 | Yamuna Aggressive Hybrid | Aggressive Hybrid Fund | DIRECT | 0.95 | equity 72 / debt 23 / cash 4 / other 1 |
| 900701 | Sindhu Large Cap | Large Cap Fund | DIRECT | 0.89 | manager change 2026-07-01 (recent) |
| 900801 | Ganga Short Duration | Short Duration Fund | DIRECT | 0.38 | debt 93 / cash 7; no equity constituents |

- Disclosed equity constituents sum to `equityPct − 0.8 .. 2.5` (seeded), so OTHER is never empty for equity funds.
- `previousTop10` (as of the previous month) differs by 1–2 names so "what changed recently" has content.

**Indices:** NIFTY50 (price), NIFTY50_TRI, NIFTY100_TRI, NIFTY500_TRI, NIFTY_MIDCAP150_TRI, NIFTY_SMALLCAP250_TRI, CRISIL_HYBRID_35_65, CRISIL_SHORT_DURATION_DEBT.

**fund_categories.json:** per category, the plain-words mandate, minimum equity %, medians (TER direct/regular, age, AUM, top10 share, holdings count, manager tenure), average returns for 3/5/10Y, average worst fall, and average years trailed.

**sample_user.json:**
- Stocks: RELIANCE 40 @ 2380.00, HDFCBANK 60 @ 1520.00, TCS 15 @ 3410.00, ITC 300 @ 395.00, TATASTEEL 500 @ 118.00, DECCANINF 400 @ 212.00.
- Funds: 900101 1850.234 @ 62.40, 900201 3120.500 @ 21.85, 900301 410.112 @ 98.30, 900501 980.000 @ 41.20.
- Each position has a firstBuyDate; idle cash is ₹42,350.75.

**Surveillance CSVs:** SHIVAGRO on ASM; two universe-only names on GSM/ESM. **sample_cas.pdf** comes from `make_sample_cas_pdf.py` and contains 900701, 900801 and one unmatched fund ("Example Gilt Fund"). The test encrypts it with pypdf using password `SAMPLE1234`.

File formats: contract §D.

## 5. Python check engines — sentence content rules (templates `stk.*`, `fnd.*` are PY-internal)

- Every answer has 2–3 sentences and every fact has 1–2 sentences. Order: sentence first, then figures, then source/as-of (on each figure). Rupee amounts come before ratios.
- Use neutral verbs only: "rose", "fell", "is above/below", "is higher/lower than", "changed from X to Y", "trailed", "matched".
- The banned list must never appear. Avoid the collisions listed in contract §0.6.
- Every numeric Figure carries ≥ 1 comparison (contract §0.3). The exempt cases are TEXT figures and `overlap_*` figures.
- When data is missing, set `available: false` (facts) or `value: null` with display "Not available" and explain why in the sentence. Never invent a figure.

## 6. Build order (all three agents start at once; dependencies are only on the contract)

**PY**
1. `formatting.py`, `verdict_scan.py`, `models.py`, `config.py` + tests.
2. Generator + sample data + `sample_store` + `test_sample_data`.
3. `series.py`, then the stock facts/answers, then the fund facts/answers (tests per fact).
4. instruments bundle, prices/points, search, compare, glossary/explain.
5. narrate + templates + LLM fallback.
6. Broker mock + guard, statement parser.
7. `handlers.py`, `routes.py`, `asgi_fallback.py`, `main.py`, smoke script, then the live adapters.
8. Dump contract fixtures.

**JV**
1. Engine model + Bp/Money/IndianFormat + tests (shim runner).
2. Exposure → overlap → cost/mix/concentration → returns → try-it-on → NarrationPlan, each with tests.
3. Entities/repos, PythonClient + DTOs, services, controllers, ApiExceptionHandler, application.yml, Dockerfile.

**FE**
1. `lib/` (types, format, dates, routes, verdict, copy) + node tests + tsc lib check.
2. ui components.
3. AppShell/Footer/search/Explain popover.
4. Pages in order: Stock check → Fund check → Portfolio → Home → Connect → Try-it-on → Compare → Watchlist.
5. Loading skeletons, empty states and error states on every page.

**Integrating session** (after the agents finish): root files, `make verify-local`, a cross-check of FE types and Java DTOs against PY fixtures, then README, DECISIONS and QUESTIONS.

## 7. Test list (the brief's quality bar maps to these files)

| Requirement | Test |
|---|---|
| Overlap formula | JV `OverlapEngineTest`: A{X:10,Y:5} B{X:4,Z:7} → 4.00; identical funds → Σw; disjoint → 0; symmetric; twin plans equal. PY `test_overlap_inputs`: constituent weights in (0,100], Σ ≤ equityPct, twins identical, index fund 50 names |
| Look-through sums to 100% | JV `ExposureEngineTest`: company/sector/size each Σbp == 10000 and Σ rupees == round(V) on the sample user, a debt-only portfolio, a stocks-only one, and one overshooting fund; direct + through == total per line; OTHER > 0 for the sample user |
| Try-it-on before/after | JV `TryItOnEngineTest`: before == PortfolioEngine result; lump sum new stock adds a holding; SIP = 12 × amount; adding to a held fund keeps the count; after sums to 10000; overlap list excludes self |
| 8 stock facts | PY `test_stock_facts`: one test per fact id on sample data (e.g. DECCANINF pledge 38.4; SHIVAGRO ASM + loss year; HDFCBANK fact 4 unavailable; TCS results within window, MARUTI none; size bands; ADTV positive with peer comparison) + order/ids fixed |
| 8 fund facts | PY `test_fund_facts`: 900101 regular gap > 0 vs 900102; ER vs category median; 900201 age < 10; years trailed ∈ 0..5 with per-year table; mandate text; top10 share; 900501 lock-in 3; overlap fact rendering from provided overlaps, and the empty case |
| Rupee formatting | PY `test_formatting`, JV `IndianFormatTest`, FE `format.test.ts`, all using the contract §0.4 vectors |
| Verdict-word scan | PY `test_verdict_scan`: regex cases; every template (pf/tio/stk/fnd), glossary entry, category text and stock `about`; full check output for all 15 stocks and 9 funds; compare; narrate on the sample user and try-it-on facts; explain for every term. FE `verdict.test.ts` over `copy.ts` |
| Also | `test_series` (CAGR, drawdown recovery, on-or-before), `test_narrate` (each template renders; missing key → 400; LLM fallback on a banned word or an unknown number via fake provider), `test_broker_guard` (allow-lists exact; `place_order`, `modify_order`, `cancel_order`, `place_gtt_order`, `modify_gtt_order`, `delete_gtt_order`, POST /orders/regular refused), `test_statement_parser` (text fixtures; encrypted PDF; wrong password → STATEMENT_PASSWORD_INVALID), `test_config` (DEFAULTS == example yaml), `test_handlers_contract` (every handler output validates against models with extra=forbid), `test_routes` (ROUTES == contract list) |

## 8. Verification strategy

**Runnable in this sandbox (`make verify-local`):**
1. `cd backend-python && python -m pytest -q`
2. `python scripts/smoke_internal.py`: runs a real HTTP server (Starlette fallback + uvicorn) and checks every internal route in mock mode, including the narrate and broker mock flows.
3. `backend-java/tools/engine-check.sh`: javac of `engine/**` + shim + engine tests, then the runner. Exit code 0 is required.
4. `cd frontend && tsc -p tsconfig.lib.json && tsx --test src/lib/*.test.ts`
5. Cross-language: `python scripts/dump_contract_fixtures.py`, then `tsc` on `src/lib/contract-fixtures.check.ts` (it assigns each fixture JSON to its TS type using `resolveJsonModule`).

**Not verifiable here (documented in README):**
- Spring layer compile/run, Vite build, Tailwind and Recharts rendering, docker-compose.
- All live adapters (Kite MCP/Connect, screener, NSE, mfapi, AMFI, MFData).
- casparser.

They are designed to be thin. A real-network checklist goes in the README.

## 9. Run & ops (integrating session)

- **`run-dev.sh`:** creates `.venv` if missing, then starts `python -m app.serve`, `mvn -q spring-boot:run` and `npm run dev`. It traps INT to kill all three and prints the URLs.
- **`Makefile`:** `setup`, `dev`, `test` (pytest + mvn test + npm test), `verify-local`, `sample-data`, `docker-up`, `docker-down`, `clean`.
- **`docker-compose.yml`:**
  - backend-python: env `APP_CONFIG=/config/app-config.yaml`, `HOST=0.0.0.0`.
  - backend-java: env `APP_CONFIG`, `SERVICES_PYTHONBASEURL=http://backend-python:8000`, `STORAGE_H2PATH=/data/stockanalyzer`; volume `h2data:/data`.
  - frontend: env `VITE_API_TARGET=http://backend-java:8080`; port 5173.
  - `./config` is mounted read-only at `/config` in the two backends.
  - In docker, set `services.frontendBaseUrl` and `kite.redirectUrl` to host URLs (the defaults already are).

## 10. Out of scope (prototype)

Auth, multiple users, Groww import, news/sentiment, alerts, mobile app, order placement (forbidden by the guard), tax calculations, and XIRR (a simple since-buy return is used instead and stated as such).
