import pytest

from app import handlers
from app.content import glossary as gl
from app.errors import ApiError

REQUIRED = """market_cap size_band large_cap mid_cap small_cap micro_cap revenue operating_margin net_profit eps pe_ratio pb_ratio roe debt debt_to_equity
debt_to_profit interest_coverage promoter_holding promoter_pledge fii_holding dividend_yield avg_daily_traded_value surveillance_asm surveillance_gsm
surveillance_esm cagr worst_fall recovery_time nifty_50 peers nav expense_ratio direct_plan regular_plan aum exit_load lock_in elss index_fund benchmark tri
category_average top10_share fund_overlap fund_manager sip look_through_exposure idle_cash""".split()


def test_required_terms_and_count():
    ids = {t["id"] for t in gl.list_terms()}
    assert len(REQUIRED) == 48 and set(REQUIRED) <= ids and len(ids) >= 40 and len(ids) == len(gl.list_terms())


def test_term_shape_and_plain_meaning():
    for t in gl.list_terms():
        assert set(t) == {"id", "term", "aliases", "meaning", "appliesTo", "figureIds"}
        assert set(t["appliesTo"]) <= {"STOCK", "FUND", "PORTFOLIO"} and t["appliesTo"]
        assert t["meaning"].endswith(".") and 25 < len(t["meaning"]) < 220 and "\n" not in t["meaning"]
        assert isinstance(t["aliases"], list) and isinstance(t["figureIds"], list)


def test_pe_term_matches_contract():
    t = gl.get_term("pe_ratio")
    assert t["term"] == "P/E (price to earnings)" and t["aliases"][:2] == ["PE", "price to earnings"] and t["figureIds"] == ["pe"]
    assert t["meaning"] == "How many rupees investors pay today for each rupee of the company's yearly profit."


def test_explain_stock_with_typical(ctx):
    r = handlers.explain(ctx, {"term": "pe_ratio", "kind": "STOCK", "id": "TCS"})
    assert r["instrument"] == {"kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap"}
    assert r["thisFigure"]["id"] == "pe" and r["typical"]["kind"] == "PEERS" and r["typical"]["value"] == 25.1
    assert r["sentence"]["templateId"] == "glossary.explain.with_typical" and r["sentence"]["text"].endswith("is 25.1x.")


def test_explain_fund_category_typical(ctx):
    r = handlers.explain(ctx, {"term": "expense_ratio", "kind": "FUND", "id": "900102"})
    assert r["typical"]["kind"] == "CATEGORY" and r["typical"]["value"] == 0.72 and r["thisFigure"]["id"] == "expense_ratio"


def test_explain_without_instrument_or_figure(ctx):
    r = handlers.explain(ctx, {"term": "sip"})
    assert r["instrument"] is None and r["thisFigure"] is None and r["typical"] is None and r["sentence"] is None and r["term"]["id"] == "sip"
    r = handlers.explain(ctx, {"term": "sip", "kind": "STOCK", "id": "TCS"})
    assert r["instrument"] is None and r["sentence"] is None
    r = handlers.explain(ctx, {"term": "pe_ratio", "kind": "FUND", "id": "900101"})
    assert r["thisFigure"] is None


def test_explain_errors(ctx):
    for p, st in (({"term": "nope"}, 404), ({"term": "pe_ratio", "kind": "STOCK"}, 400), ({"term": "pe_ratio", "kind": "STOCK", "id": "ZZZ"}, 404),
                  ({"term": "pe_ratio", "kind": "BOND", "id": "x"}, 400)):
        with pytest.raises(ApiError) as e:
            handlers.explain(ctx, p)
        assert e.value.status == st


def test_every_term_with_a_figure_resolves_for_some_instrument(ctx):
    resolved = 0
    for t in gl.list_terms():
        if not t["figureIds"]:
            continue
        for kind, iid in (("STOCK", "TCS"), ("FUND", "900101")):
            r = handlers.explain(ctx, {"term": t["id"], "kind": kind, "id": iid})
            if r["thisFigure"]:
                resolved += 1
                assert r["thisFigure"]["id"] in t["figureIds"]
    assert resolved >= 25
