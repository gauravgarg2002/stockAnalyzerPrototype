import pytest

from app.verdict_scan import walk_strings
from conftest import ALL_STOCKS, by_id, fig

QUESTIONS = ["What does the company do and how does it earn money?", "Is it growing and profitable?", "Is it financially safe?",
             "How is it priced against its own history and its peers?", "What changed recently?"]
IDS = ["business", "growth", "safety", "price", "recent"]
FIG_IDS = {
    "business": ["revenue_fy", "top_segment_share"], "growth": ["revenue_cagr_3y", "profit_cagr_3y", "operating_margin", "roe"],
    "safety": ["total_debt", "debt_to_equity", "interest_coverage", "cash"], "price": ["pe", "pb", "market_cap", "dividend_yield"],
    "recent": ["quarter_revenue_yoy", "quarter_profit_yoy", "price_change_90d"]}


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_five_answers_fixed(stock, sym):
    c = stock(sym)
    assert [a["id"] for a in c["answers"]] == IDS and [a["question"] for a in c["answers"]] == QUESTIONS
    assert [a["order"] for a in c["answers"]] == [1, 2, 3, 4, 5]
    for a in c["answers"]:
        assert 2 <= len(a["sentences"]) <= 3
        exp = FIG_IDS[a["id"]]
        if a["id"] == "safety" and c["instrument"]["sector"] == "Financial Services" and sym in ("HDFCBANK", "FEDERALBNK"):
            exp = ["net_worth", "roe"]
        assert [f["id"] for f in a["figures"]] == exp, (sym, a["id"])


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_every_numeric_figure_has_comparison(stock, sym):
    c = stock(sym)
    for block in c["answers"] + c["facts"]:
        for f in block["figures"]:
            if f["unit"] != "TEXT" and not f["id"].startswith("overlap_"):
                assert f["comparisons"], (sym, block["id"], f["id"])
            assert f["display"] == "Not available" or f["value"] is not None
            assert f["source"] == "Sample data"


def test_answer_comparison_kinds(stock):
    c = stock("TCS")
    g = by_id(c["answers"], "growth")
    assert [x["kind"] for x in fig(g, "operating_margin")["comparisons"]] == ["OWN_HISTORY", "PEERS"]
    assert [x["kind"] for x in fig(g, "revenue_cagr_3y")["comparisons"]] == ["PEERS"]
    p = by_id(c["answers"], "price")
    assert [x["kind"] for x in fig(p, "pe")["comparisons"]] == ["OWN_HISTORY", "PEERS"]
    assert fig(p, "pe")["comparisons"][1]["label"] == "Median of IT services peers"
    assert fig(p, "pe")["comparisons"][1]["value"] == 25.1
    r = by_id(c["answers"], "recent")
    assert fig(r, "price_change_90d")["comparisons"][0]["kind"] == "INDEX"


def test_bank_safety_branch(stock):
    s = by_id(stock("HDFCBANK")["answers"], "safety")
    assert "bank or lender" in s["sentences"][0]["text"]
    assert fig(s, "roe")["comparisons"][0]["kind"] == "PEERS"


def test_loss_company_pe_may_be_null_or_set(stock):
    p = by_id(stock("SHIVAGRO")["answers"], "price")
    assert fig(p, "pe")["unit"] == "TIMES"


def test_instrument_priceHistory_drawdown(stock):
    c = stock("TCS")
    ih = c["instrument"]
    assert ih["lastPrice"]["id"] == "last_price" and ih["lastPrice"]["comparisons"][0]["label"] == "1 year ago"
    assert ih["marketCap"]["id"] == "market_cap"
    ph = c["priceHistory"]
    assert ph["frequency"] == "WEEKLY" and ph["from"] == "2021-11-05" and ph["to"] == "2026-10-30"
    assert ph["points"][-1]["date"] == "2026-10-30" and ph["benchmark"]["id"] == "NIFTY50"
    assert [p["date"] for p in ph["benchmark"]["points"]] == [p["date"] for p in ph["points"]]
    assert ph["benchmark"]["points"][0]["value"] == pytest.approx(ph["points"][0]["value"], rel=1e-3)
    dd = c["drawdown"]
    assert dd["window"] == "5Y" and dd["worstFall"]["id"] == "worst_fall" and dd["worstFall"]["value"] < 0
    assert dd["worstFall"]["comparisons"][0]["kind"] == "BENCHMARK"
    assert dd["peakDate"] < dd["troughDate"]
    if dd["recoveryDate"] is None:
        assert dd["recoveryDays"] is None
    assert c["peers"]["groupName"] == "IT services"
    assert {m["symbol"]: m["checkAvailable"] for m in c["peers"]["members"]}["INFY"] is True
    assert {m["symbol"]: m["checkAvailable"] for m in c["peers"]["members"]}["HCLTECH"] is False


def test_details_tables_present(stock):
    c = stock("TCS")
    assert by_id(c["answers"], "business")["details"]["title"] == "Revenue by business"
    for a in c["answers"]:
        d = a["details"]
        assert d and all(len(r) == len(d["columns"]) for r in d["rows"])


def test_unknown_stock_404(ctx):
    from app import handlers
    from app.errors import ApiError
    with pytest.raises(ApiError) as e:
        handlers.stock_check(ctx, {"symbol": "XYZ"})
    assert e.value.status == 404 and e.value.body() == {"error": {"code": "NOT_FOUND", "message": "No stock found for symbol XYZ.", "details": {"symbol": "XYZ"}}}


def test_no_screener_word_anywhere(stock):
    for sym in ALL_STOCKS:
        assert not any("screener" in s.lower() for _, s in walk_strings(stock(sym)))
