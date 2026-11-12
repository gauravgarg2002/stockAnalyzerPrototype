# Product brief (source of truth for the prototype)

This is the brief the prototype was built from. On any conflict with other notes, this file wins.

## Product

A web app that helps a BEGINNER investor in India who is building a personal portfolio. Core loop:
(1) connect Zerodha Kite and import holdings, (2) see "what you really own" across stocks and mutual
funds in plain words, (3) check any stock or fund before adding it, (4) "try it on": enter an amount
or monthly SIP and see how the portfolio would change, (5) save to a watchlist with a note.

**Hard rule, informational only:** the app states facts and findings and NEVER gives buy/sell views,
scores, ratings, targets or verdict words. "Debt has doubled in three years while profit is flat" is
allowed; "avoid", "overvalued", "good", "bad", "strong buy" are not. Include an automated test that
scans all generated and template text for banned verdict words (buy, sell, avoid, overvalued,
undervalued, cheap, expensive as a judgement, good, bad, recommend, target price, should) and fails
if any appear in user-facing findings. Show a short "Information only, not investment advice" line in
the footer.

**Design principles:** one screen answers one question; sentence first, number second, source and
as-of date third; rupee amounts before ratios (Indian numbering: lakh, crore); the same fixed
checklist for every stock and for every fund, neutral colours (no red/green verdict colouring); no
number without a comparison (own history, peers or category); full tables behind a "Show details"
toggle.

### Screens (React, mobile-responsive, polished and friendly)

- **Home:** big search box "Check a stock or fund"; portfolio summary in three plain sentences; top
  five true exposures; three portfolio facts; watchlist.
- **Connect:** primary "Connect Zerodha Kite"; secondary "Have funds outside Zerodha? Add a
  statement" (upload a CAMS/KFintech consolidated account statement PDF with its password); manual
  add as a last option; shows what was imported and when.
- **My portfolio:** true company, sector and size exposure across direct stocks AND the companies
  inside the user's funds, each line split into "direct" and "through funds"; fund overlap pairs;
  yearly fund cost in rupees and the regular-vs-direct plan gap; equity/debt and stocks/funds mix;
  return of each holding and of the portfolio against Nifty 50; idle cash from the account; holdings
  list linking to check pages.
- **Stock check:** five questions, each answered in two or three plain sentences with the figures
  behind them: (1) what does the company do and how does it earn money, (2) is it growing and
  profitable, (3) is it financially safe, (4) how is it priced against its own history and its
  peers, (5) what changed recently. Then eight fixed facts: promoter holding level and four-quarter
  direction; promoter pledge; profit or loss in each of the last three years; debt against yearly
  earnings; price move in the last 30 days and whether results were announced in that period;
  average daily trading value; size band (large, mid, small, micro); whether it is on an NSE
  surveillance list (ASM, GSM, ESM). Plus price chart, worst fall and recovery time, "Try it on my
  portfolio", "Save with a note".
- **Fund check:** five questions: (1) what it invests in and who runs it, (2) performance against
  benchmark and category over 3, 5, 10 years, (3) how bumpy: worst fall and recovery, (4) what it
  costs per year in rupees on the user's amount and whether a cheaper plan of the same fund exists,
  (5) what changed recently. Eight fixed facts: direct or regular plan and yearly rupee cost
  difference; expense ratio against category median; fund age and size; years out of the last five
  it trailed its benchmark; category and what it may hold; share of the fund in its top ten
  holdings; exit load and lock-in; overlap with each fund the user already holds.
- **Compare:** two or three stocks, or two or three funds, side by side on the same five questions.
- **Watchlist:** saved items with the user's "why I am interested" note.
- **Everywhere:** an "Explain this" popover on financial terms giving a one-line meaning, the figure
  for this stock or fund, and what is typical for its industry or category (ship a glossary of at
  least 40 terms).
- **Try it on:** before/after for largest company exposure, top sector share, size mix, number of
  holdings, overlap with existing funds, yearly cost. State the change and stop; no advice.

### Rules for computed numbers

