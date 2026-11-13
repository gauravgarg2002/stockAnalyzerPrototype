#!/usr/bin/env python3
"""Starts the Starlette fallback app under uvicorn on a free port (mock config) and hits every /internal route with requests."""
from __future__ import annotations

import base64
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
failures: list[str] = []
checks = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global checks
    checks += 1
    if not cond:
        failures.append(f"{name} {extra}".strip())
        print(f"FAIL  {name} {extra}")
    else:
        print(f"ok    {name}")


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main() -> int:
    port = free_port()
    env = {**os.environ, "APP_CONFIG": str(ROOT / "nonexistent-config.yaml"), "PYTHONPATH": str(ROOT)}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.asgi_fallback:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                            cwd=ROOT, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if requests.get(base + "/internal/health", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.25)
        else:
            print("server did not start")
            return 2
        g = lambda path, **kw: requests.get(base + path, timeout=30, **kw)
        p = lambda path, body=None: requests.post(base + path, json=body, timeout=60)

        r = g("/internal/health"); j = r.json()
        check("health", r.status_code == 200 and j["status"] == "ok" and j["sampleData"] is True and j["asOf"] == "2026-10-30")
        r = g("/internal/search", params={"q": "tata"}); check("search", r.status_code == 200 and len(r.json()["results"]) == 2)
        r = g("/internal/search", params={"q": ""}); check("search empty -> 400", r.status_code == 400 and r.json()["error"]["code"] == "BAD_REQUEST")
        for sym in ("TCS", "HDFCBANK", "SHIVAGRO", "DECCANINF"):
            r = g(f"/internal/stocks/{sym}/check"); j = r.json()
            check(f"stock check {sym}", r.status_code == 200 and len(j["answers"]) == 5 and len(j["facts"]) == 8 and j["priceHistory"]["points"])
        r = g("/internal/stocks/NOPE/check"); check("stock 404", r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND")
        body = {"amountInr": 115448.0, "amountBasis": "HOLDING",
                "userFunds": [{"schemeCode": "900201", "name": "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "overlapPct": 41.37, "commonCount": 27}]}
        for code in ("900101", "900201", "900501", "900801"):
            r = p(f"/internal/funds/{code}/check", body); j = r.json()
            check(f"fund check {code}", r.status_code == 200 and len(j["answers"]) == 5 and len(j["facts"]) == 8 and j["amount"]["basis"] == "HOLDING")
        r = p("/internal/funds/900101/check", {"amountInr": -1}); check("fund bad amount -> 400", r.status_code == 400)
        r = g("/internal/compare", params={"kind": "STOCK", "ids": "TCS,INFY"}); check("compare stocks", r.status_code == 200 and len(r.json()["rows"]) == 5)
        r = g("/internal/compare", params={"kind": "FUND", "ids": "900101,900301,900401", "amountInr": 100000}); check("compare funds", r.status_code == 200 and len(r.json()["instruments"]) == 3)
        r = g("/internal/glossary"); check("glossary >= 40 terms", r.status_code == 200 and len(r.json()["terms"]) >= 40)
        r = g("/internal/explain", params={"term": "pe_ratio", "kind": "STOCK", "id": "TCS"}); check("explain", r.status_code == 200 and r.json()["typical"]["kind"] == "PEERS")
        r = p("/internal/instruments/bundle", {"stocks": ["TCS", "XYZ"], "funds": ["900101", "900801"]}); j = r.json()
        check("bundle", r.status_code == 200 and len(j["stocks"]) == 1 and len(j["funds"]) == 2 and j["notFound"] == [{"kind": "STOCK", "id": "XYZ"}])
        r = p("/internal/prices/points", {"items": [{"kind": "STOCK", "id": "TCS", "dates": ["2025-10-30", "2026-10-30"]}, {"kind": "INDEX", "id": "NIFTY50", "dates": ["2025-10-30"]}]})
        check("prices points", r.status_code == 200 and r.json()["items"][0]["values"][1]["value"] == 3925.4)
        r = g("/internal/broker/portfolio"); check("portfolio before connect -> 409", r.status_code == 409 and r.json()["error"]["code"] == "BROKER_NOT_CONNECTED")
        r = p("/internal/broker/login/start"); check("login start", r.status_code == 200 and r.json()["status"] == "CONNECTED")
        r = g("/internal/broker/login/status"); check("login status", r.json()["accountLabel"] == "Your Zerodha account (sample)")
        r = g("/internal/broker/portfolio"); j = r.json(); check("portfolio", r.status_code == 200 and len(j["stocks"]) == 6 and len(j["funds"]) == 4 and j["idleCashInr"] == 42350.75)
        r = p("/internal/broker/login/complete", {"requestToken": "x"}); check("complete in mock -> 400", r.status_code == 400)
        r = p("/internal/broker/logout"); check("logout", r.json()["status"] == "NOT_CONNECTED")
        items = [{"key": "summary.0", "templateId": "pf.summary.value", "facts": {"totalValueInr": {"value": 1277410, "unit": "INR"}, "stockCount": {"value": 6, "unit": "COUNT"}, "fundCount": {"value": 4, "unit": "COUNT"}}},
                 {"key": "tio.0", "templateId": "tio.cost", "facts": {"beforeInr": {"value": 9000, "unit": "INR"}, "afterInr": {"value": 10200, "unit": "INR"}}}]
        r = p("/internal/narrate", {"items": items, "useLlm": True}); j = r.json()
        check("narrate", r.status_code == 200 and j["items"][0]["sentence"]["text"] == "Your holdings are worth ₹12.8 lakh across 6 stocks and 4 mutual funds." and j["items"][1]["sentence"]["generator"] == "template")
        r = p("/internal/narrate", {"items": [{"key": "bad", "templateId": "pf.summary.value", "facts": {}}]}); check("narrate missing facts -> 400", r.status_code == 400 and r.json()["error"]["details"]["key"] == "bad")
        r = p("/internal/statements/parse", {"filename": "x.pdf", "fileBase64": base64.b64encode(b"junk").decode(), "password": "x"}); check("statement junk -> 422", r.status_code == 422)
        sample_pdf = ROOT / "app" / "data" / "sample" / "sample_cas.pdf"
        if sample_pdf.is_file():
            try:
                from pypdf import PdfReader, PdfWriter
                import io
                w = PdfWriter(); [w.add_page(pg) for pg in PdfReader(str(sample_pdf)).pages]; w.encrypt("SAMPLE1234")
                buf = io.BytesIO(); w.write(buf)
                r = p("/internal/statements/parse", {"filename": "cas.pdf", "fileBase64": base64.b64encode(buf.getvalue()).decode(), "password": "SAMPLE1234"})
                check("statement parse sample", r.status_code == 200 and len(r.json()["funds"]) >= 2, r.text[:120])
                r = p("/internal/statements/parse", {"filename": "cas.pdf", "fileBase64": base64.b64encode(buf.getvalue()).decode(), "password": "WRONG"})
                check("statement wrong password -> 422", r.status_code == 422 and r.json()["error"]["code"] == "STATEMENT_PASSWORD_INVALID")
            except ImportError:
                print("skip  statement (pypdf missing)")
        r = g("/internal/nothing"); check("unknown route -> 404 json", r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"\n{checks - len(failures)}/{checks} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
