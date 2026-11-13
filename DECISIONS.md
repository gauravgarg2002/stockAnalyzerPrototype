# Decisions made while building (owner was asleep)

1. **Repo and branch.** The repo was empty, so everything went to `main` directly; no PR.
2. **Planning.** One Plan sub-agent (opus) produced `PLAN.md` and `docs/api-contract.md`; four coding sub-agents (sonnet) built Python core, Python live adapters, Java and the frontend in parallel against that contract, followed by independent review passes on the Java and frontend code.
3. **Package registries blocked.** No installs were possible, so the design keeps logic in framework-free modules that can be run here: Python engines (plus a Starlette fallback app next to the FastAPI `main.py`), a pure-Java `engine/` package with a small JUnit stand-in runner, and a dependency-free `frontend/src/lib`.
4. **Percentages in basis points.** The Java engine rounds with the largest-remainder method so exposure lines sum to exactly 100.00% and rupee lines to the exact total. Rupee and percent formatting share one rounding rule (half-up on the shortest decimal) and common test vectors in all three languages.
5. **Idle cash is not part of portfolio value.** Exposure sums to 100% of invested value; idle cash is reported separately.
6. **Overlap in Java, sentences in Python.** Java computes all portfolio numbers and sends only computed facts to Python's `/internal/narrate`, which returns sentences from templates (31+ templates). Java writes no user-facing sentences except error messages.
7. **Sample data.** Deterministic generator (seed 20261030, fixed "today" 30 Oct 2026). Two stocks (pledge case, surveillance case) and all fund houses are fictional so no real company is tied to an invented flag. Real company names are used for the other 13 stocks with illustrative figures.
8. **SIP modelling.** Try-it-on SIP = 12 monthly instalments (1-60 allowed) at today's price, as new money.
9. **Returns.** Price/NAV only versus the Nifty 50 price index on the same dates; since-buy returns only where a buy date is known (Kite gives none).
10. **Live data gaps are shown, not guessed.** Missing live fields appear as "Not available"; `benchmarkId` is not inferred from category in live fund meta.
11. **Source labels.** Mock figures say "Sample data". Live figures use generic labels (Company filings, NSE, AMFI, Fund factsheet, Your Zerodha account). The fundamentals source's name never reaches the UI.
12. **Banned-word regex** covers the brief's words plus common word forms; templates avoid collisions (for example "buyback" is written without the hyphen form). `should` and `good`/`bad` are banned everywhere in user-facing text.
13. **Kite safety.** Allow-lists (not deny-lists) for both Kite modes; anything not listed is refused before any network call.
14. **Groww** was mentioned in the owner's earlier notes but the brief covers Kite only; Groww import is out of scope.
15. **Fund-check cache key** includes the amount basis so a holding-based amount and a user-typed amount never share an entry.
16. **Kite import in mock mode** reports a broker stock Python does not know as "unmatched" rather than storing it.
