"""Optional LLM rewriting. Providers: none | anthropic | openai (via requests).

The model only ever sees the already-rendered template sentence and the display strings of its facts.
Output is validated by narrate.validate_llm_output; any failure falls back to the template.
No keys live in code: they come from config llm.apiKey.
"""
from __future__ import annotations

from typing import Optional

import requests

SYSTEM = (
    "You rewrite one sentence for a beginner investor in India, in plain, friendly words. "
    "Use only the facts provided. Keep every number exactly as written. Do not add any number, advice, opinion, "
    "prediction or judgement. Do not use the words buy, sell, avoid, good, bad, cheap, expensive, overvalued, "
    "undervalued, recommend, should. Reply with the rewritten sentence only."
)


def build_prompt(sentence: str, facts: dict[str, str]) -> str:
    lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    return f"Sentence:\n{sentence}\n\nFacts:\n{lines}\n\nRewrite the sentence in plain words, keeping all facts."


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str, timeout: float):
        self.model, self.api_key, self.timeout = model, api_key, timeout

    def rewrite(self, sentence: str, facts: dict[str, str]) -> Optional[str]:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=self.timeout,
                          headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": self.model, "max_tokens": 200, "system": SYSTEM, "messages": [{"role": "user", "content": build_prompt(sentence, facts)}]})
        r.raise_for_status()
        parts = r.json().get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip() or None


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str, api_key: str, timeout: float):
        self.model, self.api_key, self.timeout = model, api_key, timeout

    def rewrite(self, sentence: str, facts: dict[str, str]) -> Optional[str]:
        r = requests.post("https://api.openai.com/v1/chat/completions", timeout=self.timeout,
                          headers={"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"},
                          json={"model": self.model, "max_tokens": 200,
                                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_prompt(sentence, facts)}]})
        r.raise_for_status()
        ch = r.json().get("choices", [])
        return (ch[0]["message"]["content"].strip() or None) if ch else None


def get_provider(config: dict):
    """Provider instance, or None when provider is 'none' or not fully configured."""
    c = config.get("llm", {})
    prov = (c.get("provider") or "none").lower()
    if prov == "none" or not c.get("apiKey") or not c.get("model"):
        return None
    timeout = float(c.get("timeoutSeconds", 20))
    if prov == "anthropic":
        return AnthropicProvider(c["model"], c["apiKey"], timeout)
    if prov == "openai":
        return OpenAIProvider(c["model"], c["apiKey"], timeout)
    return None
