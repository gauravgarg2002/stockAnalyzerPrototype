# Frontend agent notes

## Verified here
- `tsc -p tsconfig.lib.json` (lib only, strict) and `tsx --test src/lib/*.test.ts`.
- esbuild bundling of `src/main.tsx` with react, react-dom, react-router-dom and recharts as externals. This is a syntax and import-resolution check only. It is not a type-check and not a render.
- The `.tsx` files were also type-checked against hand-written, deliberately loose stubs for react, react-router-dom and recharts. That proves every `copy.*` key, `lib/*` import and contract field name used by the components exists. It does not prove prop types against the real `@types/react`.

## Not verified here
- `vite build`, Tailwind output, Recharts rendering, the real `@types/react` type-check, any browser behaviour (focus handling, popover placement), and any call to a real backend.

## Contract gaps and assumptions
- The contract has no endpoint to read a single holding or disconnect-status polling interval; the FE polls `GET /api/connect/kite/status` every 2 s for at most 5 minutes (the contract's `kite.loginTimeoutSeconds` default) because the FE does not receive the configured value.
- `Figure.value` is typed `number | string | null` and `Comparison.value` the same (TEXT comparisons are possible).
- Negative zero: `formatPct(-0.04)` gives `0.0%` (no `-`). The contract vectors do not cover it. Java's BigDecimal behaves the same; Python's Decimal quantize would give `-0.0`. Worth aligning in the cross-language check.
- Rupee amounts are ordered before ratios inside each figure grid by a stable sort in `FigureGrid` (display order only; no maths).
- The glossary endpoint is wrapped in `api-client.ts` but no screen lists the whole glossary; terms are reached through the "Explain this" popover (`GET /api/explain`).
- Overlap detail rows show `weightA`, `weightB`, `minWeight` formatted with `formatPct` (1 dp), so they can differ from the 2 dp numbers in the JSON.
- `Try it on` sends `months: null` for LUMP_SUM (the contract says it is ignored and echoed as null).
- `contract-fixtures.check.ts` from PLAN §2.4 is not written: the Python fixture file names were not known when this was built. The integrating session can assign each fixture JSON to its type in `src/lib/api-types.ts` with `resolveJsonModule`.

## Open questions
- Should `/api/import/kite` also be called automatically after `POST /api/connect/kite/start` returns CONNECTED in mock mode? The FE does so (per the contract's FE rule).
- The sample "Made-up company" badge uses `instrument.fictional`; confirm that wording is acceptable.
