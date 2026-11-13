import pytest

from app import handlers
from conftest import ALL_FUNDS


def overlap(a, b):
    wa = {h["key"]: h["weightPct"] for h in a["holdings"]}
    wb = {h["key"]: h["weightPct"] for h in b["holdings"]}
    return round(sum(min(wa[k], wb[k]) for k in wa.keys() & wb.keys()), 2), len(wa.keys() & wb.keys())


@pytest.fixture(scope="module")
def bundle(ctx):
    b = handlers.bundle(ctx, {"body": {"stocks": ["TCS", "XYZ"], "funds": ALL_FUNDS + ["000000"]}})
    return b, {f["schemeCode"]: f for f in b["funds"]}


def test_not_found_listed(bundle):
    b, _ = bundle
    assert b["notFound"] == [{"kind": "STOCK", "id": "XYZ"}, {"kind": "FUND", "id": "000000"}]
    assert [s["symbol"] for s in b["stocks"]] == ["TCS"] and len(b["funds"]) == 9


def test_weights_valid_and_within_equity(bundle):
    _, funds = bundle
    for code, f in funds.items():
        mix = f["assetMix"]
        assert round(sum(mix.values()), 2) == 100.0, code
        total = 0.0
        for h in f["holdings"]:
            assert 0 < h["weightPct"] <= 100
            assert h["key"] == (h["symbol"] or h["isin"] or "NAME:" + h["name"].upper())
            total += h["weightPct"]
        assert total <= mix["equityPct"] + 1e-6, code
        if f["holdings"]:
            assert mix["equityPct"] - 2.5 - 1e-6 <= total <= mix["equityPct"] - 0.8 + 1e-6, (code, total)


def test_twins_identical(bundle):
    _, funds = bundle
    assert funds["900101"]["holdings"] == funds["900102"]["holdings"]
    assert funds["900101"]["assetMix"] == funds["900102"]["assetMix"]
    assert funds["900101"]["twinSchemeCode"] == "900102" and funds["900101"]["twinTerPct"] == 0.68 and funds["900102"]["twinTerPct"] == 1.72
    assert overlap(funds["900101"], funds["900102"])[0] == round(sum(h["weightPct"] for h in funds["900101"]["holdings"]), 2)


def test_index_fund_has_50_names_and_debt_fund_none(bundle):
    _, funds = bundle
    assert len(funds["900201"]["holdings"]) == 50
    assert funds["900801"]["holdings"] == [] and funds["900801"]["assetMix"]["debtPct"] == 93.0


def test_overlap_formula_and_sample_user_pairs(bundle):
    _, funds = bundle
    a = {"holdings": [{"key": "X", "weightPct": 10}, {"key": "Y", "weightPct": 5}]}
    b = {"holdings": [{"key": "X", "weightPct": 4}, {"key": "Z", "weightPct": 7}]}
    assert overlap(a, b) == (4.0, 1) and overlap(a, b) == overlap(b, a)
    assert overlap(a, {"holdings": [{"key": "Q", "weightPct": 1}]})[0] == 0
    pct, n = overlap(funds["900101"], funds["900201"])
    assert 15 < pct < 70 and n > 10
    pct2, _ = overlap(funds["900101"], funds["900501"])
    assert pct2 > 5


def test_bundle_fields(bundle):
    b, funds = bundle
    s = b["stocks"][0]
    assert s["symbol"] == "TCS" and s["subtitle"] == "Information Technology · Large cap" and s["priceOneYearAgo"] > 0 and s["lastPriceDate"] == "2026-10-30"
    f = funds["900101"]
    assert f["categoryMedianTerPct"] == 1.61 and funds["900102"]["categoryMedianTerPct"] == 0.72
    assert f["navDate"] == "2026-10-30" and f["navOneYearAgo"] > 0 and f["portfolioDate"] == "2026-09-30"
    assert f["subtitle"] == "Flexi Cap Fund · Regular plan" and f["source"] == "Sample data"
    h = f["holdings"][0]
    assert h["checkAvailable"] == (h["symbol"] in ("RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC", "LT", "SUNPHARMA", "MARUTI", "ASIANPAINT", "TATASTEEL", "BHARTIARTL", "VOLTAS", "FEDERALBNK", "DECCANINF", "SHIVAGRO"))
    assert all(x["sizeBand"] in ("LARGE", "MID", "SMALL", "MICRO") and x["sector"] for x in f["holdings"])
