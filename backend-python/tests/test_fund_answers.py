import pytest

from conftest import ALL_FUNDS, SAMPLE_FUND_OVERLAPS, by_id, fig

QUESTIONS = ["What does it invest in and who runs it?", "How has it done against its benchmark and category over 3, 5 and 10 years?",
             "How bumpy has the ride been?", "What does it cost per year on your amount?", "What changed recently?"]
IDS = ["holdings", "performance", "bumpiness", "cost", "recent"]
FIG_IDS = {"holdings": ["equity_share", "holdings_count", "manager_tenure"], "performance": ["return_3y", "return_5y", "return_10y"],
           "bumpiness": ["worst_fall", "recovery_time"], "cost": ["expense_ratio", "yearly_cost", "twin_gap"], "recent": ["aum", "aum_change_1y"]}


@pytest.mark.parametrize("code", ALL_FUNDS)
def test_five_answers_fixed(fund, code):
    c = fund(code)
    assert [a["id"] for a in c["answers"]] == IDS and [a["question"] for a in c["answers"]] == QUESTIONS
    for a in c["answers"]:
        assert 2 <= len(a["sentences"]) <= 3, (code, a["id"])
        assert [f["id"] for f in a["figures"]] == FIG_IDS[a["id"]]
        for f in a["figures"]:
            assert f["comparisons"], (code, a["id"], f["id"])
    for b in c["answers"] + c["facts"]:
        for f in b["figures"]:
            if f["unit"] != "TEXT" and not f["id"].startswith("overlap_"):
                assert f["comparisons"], (code, b["id"], f["id"])


def test_performance_periods_and_young_fund(fund):
    p = by_id(fund("900101")["answers"], "performance")
    assert [x["kind"] for x in fig(p, "return_5y")["comparisons"]] == ["BENCHMARK", "CATEGORY"]
    assert all(fig(p, f"return_{n}y")["value"] is not None for n in (3, 5, 10))
    young = by_id(fund("900201")["answers"], "performance")
    assert fig(young, "return_10y")["value"] is None and fig(young, "return_10y")["display"] == "Not available"
    assert "younger than 10 years" in young["sentences"][2]["text"]
    assert fig(young, "return_5y")["value"] is not None
    labels = [r[0] for r in p["details"]["rows"]]
    assert labels[-5:] == [f"Calendar year {y}" for y in range(2021, 2026)]


def test_bumpiness_windows(fund):
    c = fund("900101")
    assert c["drawdown"]["window"] == "10Y" and c["drawdown"]["worstFall"]["value"] < 0
    assert fund("900201")["drawdown"]["window"] == "SINCE_LAUNCH"
    b = by_id(c["answers"], "bumpiness")
    assert fig(b, "worst_fall")["value"] == c["drawdown"]["worstFall"]["value"]
    assert [x["kind"] for x in fig(b, "worst_fall")["comparisons"]] == ["BENCHMARK", "CATEGORY"]
    assert 1 <= len(b["details"]["rows"]) <= 5


def test_cost_numbers_and_amount_basis(fund):
    c = fund("900101", 200000.0, "USER_INPUT")
    cost = by_id(c["answers"], "cost")
    assert fig(cost, "yearly_cost")["value"] == pytest.approx(3440) and fig(cost, "yearly_cost")["comparisons"][0]["value"] == pytest.approx(1360)
    assert fig(cost, "twin_gap")["value"] == pytest.approx(2080)
    assert "the amount you entered" in cost["sentences"][0]["text"]
    assert c["amount"] == {"amountInr": 200000.0, "display": "₹2 lakh", "basis": "USER_INPUT"}
    ill = by_id(fund("900301", 100000.0, "ILLUSTRATIVE")["answers"], "cost")
    assert fig(ill, "twin_gap")["value"] is None and fig(ill, "yearly_cost")["comparisons"][0]["kind"] == "CATEGORY"
    assert "illustrative amount" in ill["sentences"][0]["text"]


def test_holdings_and_recent(fund):
    h = by_id(fund("900101")["answers"], "holdings")
    assert fig(h, "equity_share")["comparisons"][0]["kind"] == "THRESHOLD"
    assert h["details"]["rows"][0][2].endswith("%")
    r = by_id(fund("900701")["answers"], "recent")
    assert "Pooja Sharma joined as co-manager" in r["sentences"][2]["text"]
    assert fig(r, "aum")["comparisons"][0]["label"] == "1 year ago"
    debt = by_id(fund("900801")["answers"], "holdings")
    assert fig(debt, "holdings_count")["value"] is None


def test_instrument_block(fund):
    i = fund("900101")["instrument"]
    assert i["twin"] == {"schemeCode": "900102", "name": "Kaveri Flexi Cap Fund - Direct Plan - Growth", "planType": "DIRECT"}
    assert i["benchmark"] == {"id": "NIFTY500_TRI", "name": "Nifty 500 TRI"} and i["nav"]["id"] == "nav" and i["nav"]["value"] == 62.4012
    assert fund("900301")["instrument"]["twin"] is None
    ph = fund("900101")["priceHistory"]
    assert ph["from"] <= "2016-11-04" and ph["to"] == "2026-10-30" and ph["benchmark"]["id"] == "NIFTY500_TRI"
