# backend-java notes (JV agent)

## What is verified and how
- `tools/engine-check.sh` compiles `engine/**` (imports are checked to be `java.*` or `com.stockanalyzer.engine.*` only), the JUnit shim and the engine tests with plain `javac`, then runs every `@Test` by reflection. This is the only part that was executed.
- The Spring layer (`config`, `python`, `domain`, `service`, `web`) could not be compiled with Maven here (no Maven Central). As a partial check it was compiled once against hand-written API stubs of the Spring / Jakarta / Jackson types it uses, which checks DTO records, accessors, generics and engine calls but not the real library signatures. The two Spring tests (`src/test/java/com/stockanalyzer/web`) were never compiled or run.

## Deviations from PLAN §2.3 (internal only, no contract field changed)
- `FundInfo` has three extra components: `twinName`, `categoryMedianTerPct`, `portfolioDate` (needed for A.3 `directTwin.name`, the CATEGORY comparison and the overlap `asOf`). `terPct` and `twinTerPct` are `Double` (nullable) so an unknown fee is never shown as 0.
- Result types are nested records of their engine (`OverlapEngine.OverlapPair`, `CostEngine.CostResult`, `MixEngine.MixLine`, `ReturnsEngine.ReturnsResult`, `TryItOnEngine.TryItOnResult`) and `ExposureLine`, `ExposureBreakdown`, `NarrateItem`, `MapPricePoints`, `ValuedPosition`, `Units` are extra engine files.
- `Bp.largestRemainder` has three overloads (double[] with tie values and keys, double[], long[] weights); tie rule is larger value, then key ascending, then index.
- JUnit shim also contains `org.junit.jupiter.api.function.Executable` (needed by `assertThrows`).
- DTO record names that clash with engine names carry a `View` suffix (`ExposureLineView`, `MixLineView`, ...). JSON is unaffected.

## Assumptions and contract gaps
1. `connected` (home, portfolio) = at least one KITE import that was not FAILED exists. No broker call is made on those pages.
2. Empty portfolio: `summary` = [`pf.summary.empty`], `facts` = [] on both home and portfolio, exposure/concentration `sentences` = [], cost/overlap `sentences` = [], pct figures are 0, counts are 0. The contract only specifies home.
3. `summary` has only the sentences that exist: `pf.summary.top_exposure` is skipped when there is no company line (debt-only portfolio).
4. Cost fact: `pf.fact.cost_none` when no funds; `pf.fact.cost_direct_only` only when there is no REGULAR fund; otherwise `pf.fact.cost` (the gap can be 0 when a regular fund has no known direct twin).
5. Fund-check cache key is `fund-check:{code}:{amount}:{basis}:{hash}` (basis added to the PLAN key, otherwise HOLDING and USER_INPUT with the same amount would share an entry).
6. Try-it-on on an empty portfolio sends the TEXT fact value `None` for a missing "before" company or sector name.
7. Java writes these short non-narrated strings: error messages, import-log `message` (the contract example text, e.g. "Imported 6 stocks, 4 funds and idle cash."), the `unmatched[].reason` for a stock Python does not know ("Stock not found in stock list."), figure/comparison labels, and the narrate fact `windowLabel` = "1 year".
8. Kite import: a broker stock that the Python bundle does not know is reported in `unmatched` and not stored (mock mode only knows 15 stocks).
9. Statement import stores funds only (`STATEMENT` rows), `avgPrice = avgCostNav ?? nav`, `firstBuyDate = null`; zero parseable funds gives 422 `STATEMENT_UNREADABLE`.
10. Portfolio 1Y return uses Python price points at `asOf` and `asOf - 1 year`; the holding's bundle price is the fallback for `asOf`. Since-buy uses only holdings with a known buy date and a Nifty value on that date (`coveredCount`).
11. `HoldingRow` order and `returns.holdings` order: value descending (ties kind, id).
12. `GET /api/connection.loginUrl` is the URL returned by the last `start` call while the status is PENDING_LOGIN, otherwise null.
13. A.1 `adapters` is passed through from Python `/internal/health` as a map. If Python is down, `/api/meta` returns 502 (no fallback values are invented).
14. Compare `amountInr` is sent to Python as a 2-decimal string when kind is FUND; omitted for STOCK.
15. COUNT narrate facts are sent as JSON integers, INR as whole-rupee integers, PCT as percent units (basis points / 100).

## Open questions
- Does Python's `/internal/prices/points` return the same price at `asOf` as the bundle's `lastPrice`? Java prefers the points value and only falls back to the bundle.
- Docker: the Dockerfile expects the build context to be `backend-java/`.
