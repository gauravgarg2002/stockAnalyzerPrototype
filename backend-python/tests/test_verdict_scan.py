import re

import pytest

from app import verdict_scan as vs
from app.content import glossary as gl
from app.context import content_categories
from app.adapters import sample_store as ss
from app import handlers
from app.narrative.templates import TEMPLATES
from conftest import ALL_FUNDS, ALL_STOCKS, SAMPLE_FUND_OVERLAPS

BAD = ["buy", "Buys", "buying", "SELL", "selling", "avoid", "avoided", "overvalued", "undervalued", "cheap", "expensive", "good", "bad",
       "recommend", "recommended", "recommendation", "should", "target price", "target  prices"]
OK = ["buyback", "goods", "shoulder", "badge", "sold", "sell-off".replace("sell-off", "fall"), "bad loans".replace("bad loans", "non-performing loans"),
      "lower-cost", "higher-cost", "proposed dividend", "outsell", "forbid"]


@pytest.mark.parametrize("w", BAD)
def test_banned_words_detected(w):
    assert vs.scan(f"This is {w} for you.")


@pytest.mark.parametrize("w", OK)
def test_allowed_words_pass(w):
    assert vs.scan(f"This is {w} for you.") == []


def test_pattern_is_the_contract_regex():
    assert vs.PATTERN.startswith(r"\b(buy|buys|buying|sell|sells|selling|avoid") and vs.PATTERN.endswith(r"target\s+prices?)\b")
    assert vs.BANNED_RE.flags & re.IGNORECASE


def test_names_are_masked():
    assert vs.scan("Good Fund Ltd holds shares.", allow_names=["Good Fund Ltd"]) == []
    assert vs.scan("Good Fund Ltd should hold.", allow_names=["Good Fund Ltd"]) == ["should"]


def assert_clean(strings, names=()):
    bad = [(p, s, vs.scan(s, names)) for p, s in strings if vs.scan(s, names)]
    assert not bad, bad[:5]


def all_names():
    names = [r["name"] for r in ss.stock_records().values()] + [u["name"] for u in ss.universe()] + [r["name"] for r in ss.fund_records().values()]
    names += [r["shortName"] for r in ss.fund_records().values()] + [r["amc"] for r in ss.fund_records().values()]
    for r in ss.stock_records().values():
        names += [m["name"] for m in r["peerGroup"]["members"]] + [s["name"] for s in r["revenueSegments"]]
    for r in ss.fund_records().values():
        names += [m["name"] for m in r["managers"]]
    return names


def test_every_template_text():
    strings = [(tid, re.sub(r"\{[^}]*\}", "X", text)) for tid, (text, _) in TEMPLATES.items()]
    assert len(strings) > 100
    assert_clean(strings)


def test_glossary_entries():
    strings = []
    for t in gl.list_terms():
        strings += [(t["id"], t["term"]), (t["id"], t["meaning"])] + [(t["id"], a) for a in t["aliases"]]
    assert_clean(strings)


def test_category_text():
    strings = [(k, v["mayHold"]) for k, v in ss.categories().items()] + [(k, v["mayHold"]) for k, v in content_categories().items()]
    assert_clean(strings + [(k, k) for k in ss.categories()])


def test_stock_about_and_data_text():
    strings = []
    for r in ss.stock_records().values():
        strings += [(r["symbol"], r["name"] + " " + r["about"]), (r["symbol"], r["industry"]), (r["symbol"], r["peerGroup"]["name"])]
        strings += [(r["symbol"], e["text"]) for e in r["events"]]
    for r in ss.fund_records().values():
        strings += [(r["schemeCode"], e["text"]) for e in r["events"]] + [(r["schemeCode"], r["exitLoad"]["text"])]
    assert_clean(strings, all_names())


@pytest.mark.parametrize("sym", ALL_STOCKS)
def test_full_stock_check_output(stock, sym):
    assert_clean(list(vs.walk_strings(stock(sym))), all_names())


@pytest.mark.parametrize("code", ALL_FUNDS)
def test_full_fund_check_output(fund, code):
    assert_clean(list(vs.walk_strings(fund(code, user_funds=SAMPLE_FUND_OVERLAPS))), all_names())
    assert_clean(list(vs.walk_strings(fund(code))), all_names())


def test_compare_output(ctx):
    assert_clean(list(vs.walk_strings(handlers.compare(ctx, {"kind": "STOCK", "ids": "TCS,INFY,HDFCBANK"}))), all_names())
    assert_clean(list(vs.walk_strings(handlers.compare(ctx, {"kind": "FUND", "ids": "900101,900201,900801", "amountInr": "100000"}))), all_names())


def dummy(unit):
    return {"INR": 1234567.0, "PCT": 12.3, "PCT_CHANGE": -4.5, "TIMES": 3.2, "COUNT": 2, "TEXT": "Sample Name", "YEARS": 3.5, "DAYS": 40, "INR_PRICE": 100.5, "MONTHS": 2}[unit]


def test_narrate_every_template_rendered(ctx):
    items = [{"key": tid, "templateId": tid, "facts": {k: {"value": dummy(u), "unit": u} for k, u in units.items()}} for tid, (_, units) in TEMPLATES.items()]
    out = handlers.narrate(ctx, {"body": {"items": items}})
    assert len(out["items"]) == len(TEMPLATES)
    assert_clean([(i["key"], i["sentence"]["text"]) for i in out["items"]], ["Sample Name"])


def test_explain_every_term(ctx):
    strings = []
    for t in gl.list_terms():
        for kind, iid in (("STOCK", "TCS"), ("FUND", "900101"), ("STOCK", "HDFCBANK")):
            strings += list(vs.walk_strings(handlers.explain(ctx, {"term": t["id"], "kind": kind, "id": iid})))
        strings += list(vs.walk_strings(handlers.explain(ctx, {"term": t["id"]})))
    assert_clean(strings, all_names())
