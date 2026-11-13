# Questions for the owner

1. **First real run.** Please run `./run-dev.sh` and tell me what breaks. Maven compile of the Spring layer, `npm install && npm run build` and the first browser render have never happened. In particular, the root `@ConfigurationProperties` record `AppProperties` (empty prefix) and H2 DDL for `@Lob` columns could not be confirmed without a real build.
2. **Live Kite.** Which route do you want first: `kite_mcp` (no API key, browser login) or `kite_connect` (needs your API key/secret and a registered redirect URL)? Tool result shapes and argument names for the MCP server are unverified.
3. **Company data source.** Is server-side fetching of public company pages acceptable for your own use, and do you have a session cookie to configure? Page layout and URL assumptions are unverified.
4. **Live fund fields.** AMFI NAVAll gives category and NAV only. Where should expense ratio, fund size, exit load and benchmark come from in live mode (factsheets, MFData.in, another feed)? Until decided they show "Not available".
5. **MFData.in.** Exact endpoint path and fields are unverified; the adapter falls back to the bundled starter holdings (labelled "Sample data") if the call yields nothing. Is that fallback acceptable, or should it show "Not available"?
6. **Fictional sample names.** Two stocks and all fund houses are made up (the UI shows a "Made-up company for the sample" badge for stocks). Confirm the wording, or prefer real names with clearly illustrative numbers.
7. **P/E basis.** Sample P/E uses the last four quarters of net profit, not the last financial year. Which do you want?
8. **Fund "Explain this" amount.** Java passes no amount, so fund explain uses the illustrative amount in config (Rs 1,00,000). Should it use the user's holding when they own the fund?
9. **Returns method.** Price/NAV return only. Do you want XIRR (needs buy dates, which Kite does not give) added later?
10. **Kite polling.** The frontend polls the connection status every 2 seconds for up to 5 minutes; the configured timeout is not exposed to it. Add it to the meta endpoint?
11. **Negative zero.** `formatPct(-0.04)` shows `0.0%` in TypeScript/Java; Python's decimal may give `-0.0`. Align in a cross-language test once everything runs.
12. **Glossary screen.** There is an endpoint but no browse page; terms are reached through "Explain this". Add one?
