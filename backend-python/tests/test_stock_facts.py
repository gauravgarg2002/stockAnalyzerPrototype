import pytest

from conftest import ALL_STOCKS, by_id, fig

FACT_IDS = ["promoter_holding", "promoter_pledge", "profit_last_3y", "debt_to_earnings", "price_move_30d", "avg_traded_value", "size_band", "surveillance"]
TITLES = ["Promoter holding", "Promoter pledge", "Profit or loss in each of the last three years", "Debt against yearly earnings",
          "Price move in the last 30 days", "Average daily trading value", "Size band", "NSE surveillance lists (ASM, GSM, ESM)"]


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_ids_order_titles_fixed(stock, sym):
    facts = stock(sym)["facts"]
    assert [f["id"] for f in facts] == FACT_IDS
    assert [f["order"] for f in facts] == list(range(1, 9))
    assert [f["title"] for f in facts] == TITLES
    for f in facts:
        assert 1 <= len(f["sentences"]) <= 2


def test_fact1_promoter_holding_direction(stock):
    f = by_id(stock("TCS")["facts"], "promoter_holding")
    assert f["sentences"][0]["text"] == "Promoters own 71.8% of the company, unchanged from 71.8% four quarters ago."
    f = by_id(stock("ASIANPAINT")["facts"], "promoter_holding")
    assert "down from" in f["sentences"][0]["text"]
    assert fig(f, "promoter_holding")["comparisons"][0]["kind"] == "PREVIOUS_PERIOD"
    assert f["details"]["columns"] == ["Quarter end", "Promoter holding", "Pledged (of promoter shares)"] and len(f["details"]["rows"]) == 5


def test_fact2_pledge_deccaninf(stock):
    f = by_id(stock("DECCANINF")["facts"], "promoter_pledge")
    assert fig(f, "promoter_pledge")["value"] == 38.4
    assert fig(f, "promoter_pledge")["display"] == "38.4%"
    assert "38.4%" in f["sentences"][0]["text"]
    none = by_id(stock("TCS")["facts"], "promoter_pledge")
    assert "None of the promoters' shares are pledged" in none["sentences"][0]["text"]


def test_fact3_profit_three_years_with_loss(stock):
    f = by_id(stock("SHIVAGRO")["facts"], "profit_last_3y")
    assert [x["id"] for x in f["figures"]] == ["net_profit_y1", "net_profit_y2", "net_profit_y3"]
    assert f["figures"][0]["label"] == "FY2024 (Apr 2023–Mar 2024)"
    assert f["figures"][1]["value"] < 0 and "a loss of" in f["sentences"][0]["text"]
    assert f["sentences"][1]["text"] == "1 year in this period ended with a net loss."
    assert all(x["comparisons"][0]["kind"] == "PREVIOUS_PERIOD" for x in f["figures"])
    ok = by_id(stock("TCS")["facts"], "profit_last_3y")
    assert ok["sentences"][1]["text"] == "Each of the three years ended with a profit."


def test_fact4_debt_to_earnings(stock):
    bank = by_id(stock("HDFCBANK")["facts"], "debt_to_earnings")
    assert bank["available"] is False and bank["figures"] == [] and "bank" in bank["sentences"][0]["text"]
    ts = by_id(stock("TATASTEEL")["facts"], "debt_to_earnings")
    assert fig(ts, "debt_to_profit")["value"] > 10
    assert {c["kind"] for c in fig(ts, "debt_to_profit")["comparisons"]} == {"OWN_HISTORY", "PEERS"}
    tcs = by_id(stock("TCS")["facts"], "debt_to_earnings")
    assert fig(tcs, "debt_to_profit")["value"] < 1


def test_fact5_results_in_window(stock):
    t = by_id(stock("TCS")["facts"], "price_move_30d")
    assert fig(t, "results_in_window")["value"] == "Yes, on 9 Oct 2026"
    assert "announced in this period, on 9 Oct 2026" in t["sentences"][1]["text"]
    m = by_id(stock("MARUTI")["facts"], "price_move_30d")
    assert fig(m, "results_in_window")["value"] == "No"
    assert fig(m, "price_change_30d")["comparisons"][0]["kind"] == "INDEX"
    assert fig(m, "price_change_30d")["unit"] == "PCT_CHANGE"


def test_fact6_avg_traded_value(stock):
    for sym in ALL_STOCKS:
        f = by_id(stock(sym)["facts"], "avg_traded_value")
        x = fig(f, "avg_daily_traded_value")
        assert x["value"] > 0 and x["unit"] == "INR"
        assert {c["kind"] for c in x["comparisons"]} == {"OWN_HISTORY", "PEERS"}


def test_fact7_size_bands(stock):
    expect = {"TCS": "LARGE", "VOLTAS": "MID", "DECCANINF": "SMALL", "SHIVAGRO": "MICRO"}
    labels = {"LARGE": "Large cap", "MID": "Mid cap", "SMALL": "Small cap", "MICRO": "Micro cap"}
    for sym, band in expect.items():
        c = stock(sym)
        assert c["instrument"]["sizeBand"] == band
        f = by_id(c["facts"], "size_band")
        assert fig(f, "size_band")["value"].startswith(labels[band])
        assert fig(f, "market_cap")["comparisons"][0]["kind"] == "THRESHOLD"
    assert "rank 2 by market value" in fig(by_id(stock("TCS")["facts"], "size_band"), "size_band")["value"]
    assert fig(by_id(stock("TCS")["facts"], "size_band"), "market_cap")["comparisons"][0]["value"] == 100000 * 10**7


def test_fact8_surveillance(stock):
    s = by_id(stock("SHIVAGRO")["facts"], "surveillance")
    assert fig(s, "surveillance_status")["value"] == "ASM long-term stage II since 14 Aug 2026"
    assert s["termId"] == "surveillance_asm"
    t = by_id(stock("TCS")["facts"], "surveillance")
    assert fig(t, "surveillance_status")["value"] == "Not on ASM, GSM or ESM lists"
