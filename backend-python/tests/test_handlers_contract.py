"""Every handler output validates against the extra=forbid models (all nullable fields present)."""
import pytest

from app import handlers, models
from app.adapters import sample_store as ss
from app.content import glossary as gl
from app.sources import ALL_LABELS
from app.verdict_scan import walk_strings
from conftest import ALL_FUNDS, ALL_STOCKS, SAMPLE_FUND_OVERLAPS

STOCK_KEYS = {"sampleData", "asOf", "instrument", "answers", "facts", "priceHistory", "drawdown", "peers"}
FUND_KEYS = {"sampleData", "asOf", "instrument", "amount", "answers", "facts", "priceHistory", "drawdown"}


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_stock_check_models(stock, sym):
    c = stock(sym)
    models.StockCheck.model_validate(c)
    assert set(c) == STOCK_KEYS and c["sampleData"] is True


@pytest.mark.parametrize("code", ALL_FUNDS)
def test_fund_check_models(fund, code):
    c = fund(code, user_funds=SAMPLE_FUND_OVERLAPS)
    models.FundCheck.model_validate(c)
    assert set(c) == FUND_KEYS and c["sampleData"] is True
    models.FundCheck.model_validate(fund(code))


def test_figure_sources_and_sentence_generators(stock, fund):
    for c in [stock(s) for s in ALL_STOCKS] + [fund(f, user_funds=SAMPLE_FUND_OVERLAPS) for f in ALL_FUNDS]:
        def visit(o):
            if isinstance(o, dict):
                if {"id", "label", "value", "unit", "display", "source", "asOf", "comparisons", "termId"} == set(o):
                    assert o["source"] in ALL_LABELS and o["asOf"][:2] == "20"
                    for cmp in o["comparisons"]:
                        assert set(cmp) == {"kind", "label", "value", "unit", "display"}
                if {"text", "templateId", "generator"} == set(o):
                    assert o["generator"] == "template" and o["text"].strip()
                for v in o.values():
                    visit(v)
            elif isinstance(o, list):
                for v in o:
                    visit(v)
        visit(c)


def test_term_ids_in_checks_exist_in_glossary(stock, fund):
    ids = {t["id"] for t in gl.list_terms()}
    for c in [stock(s) for s in ALL_STOCKS] + [fund(f) for f in ALL_FUNDS]:
        def visit(o):
            if isinstance(o, dict):
                if "termId" in o and o["termId"] is not None:
                    assert o["termId"] in ids, o["termId"]
                for v in o.values():
                    visit(v)
            elif isinstance(o, list):
                for v in o:
                    visit(v)
        visit(c)


def test_health_search_glossary_explain_models(ctx):
    h = handlers.health(ctx, {})
    models.Health.model_validate(h)
    assert h["adapters"] == {"broker": "mock", "fundamentals": "mock", "prices": "mock", "surveillance": "mock", "fundNav": "mock", "fundMeta": "mock",
                             "fundHoldings": "mock", "statement": "auto"} and h["llmEnabled"] is False and h["sampleData"] is True
    models.SearchResponse.model_validate(handlers.search(ctx, {"q": "tata"}))
    models.Glossary.model_validate(handlers.glossary(ctx, {}))
    for term in ("pe_ratio", "nav", "sip"):
        for extra in ({}, {"kind": "STOCK", "id": "TCS"}, {"kind": "FUND", "id": "900101"}):
            models.Explain.model_validate(handlers.explain(ctx, {"term": term, **extra}))


def test_compare_bundle_points_models(ctx):
    models.Compare.model_validate(handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,INFY,ITC"}))
    models.Compare.model_validate(handlers.compare(ctx, {"kind": "FUND", "ids": "900101,900301", "amountInr": "50000"}))
    models.Bundle.model_validate(handlers.bundle(ctx, {"body": {"stocks": ["TCS", "NOPE"], "funds": ALL_FUNDS}}))
    models.Bundle.model_validate(handlers.bundle(ctx, {"body": {}}))
    pts = handlers.prices_points(ctx, {"body": {"items": [
        {"kind": "STOCK", "id": "TCS", "dates": ["2025-10-30", "2023-06-05", "2026-10-30", "2020-01-01"]},
        {"kind": "INDEX", "id": "NIFTY50", "dates": ["2025-10-30"]}, {"kind": "FUND", "id": "900101", "dates": ["2026-10-31"]},
        {"kind": "STOCK", "id": "UNKNOWN", "dates": ["2025-10-30"]}]}})
    models.Points.model_validate(pts)
    vals = pts["items"][0]["values"]
    assert vals[0]["date"] == "2025-10-30" and vals[3] == {"requestedDate": "2020-01-01", "date": None, "value": None}
    assert vals[2]["value"] == 3925.4
    assert pts["items"][2]["values"][0]["date"] == "2026-10-30"  # weekend date -> last business day
    assert pts["items"][3]["values"][0] == {"requestedDate": "2025-10-30", "date": None, "value": None}


def test_broker_and_narrate_models(ctx):
    models.BrokerStatus.model_validate(handlers.broker_login_status(ctx, {}))
    models.BrokerStart.model_validate(handlers.broker_login_start(ctx, {}))
    models.BrokerStatus.model_validate(handlers.broker_login_status(ctx, {}))
    models.BrokerPortfolioOut.model_validate(handlers.broker_portfolio(ctx, {}))
    models.BrokerStart.model_validate(handlers.broker_logout(ctx, {}))
    handlers.broker_login_start(ctx, {})
    out = handlers.narrate(ctx, {"body": {"items": [{"key": "k", "templateId": "pf.summary.empty", "facts": {}}]}})
    models.NarrateOut.model_validate(out)


def test_models_reject_extra_fields(stock):
    bad = dict(stock("TCS"))
    bad["surprise"] = 1
    with pytest.raises(Exception):
        models.StockCheck.model_validate(bad)


def test_statement_parse_bad_input_is_422_or_400(ctx):
    from app.errors import ApiError
    with pytest.raises(ApiError) as e:
        handlers.statements_parse(ctx, {"body": {"filename": "x.pdf", "fileBase64": "", "password": "x"}})
    assert e.value.status == 400
    import base64
    with pytest.raises(ApiError) as e:
        handlers.statements_parse(ctx, {"body": {"filename": "x.pdf", "fileBase64": base64.b64encode(b"not a pdf").decode(), "password": "x"}})
    assert e.value.status == 422 and e.value.code == "STATEMENT_UNREADABLE"


def test_fund_check_bad_requests(ctx):
    from app.errors import ApiError
    for body in ({}, {"amountInr": 0}, {"amountInr": "abc"}, {"amountInr": 5, "amountBasis": "WHAT"}, {"amountInr": 5, "userFunds": [{"x": 1}]}, "str"):
        with pytest.raises(ApiError) as e:
            handlers.fund_check(ctx, {"schemeCode": "900101", "body": body})
        assert e.value.status == 400
    with pytest.raises(ApiError) as e:
        handlers.fund_check(ctx, {"schemeCode": "123456", "body": {"amountInr": 1000}})
    assert e.value.status == 404 and e.value.details == {"schemeCode": "123456"}
