"""/internal/narrate logic: render templates; optional LLM rewrite with strict validation and template fallback."""
from __future__ import annotations

import re
from typing import Any

from ..errors import bad_request
from ..verdict_scan import scan
from .render import TemplateError, display_facts, render_text, sentence

NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def number_tokens(text: str) -> set[str]:
    return {t.replace(",", "").rstrip(".") for t in NUM_RE.findall(text)}


def validate_llm_output(out: str, template_sentence: str, text_values: list[str]) -> bool:
    """True if out is safe to show: no banned word, no unseen number, not longer than 2x the template."""
    if not out or not out.strip():
        return False
    if scan(out, text_values):
        return False
    if not number_tokens(out) <= number_tokens(template_sentence):
        return False
    return len(out) <= 2 * len(template_sentence)


def narrate(body: Any, provider) -> dict:
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise bad_request("Body must contain an 'items' list.", {"key": None, "missing": ["items"]})
    use_llm = bool(body.get("useLlm")) and provider is not None
    out = []
    for item in body["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not isinstance(item.get("templateId"), str):
            raise bad_request("Each item needs 'key' and 'templateId'.", {"key": item.get("key") if isinstance(item, dict) else None, "missing": ["key", "templateId"]})
        key, tid = item["key"], item["templateId"]
        facts = item.get("facts") or {}
        try:
            disp = display_facts(tid, facts)
            text = render_text(tid, facts)
        except TemplateError as e:
            missing = ["templateId"] if e.unknown_template else e.missing
            raise bad_request(str(e), {"key": key, "missing": missing})
        sent = sentence(tid, facts, "template", text)
        if use_llm:
            shown = {k: v for k, v in disp.items() if not k.endswith("__raw")}
            try:
                cand = provider.rewrite(text, shown)
            except Exception:
                cand = None
            if cand:
                texts = [str(v) for k, v in disp.items() if k.endswith("__raw") and isinstance(v, str)]
                if validate_llm_output(cand.strip(), text, texts):
                    sent = sentence(tid, facts, "llm", cand.strip())
        out.append({"key": key, "sentence": sent})
    return {"sampleData": False, "items": out}
