import pytest

from conftest import ALL_FUNDS, SAMPLE_FUND_OVERLAPS, by_id, fig

FACT_IDS = ["plan_type", "expense_vs_category", "age_and_size", "years_trailed_benchmark", "category_mandate", "top10_share", "exit_load_lockin", "overlap_with_holdings"]
TITLES = ["Direct or regular plan, and the yearly cost difference", "Expense ratio against the category", "Fund age and size",
          "Years out of the last five it trailed its benchmark", "Category and what it may hold", "Share of the fund in its top ten holdings",
          "Exit load and lock-in", "Overlap with funds you already hold"]


@pytest.mark.parametrize("code", ALL_FUNDS)
def test_ids_order_titles(fund, code):
    f = fund(code)["facts"]
    assert [x["id"] for x in f] == FACT_IDS and [x["order"] for x in f] == list(range(1, 9)) and [x["title"] for x in f] == TITLES
    assert all(1 <= len(x["sentences"]) <= 2 for x in f)


def test_fact1_regular_gap_vs_direct_twin(fund):
    reg = by_id(fund("900101", 100000)["facts"], "plan_type")
    gap = fig(reg, "plan_cost_gap")
    assert fig(reg, "plan_type")["value"] == "Regular plan"
    assert gap["value"] == pytest.approx(100000 * (1.72 - 0.68) / 100) and gap["value"] > 0
    assert gap["comparisons"][0]["kind"] == "PLAN_TWIN" and gap["comparisons"][0]["value"] == pytest.approx(680)
    assert "would cost ₹1,040 less each year" in reg["sentences"][0]["text"]
    d = by_id(fund("900102", 100000)["facts"], "plan_type")
    assert fig(d, "plan_cost_gap")["value"] == pytest.approx(1040) and "more each year" in d["sentences"][0]["text"]


def test_fact1_no_twin_unavailable(fund):
    f = by_id(fund("900301")["facts"], "plan_type")
    assert f["available"] is False and "no matching regular plan is known" in f["sentences"][0]["text"]


def test_fact2_expense_vs_category(fund):
    f = by_id(fund("900101")["facts"], "expense_vs_category")
    x = fig(f, "expense_ratio")
    assert x["value"] == 1.72 and x["comparisons"][0]["kind"] == "CATEGORY" and x["comparisons"][0]["value"] == 1.61
    assert "above the Flexi Cap Fund median" in f["sentences"][0]["text"]
    d = fig(by_id(fund("900102")["facts"], "expense_vs_category"), "expense_ratio")
    assert d["comparisons"][0]["value"] == 0.72


def test_fact3_age_and_size(fund):
    f = by_id(fund("900201")["facts"], "age_and_size")
    assert fig(f, "fund_age")["value"] < 10 and fig(f, "fund_age")["unit"] == "YEARS"
    assert fig(f, "aum")["comparisons"][0]["kind"] == "CATEGORY"
    old = fig(by_id(fund("900101")["facts"], "age_and_size"), "fund_age")["value"]
    assert 13 < old < 14


@pytest.mark.parametrize("code", ALL_FUNDS)
def test_fact4_years_trailed_within_0_5_with_table(fund, code):
    f = by_id(fund(code)["facts"], "years_trailed_benchmark")
    x = fig(f, "years_trailed")
    assert 0 <= x["value"] <= 5 and x["unit"] == "COUNT"
    assert x["comparisons"][0]["kind"] == "CATEGORY"
    assert [r[0] for r in f["details"]["rows"]] == ["2021", "2022", "2023", "2024", "2025"]
    n = sum(1 for r in f["details"]["rows"] if r[3] == "Trailed")
    assert n == x["value"] and f["available"] is True


def test_fact5_mandate_text(fund):
    f = by_id(fund("900101")["facts"], "category_mandate")
    assert fig(f, "category")["value"] == "Flexi Cap Fund"
    assert f["sentences"][0]["text"].startswith("Flexi Cap Fund: Shares of companies of any size")
    e = fig(f, "equity_share")
    assert e["comparisons"][0] == {"kind": "THRESHOLD", "label": "Category minimum", "value": 65.0, "unit": "PCT", "display": "65.0%"}
    d = by_id(fund("900801")["facts"], "category_mandate")
    assert "no shares" in d["sentences"][0]["text"] or "holds no shares" in d["sentences"][0]["text"]


def test_fact6_top10_share(fund):
    f = by_id(fund("900201")["facts"], "top10_share")
    x = fig(f, "top10_share")
    assert 30 < x["value"] < 80 and x["comparisons"][0]["kind"] == "CATEGORY" and len(f["details"]["rows"]) == 10
    d = by_id(fund("900801")["facts"], "top10_share")
    assert d["available"] is False


def test_fact7_exit_load_lockin(fund):
    f = by_id(fund("900501")["facts"], "exit_load_lockin")
    assert fig(f, "exit_load")["value"] == "None" and fig(f, "lock_in")["value"] == 3
    assert fig(f, "lock_in")["comparisons"][0] == {"kind": "THRESHOLD", "label": "ELSS lock-in set by law: 3 years", "value": 3.0, "unit": "YEARS", "display": "3 years"}
    g = by_id(fund("900401")["facts"], "exit_load_lockin")
    assert fig(g, "exit_load")["value"] == "1% if you take money out within 365 days"
    assert fig(g, "lock_in")["comparisons"][0]["kind"] == "CATEGORY" and fig(g, "lock_in")["value"] == 0


def test_fact8_overlap_rendering_and_empty(fund):
    e = by_id(fund("900101")["facts"], "overlap_with_holdings")
    assert e["available"] is True and e["figures"] == [] and e["sentences"][0]["templateId"] == "fnd.fact.overlap_none"
    ufs = SAMPLE_FUND_OVERLAPS + [{"schemeCode": "900301", "name": "Godavari Midcap Fund - Direct Plan - Growth", "overlapPct": 20.5, "commonCount": 11}]
    f = by_id(fund("900501", user_funds=ufs)["facts"], "overlap_with_holdings")
    assert [x["id"] for x in f["figures"]] == ["overlap_900201", "overlap_900301"]
    assert f["figures"][0]["value"] == 41.37 and f["figures"][0]["comparisons"] == [] and f["figures"][0]["label"].startswith("Narmada")
    assert f["figures"][0]["unit"] == "PCT" and f["figures"][0]["termId"] == "fund_overlap"
    assert "41.4%" in f["sentences"][0]["text"] and "27 companies in common" in f["sentences"][0]["text"]
    assert "1 other fund" in f["sentences"][1]["text"]
