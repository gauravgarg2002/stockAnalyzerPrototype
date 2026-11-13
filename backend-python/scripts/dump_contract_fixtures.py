#!/usr/bin/env python3
"""Writes tests/fixtures/contract/*.json from the handlers in mock mode (used by the FE/Java cross-checks)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_CONFIG", str(ROOT / "nonexistent-config.yaml"))

from app import config, handlers  # noqa: E402
from app.context import AppContext  # noqa: E402

OVERLAPS = [{"schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "overlapPct": 41.37, "commonCount": 27}]
NARRATE_ITEMS = [
    {"key": "summary.0", "templateId": "pf.summary.value", "facts": {"totalValueInr": {"value": 1277410, "unit": "INR"}, "stockCount": {"value": 6, "unit": "COUNT"}, "fundCount": {"value": 4, "unit": "COUNT"}}},
    {"key": "fact.overlap", "templateId": "pf.fact.overlap", "facts": {"fundA": {"value": "Kaveri Flexi Cap Fund - Regular Plan - Growth", "unit": "TEXT"},
     "fundB": {"value": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "unit": "TEXT"}, "overlapPct": {"value": 41.37, "unit": "PCT"}, "commonCount": {"value": 27, "unit": "COUNT"}}}]


def main(out_dir: Path) -> None:
    ctx = AppContext(config.load("/nonexistent/app-config.yaml"))
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "health": handlers.health(ctx, {}),
        "search": handlers.search(ctx, {"q": "tata"}),
        "stock-check-tcs": handlers.stock_check(ctx, {"symbol": "TCS"}),
        "stock-check-hdfcbank": handlers.stock_check(ctx, {"symbol": "HDFCBANK"}),
        "stock-check-shivagro": handlers.stock_check(ctx, {"symbol": "SHIVAGRO"}),
        "fund-check-900101": handlers.fund_check(ctx, {"schemeCode": "900101", "body": {"amountInr": 115448.0, "amountBasis": "HOLDING", "userFunds": OVERLAPS}}),
        "fund-check-900201": handlers.fund_check(ctx, {"schemeCode": "900201", "body": {"amountInr": 100000.0, "amountBasis": "ILLUSTRATIVE", "userFunds": []}}),
        "fund-check-900801": handlers.fund_check(ctx, {"schemeCode": "900801", "body": {"amountInr": 100000.0, "amountBasis": "ILLUSTRATIVE", "userFunds": []}}),
        "compare-stocks": handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,INFY"}),
        "compare-funds": handlers.compare(ctx, {"kind": "FUND", "ids": "900101,900301", "amountInr": "100000"}),
        "glossary": handlers.glossary(ctx, {}),
        "explain-pe": handlers.explain(ctx, {"term": "pe_ratio", "kind": "STOCK", "id": "TCS"}),
        "bundle": handlers.bundle(ctx, {"body": {"stocks": ["TCS", "HDFCBANK", "XYZ"], "funds": ["900101", "900201", "900801"]}}),
        "prices-points": handlers.prices_points(ctx, {"body": {"items": [{"kind": "STOCK", "id": "TCS", "dates": ["2025-10-30", "2023-06-05", "2026-10-30"]}, {"kind": "INDEX", "id": "NIFTY50", "dates": ["2025-10-30", "2026-10-30"]}]}}),
        "broker-start": handlers.broker_login_start(ctx, {}),
        "broker-status": handlers.broker_login_status(ctx, {}),
        "broker-portfolio": handlers.broker_portfolio(ctx, {}),
        "narrate": handlers.narrate(ctx, {"body": {"items": NARRATE_ITEMS, "useLlm": False}}),
    }
    for name, payload in files.items():
        (out_dir / f"{name}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(files)} fixtures to {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests" / "fixtures" / "contract")