All numbers are computed in code. An LLM may only turn already-computed facts into sentences and
must be given nothing else; if no LLM key is configured, use deterministic sentence templates (the
app must be fully usable without an LLM key). Every figure carries a source label and as-of date.
Fund overlap = for each stock held by both funds take the lower of the two weights, then sum. True
exposure must sum to 100% of portfolio value.

## Architecture (required stack: Java and Python backend, React frontend)

- `frontend/`: React (Vite, TypeScript), a clean component library of our own with Tailwind CSS,
  Recharts for charts, React Router. Friendly empty states, loading skeletons, error states,
  accessible contrast, keyboard-usable.
- `backend-java/`: Spring Boot 3 (Java 21, Maven). The only API the frontend talks to. Owns: user
  data (holdings, watchlist, notes) in an embedded H2 file database; portfolio engine (look-through
  exposure, concentration, overlap, cost, mix, returns versus Nifty 50, try-it-on what-if);
  orchestration of calls to the Python service; response caching. JUnit tests for the portfolio
  maths.
- `backend-python/`: FastAPI service called only by the Java backend. Owns: data adapters, the
  stock-check and fund-check engines (five answers plus eight facts), statement parsing, glossary,
  sentence generation. pytest tests for facts, overlap inputs and the verdict-word scan.
- Each external source sits behind its own adapter interface with a `mock` implementation and a
  `live` implementation, selected in config:
  - Broker: `mock` | `kite_mcp` | `kite_connect`. `kite_mcp` = act as an MCP client to Zerodha's
    hosted server at https://mcp.kite.trade/mcp (streamable HTTP; the `login` tool returns a URL the
    user opens in a browser), using ONLY read tools: get_profile, get_margins, get_holdings,
    get_mf_holdings, get_positions, get_quotes, get_ltp, get_ohlc, get_historical_data,
    search_instruments, get_orders, get_trades, get_gtts. `kite_connect` = official Kite Connect
    REST API with api key and secret from config and the standard login redirect. Never call any
    order-placing, modifying or GTT-writing tool or endpoint; add a guard that refuses them.
  - Stock fundamentals, peers, shareholding: `mock` | `screener` (server-side fetch of public
    company pages, cached 24 hours, at most one request every few seconds, optional session cookie
    from config; internal only, the source name is never shown in the UI; label figures "Company
    filings").
  - Prices/history: from the broker adapter, with `nse_eod` as fallback. Surveillance lists: NSE
    ASM/GSM/ESM CSV files.
  - Fund NAV history: mfapi.in. Fund expense ratio, category, size: AMFI data. Fund portfolio
    holdings: adapter `mock` | `mfdata` (MFData.in) with a small bundled starter set.
  - Statement: parse CAMS/KFintech consolidated account statement PDFs (use the casparser library
    if installable).
- Default configuration is ALL MOCK so the whole app runs end to end with no keys: bundle realistic
  sample data for at least 12 well-known Indian stocks across sectors and 8 mutual funds (with their
  portfolios), one sample user portfolio (6 stocks, 4 funds), price history, Nifty 50 history and
  surveillance lists. Mark sample data clearly in the UI with a small "Sample data" badge.
- Config: one file `config/app-config.yaml` (git-ignored) with a committed
  `config/app-config.example.yaml` documenting every value: data-source modes, Kite api key and
  secret, Kite redirect URL, LLM provider, model and API key, optional Screener session cookie,
  cache durations, ports. No secret is ever hard-coded or committed. Both backends read the same
  file.
- Running: `docker-compose.yml` for all three services, plus plain run scripts (`./run-dev.sh`) and
  a Makefile. README with: what it is, quick start in mock mode, how to switch each adapter to live,
  config reference, architecture diagram (Mermaid), what was verified and what was not, known
  limits.

## Quality bar

- Mock mode works end to end through every screen.
- Unit tests for: overlap formula, look-through summing to 100%, try-it-on before/after, each of the
  eight stock facts and eight fund facts on sample data, rupee formatting, verdict-word scan.
- No secrets in the repo; `.gitignore` covers config, build output, H2 files, node_modules,
  virtualenvs.
- Lean process only: no user stories, tickets or sprint artefacts. Code, a README, and the three
  notes files (PLAN.md, DECISIONS.md, QUESTIONS.md).
