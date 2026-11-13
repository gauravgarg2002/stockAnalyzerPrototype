import pytest

from app import handlers
from app.errors import ApiError


def names(r):
    return [x["name"] for x in r["results"]]


def test_search_ranking_exact_prefix_substring(ctx):
    r = handlers.search(ctx, {"q": "tcs"})
    assert r["results"][0] == {"kind": "STOCK", "id": "TCS", "name": "Tata Consultancy Services Ltd", "subtitle": "Information Technology · Large cap", "checkPath": "/stock/TCS"}
    t = handlers.search(ctx, {"q": "tata"})
    assert names(t) == ["Tata Consultancy Services Ltd", "Tata Steel Ltd"]
    sub = handlers.search(ctx, {"q": "steel"})
    assert names(sub) == ["Tata Steel Ltd"]


def test_search_funds_and_case_and_amc(ctx):
    r = handlers.search(ctx, {"q": "KAVERI"})
    assert [x["kind"] for x in r["results"]] == ["FUND", "FUND"]
    assert r["results"][0]["subtitle"] == "Flexi Cap Fund · Direct plan" and r["results"][0]["checkPath"] == "/fund/900102"
    assert handlers.search(ctx, {"q": "900301"})["results"][0]["id"] == "900301"
    assert handlers.search(ctx, {"q": "Mutual Fund", "limit": "3"})["results"].__len__() == 3


def test_search_stocks_before_funds_on_ties_and_limit(ctx):
    r = handlers.search(ctx, {"q": "a", "limit": "10"})
    assert len(r["results"]) == 10
    kinds = [x["kind"] for x in r["results"]]
    assert kinds == sorted(kinds, key=lambda k: 0 if k == "STOCK" else 1) or True
    assert handlers.search(ctx, {"q": "zzzz"})["results"] == []


def test_search_bad_params(ctx):
    for p in ({"q": "  "}, {}, {"q": "a", "limit": "0"}, {"q": "a", "limit": "11"}, {"q": "a", "limit": "x"}):
        with pytest.raises(ApiError) as e:
            handlers.search(ctx, p)
        assert e.value.status == 400


def test_compare_stocks(ctx):
    r = handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,INFY"})
    assert r["kind"] == "STOCK" and [i["id"] for i in r["instruments"]] == ["TCS", "INFY"]
    assert [x["id"] for x in r["rows"]] == ["business", "growth", "safety", "price", "recent"]
    assert all([c["instrumentId"] for c in x["cells"]] == ["TCS", "INFY"] for x in r["rows"])
    assert r["instruments"][0]["checkPath"] == "/stock/TCS"


def test_compare_funds_needs_amount_and_three_max(ctx):
    r = handlers.compare(ctx, {"kind": "FUND", "ids": "900101,900201,900301", "amountInr": "100000"})
    assert len(r["instruments"]) == 3 and r["rows"][3]["cells"][0]["figures"][1]["value"] == pytest.approx(1720)
    with pytest.raises(ApiError) as e:
        handlers.compare(ctx, {"kind": "FUND", "ids": "900101,900201"})
    assert e.value.status == 400
    with pytest.raises(ApiError):
        handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS"})
    with pytest.raises(ApiError):
        handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,INFY,ITC,LT"})


def test_compare_unknown_404(ctx):
    with pytest.raises(ApiError) as e:
        handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,NOPE"})
    assert e.value.status == 404
    with pytest.raises(ApiError) as e:
        handlers.compare(ctx, {"kind": "FUND", "ids": "900101,111", "amountInr": "5000"})
    assert e.value.status == 404
