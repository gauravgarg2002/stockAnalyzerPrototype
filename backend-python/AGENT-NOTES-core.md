# PY-CORE notes

## Verified here
- `python -m pytest -q` (all tests incl. PY-LIVE's) and `python scripts/smoke_internal.py` (real uvicorn + Starlette fallback app, every /internal route, mock mode).

## Not executable here
- `app/main.py` (FastAPI) - fastapi is not installed in the sandbox. It is a thin wrapper over `routes.ROUTES` (same param convention as `asgi_fallback.py`); `test_routes` only compiles it.
- Live adapters, casparser, real LLM providers (`narrative/llm.py` is only tested through a fake provider).

## Assumptions / contract gaps (most conservative reading taken)
1. `Comparison` units are free: some Figure comparisons use another unit than the figure (e.g. `aum_change_1y` PCT_CHANGE compared with the fund size a year ago in INR; `years_trailed` COUNT compared with the category average in YEARS so 2.2 does not display as 2).
2. Fund `twin_gap` is always the positive rupee difference between the regular and direct plan, also when the checked fund is the direct plan (label says which plan is the other one). With no twin, value is null and the PLAN_TWIN comparison has a null value.
3. Category with no minimum equity share (debt, balanced advantage): `equity_share` THRESHOLD comparison has value 0 and label "Category minimum (no shares required)".
4. `years_trailed_benchmark.available` is false only when fewer than 5 calendar years (2021-2025) can be compared; the figure is still returned over the years that exist.
5. 10-year windows tolerate a series that starts up to 5 days after (asOf - 10 years) because the sample series starts on 2016-10-31 while asOf - 10y is 2016-10-30.
6. Surveillance status text is built from the CSV stage ("Long-term ASM Stage II" -> "ASM long-term stage II since 14 Aug 2026").
7. `glossary.explain.*` templates were added (not in the contract template table) for the "Explain this" sentence; `thisFigure`/`typical` come from the check payload built with the illustrative amount for funds.
8. Narrate `sampleData` is always false (facts come from Java; no adapter data is involved).
9. Compare for funds passes basis `COMPARE` internally (only affects the wording "the same amount used for every fund compared").
10. Unknown routes/methods return the contract error shape (404 NOT_FOUND / 400 BAD_REQUEST).
11. Sentences about falls use the absolute percentage ("the worst fall was 31.4%"); the Figure value keeps the negative sign as the contract requires.
12. Sample category averages (`fund_categories.json` averageReturns / averageWorstFallPct) are derived by the generator from each category's benchmark path so the sample stays internally consistent; medians and `averageYearsTrailed` are hand-set.

## Open questions
- Should `/internal/explain` for a fund use the user's holding amount? Currently always `app.defaultIllustrativeAmountInr` (Java passes no amount).
- Stock P/E uses trailing four quarters of net profit (not the last financial year); documented in the glossary meaning only as "yearly profit".
