import pytest

from app import handlers
from app.errors import ApiError
from app.narrative import llm, narrate as nr
from app.narrative.templates import TEMPLATES


def item(key, tid, **facts):
    return {"key": key, "templateId": tid, "facts": {k: {"value": v[0], "unit": v[1]} for k, v in facts.items()}}


VALUE = item("summary.0", "pf.summary.value", totalValueInr=(1277410, "INR"), stockCount=(6, "COUNT"), fundCount=(4, "COUNT"))
OVERLAP = item("fact.overlap", "pf.fact.overlap", fundA=("Kaveri Flexi Cap Fund - Regular Plan - Growth", "TEXT"), fundB=("Narmada Nifty 50 Index Fund - Direct Plan - Growth", "TEXT"),
               overlapPct=(41.37, "PCT"), commonCount=(27, "COUNT"))


class Fake:
    def __init__(self, reply=None, boom=False):
        self.reply, self.boom, self.seen = reply, boom, None

    def rewrite(self, sentence, facts):
        self.seen = (sentence, facts)
        if self.boom:
            raise TimeoutError("slow")
        return self.reply


def run(ctx, items, use_llm=False, provider=None):
    ctx.llm_provider_override = provider
    try:
        return handlers.narrate(ctx, {"body": {"items": items, "useLlm": use_llm}})
    finally:
        ctx.llm_provider_override = None


def test_contract_examples_render(ctx):
    out = run(ctx, [VALUE, OVERLAP])
    assert out["sampleData"] is False
    assert [i["key"] for i in out["items"]] == ["summary.0", "fact.overlap"]
    assert out["items"][0]["sentence"] == {"text": "Your holdings are worth ₹12.8 lakh across 6 stocks and 4 mutual funds.", "templateId": "pf.summary.value", "generator": "template"}
    assert out["items"][1]["sentence"]["text"] == ("Kaveri Flexi Cap Fund - Regular Plan - Growth and Narmada Nifty 50 Index Fund - Direct Plan - Growth hold 27 companies "
                                                  "in common, adding up to an overlap of 41.4%.")


def test_plural_rule(ctx):
    one = item("a", "pf.summary.value", totalValueInr=(5000, "INR"), stockCount=(1, "COUNT"), fundCount=(1, "COUNT"))
    assert run(ctx, [one])["items"][0]["sentence"]["text"] == "Your holdings are worth ₹5,000 across 1 stock and 1 mutual fund."


def test_templates_without_facts_and_extra_keys_ignored(ctx):
    e = {"key": "x", "templateId": "pf.summary.empty", "facts": {"junk": {"value": 1, "unit": "COUNT"}}}
    assert "have not added any holdings" in run(ctx, [e])["items"][0]["sentence"]["text"]


@pytest.mark.parametrize("bad,missing", [
    ({"key": "k1", "templateId": "nope.nothing", "facts": {}}, ["templateId"]),
    ({"key": "k2", "templateId": "pf.summary.value", "facts": {"totalValueInr": {"value": 1, "unit": "INR"}}}, ["stockCount", "fundCount"]),
    ({"key": "k3", "templateId": "pf.summary.value", "facts": {"totalValueInr": {"value": 1, "unit": "PCT"}, "stockCount": {"value": 1, "unit": "COUNT"}, "fundCount": {"value": 1, "unit": "COUNT"}}}, ["totalValueInr"]),
])
def test_bad_requests(ctx, bad, missing):
    with pytest.raises(ApiError) as e:
        run(ctx, [VALUE, bad])
    assert e.value.status == 400 and e.value.code == "BAD_REQUEST"
    assert e.value.details["key"] == bad["key"] and e.value.details["missing"] == missing


def test_malformed_bodies(ctx):
    for body in (None, {}, {"items": "x"}, {"items": [{"key": 1}]}):
        with pytest.raises(ApiError) as e:
            handlers.narrate(ctx, {"body": body})
        assert e.value.status == 400


def test_llm_accepted_when_clean(ctx):
    p = Fake("You hold ₹12.8 lakh across 6 stocks and 4 mutual funds.")
    out = run(ctx, [VALUE], True, p)
    s = out["items"][0]["sentence"]
    assert s["generator"] == "llm" and s["text"].startswith("You hold") and s["templateId"] == "pf.summary.value"
    assert p.seen[0].startswith("Your holdings are worth") and "totalValueInr" in p.seen[1]


@pytest.mark.parametrize("reply", [
    "You should keep ₹12.8 lakh across 6 stocks and 4 mutual funds.",   # banned word
    "You hold ₹12.8 lakh across 7 stocks and 4 mutual funds.",           # unseen number
    "You hold ₹13 lakh across 6 stocks and 4 mutual funds.",             # unseen number
    "Your holdings are worth ₹12.8 lakh across 6 stocks and 4 mutual funds. " * 3,  # too long
    "", None,
])
def test_llm_falls_back(ctx, reply):
    out = run(ctx, [VALUE], True, Fake(reply))
    assert out["items"][0]["sentence"]["generator"] == "template"
    assert out["items"][0]["sentence"]["text"].startswith("Your holdings are worth")


def test_llm_exception_and_flag_off_and_no_provider(ctx):
    assert run(ctx, [VALUE], True, Fake(boom=True))["items"][0]["sentence"]["generator"] == "template"
    p = Fake("You hold ₹12.8 lakh across 6 stocks and 4 mutual funds.")
    assert run(ctx, [VALUE], False, p)["items"][0]["sentence"]["generator"] == "template" and p.seen is None
    assert run(ctx, [VALUE], True, None)["items"][0]["sentence"]["generator"] == "template"


def test_company_name_containing_banned_word_is_masked_for_llm():
    ok = nr.validate_llm_output("Good Foods Ltd holds 5 companies.", "Good Foods Ltd holds 5 companies.", ["Good Foods Ltd"])
    assert ok
    assert not nr.validate_llm_output("Good news: 5 companies.", "Good Foods Ltd holds 5 companies.", ["Good Foods Ltd"])


def test_provider_none_by_default(ctx):
    assert llm.get_provider(ctx.config) is None and ctx.llm_enabled() is False
    cfg = {"llm": {"provider": "anthropic", "model": "m", "apiKey": "", "timeoutSeconds": 5}}
    assert llm.get_provider(cfg) is None
    cfg["llm"]["apiKey"] = "k"
    assert llm.get_provider(cfg).name == "anthropic"
    cfg["llm"]["provider"] = "openai"
    assert llm.get_provider(cfg).name == "openai"


def test_prompt_contains_only_sentence_and_facts():
    p = llm.build_prompt("Hello ₹5.", {"a": "₹5"})
    assert "Hello ₹5." in p and "- a: ₹5" in p


def test_every_template_has_units_and_renders():
    for tid, (text, units) in TEMPLATES.items():
        import re
        keys = {m.group(1) for m in re.finditer(r"\{(\w+)", text)}
        assert keys == set(units), tid
