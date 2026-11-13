# PY-LIVE notes (live adapters)

Nothing here was run against a real service; the sandbox cannot reach those hosts. Only pure parsers, fake transports
and a loopback MCP server (127.0.0.1) were exercised.

## base.py
Nothing missing. Adapters implement the Protocols as defined. Extras I rely on: `app.errors.ApiError(code, message, details)`
(codes per contract 0.2).

## Behaviour choices PY-CORE should know
- `build(config, deps)` in every module. `statement_casparser.build` raises ImportError without casparser.
  `statement_fallback.build` / `statement_casparser.build` read `deps["fund_meta"]` (needs `find_by_isin`, `search`);
  `broker_kite_*` read `deps["fund_meta"]` to map ISIN -> scheme code; `prices_broker` / `prices_chain` read `deps["broker"]`.
  Build order therefore: fund_meta, broker, then prices/statement.
- `prices_chain.build` builds its own `NseEodPrices` for the fallback; for `prices: nse_eod` use `prices_nse_eod.build`.
- `ParsedStatement.sampleData` is `True` when the fund_meta adapter's mode is "mock" (scheme codes then come from sample data).
- Live adapters set `source` to a SourceLabel string: fundamentals "Company filings", prices/surveillance "NSE",
  fund NAV/meta "AMFI", fund holdings "Fund factsheet" (or "Sample data" when the bundled starter set answered).
- Live fundamentals leave empty/None: `isin`, `marketCapRank`, `revenueSegments`, `valuationHistory`, `events`,
  `quarterly[].resultsDate`, `shareholding[].pledgedPctOfPromoter` (only the newest row), and `peerGroup.medians` holds only `pe`
  (peer members have `symbol: None`). Engines must treat these as "not available".
- Live fund meta (AMFI NAVAll.txt) leaves None: launchDate, aumInr, aumInr1yAgo, terPct, terAsOf, exitLoad, benchmarkId;
  `lockInYears` 3.0 only when the name/category says ELSS/tax saver. `category()` returns None. `managers` is [].
- Only `NIFTY50` index history is available from `prices_nse_eod`; TRI ids return None.
- `fund_holdings_mfdata` falls back to `app/data/sample/funds.json` (read-only) when the live call yields nothing.

## UNVERIFIED AGAINST LIVE SERVICE
1. Kite MCP tool result shapes (get_holdings / get_mf_holdings / get_margins / get_profile text or JSON) and the
   `get_historical_data` / `search_instruments` argument names (chosen from the advertised input schema at runtime).
2. Kite MCP `login` result: first URL in the text is taken as `loginUrl`; auth failure of `get_profile` detected from
   `isError` or auth words in the text.
3. Kite Connect response shapes (holdings, mf/holdings, margins, candles) follow public docs; historical data may need a paid add-on.
4. Company page layout (`screener_parse.parse_company_page` ids/classes), URL scheme, search endpoint (`parse_search_json`).
5. NSE: cookie warm-up, `/api/historical/cm/equity`, `/api/historical/indicesHistory` fields (`parse_equity_history`,
   `parse_index_history`), surveillance CSV columns (`parse_surveillance_csv`) and download access.
6. AMFI NAVAll.txt header-line wording (`parse_navall`).
7. mfapi.in shape (documented; parser tested on that shape only).
8. MFData.in endpoint path and fields (`parse_mfdata_holdings`).
9. CAMS / KFintech statement text layouts (`cas_text_parser`) and casparser's dict output (`map_casparser_dict`);
   casparser itself is not installed here, so that path is untested against the real library.

## Tests
`cd backend-python && python -m pytest -q tests/test_broker_guard.py tests/test_statement_parser.py tests/test_screener_parse.py tests/test_live_*.py`
