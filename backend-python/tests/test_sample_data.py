import csv
import json
import filecmp
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.adapters import sample_store as ss
from conftest import ALL_FUNDS, ALL_STOCKS

ROOT = Path(__file__).resolve().parent.parent


def test_counts():
    assert len(ss.stock_records()) == 15 and list(ss.stock_records()) == ALL_STOCKS
    assert len(ss.fund_records()) == 9
    assert 75 <= len(ss.universe()) <= 85
    u = ss.sample_user()
    assert len(u["stocks"]) == 6 and len(u["funds"]) == 4 and u["idleCashInr"] == 42350.75
    assert ss.manifest() == {"asOf": "2026-10-30", "seed": 20261030, "generator": "scripts/generate_sample_data.py", "generatorVersion": 1,
                             "note": "Illustrative sample data, not real figures."}
    assert {i["id"] for i in ss.indices()} == {"NIFTY50", "NIFTY50_TRI", "NIFTY100_TRI", "NIFTY500_TRI", "NIFTY_MIDCAP150_TRI", "NIFTY_SMALLCAP250_TRI",
                                                 "CRISIL_HYBRID_35_65", "CRISIL_SHORT_DURATION_DEBT"}


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_stock_series(sym):
    s = ss.stock_prices(sym)
    r = ss.stock_records()[sym]
    assert s.points[0][0] == date(2021, 11, 1) and s.points[-1][0] == date(2026, 10, 30)
    assert s.points[-1][1] == r["lastPrice"]
    assert all(d.weekday() < 5 for d, _, _ in s.points)
    assert all(v >= 1 for _, _, v in s.points) and all(c > 0 for _, c, _ in s.points)
    assert len(r["annual"]) == 5 and len(r["quarterly"]) == 8 and len(r["shareholding"]) == 5 and len(r["valuationHistory"]) == 60
    assert r["valuationHistory"][0]["monthEnd"] == "2021-10-31" and r["valuationHistory"][-1]["monthEnd"] == "2026-09-30"
    assert [a["fy"] for a in r["annual"]] == ["FY2026", "FY2025", "FY2024", "FY2023", "FY2022"]


def test_market_shock_visible_in_index():
    n = ss.index_prices("NIFTY50")
    assert n.points[0][0] == date(2016, 10, 31) and n.points[-1][1] == 26150.0
    by = dict((d, c) for d, c, _ in n.points)
    assert by[date(2022, 6, 17)] / by[date(2022, 1, 17)] < 0.9


def test_fictional_flags_and_bands():
    recs = ss.stock_records()
    assert {s for s, r in recs.items() if r["fictional"]} == {"DECCANINF", "SHIVAGRO"}
    assert {s: r["sizeBand"] for s, r in recs.items()}["VOLTAS"] == "MID"
    assert recs["HDFCBANK"]["isFinancial"] and recs["FEDERALBNK"]["isFinancial"]
    assert recs["DECCANINF"]["shareholding"][0]["pledgedPctOfPromoter"] == 38.4
    assert recs["ASIANPAINT"]["shareholding"][0]["promoterPct"] < recs["ASIANPAINT"]["shareholding"][4]["promoterPct"]
    assert all(recs[s]["shareholding"][i]["promoterPct"] < recs[s]["shareholding"][i + 1]["promoterPct"] for s in ["ASIANPAINT"] for i in range(4))
    assert any(a["netProfitInr"] < 0 for a in recs["SHIVAGRO"]["annual"] if a["fy"] == "FY2025")
    ents = {e.symbol: e for e in ss.surveillance_entries()}
    assert ents["SHIVAGRO"].list == "ASM" and ents["SHIVAGRO"].since == "2026-08-14"
    assert {e.list for e in ss.surveillance_entries()} == {"ASM", "GSM", "ESM"}


def test_funds_shape():
    f = ss.fund_records()
    assert f["900101"]["twinSchemeCode"] == "900102" and f["900102"]["twinSchemeCode"] == "900101"
    assert f["900201"]["launchDate"] == "2019-07-01" and f["900501"]["lockInYears"] == 3
    assert f["900401"]["exitLoad"] == {"text": "1% if you take money out within 365 days", "pct": 1.0, "days": 365}
    assert f["900601"]["assetMix"] == {"equityPct": 72.0, "debtPct": 23.0, "cashPct": 4.0, "otherPct": 1.0}
    assert f["900801"]["holdings"] == [] and f["900801"]["assetMix"]["debtPct"] == 93.0
    assert any(e["date"] == "2026-07-01" for e in f["900701"]["events"])
    for code, r in f.items():
        assert r["isin"] == "INFSMP" + code and code.startswith("9")
        n = ss.navs(code)
        assert n.points[-1][0] == date(2026, 10, 30)
        assert n.points[0][0] == max(date.fromisoformat(r["launchDate"]), date(2016, 10, 31))
        assert r["benchmarkId"] in {i["id"] for i in ss.indices()}


def test_twins_share_portfolio():
    f = ss.fund_records()
    for k in ("holdings", "assetMix", "portfolioDate", "managers", "benchmarkId", "launchDate", "aumInr", "aumInr1yAgo"):
        assert f["900101"][k] == f["900102"][k]


def test_previous_top10_differs_by_one_or_two():
    for code, r in ss.fund_records().items():
        if not r["holdings"]:
            continue
        cur = {h["symbol"] for h in r["holdings"][:10]}
        prev = {h["symbol"] for h in r["previousTop10"]}
        assert len(prev) == 10 and 1 <= len(cur - prev) <= 2, code


def test_deterministic_regeneration(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts" / "generate_sample_data.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    gen.generate(tmp_path)
    committed = ROOT / "app" / "data" / "sample"
    files = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert len(files) > 40
    for rel in files:
        assert (tmp_path / rel).read_bytes() == (committed / rel).read_bytes(), rel
