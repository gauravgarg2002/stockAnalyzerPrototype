"""Render templates into Sentence dicts (contract 0.5)."""
from __future__ import annotations

import re
from typing import Any, Optional

from ..formatting import format_count, format_unit
from .templates import TEMPLATES

PLACEHOLDER = re.compile(r"\{(\w+)(?:\|([^|}]*)\|([^}]*))?\}")


class TemplateError(Exception):
    def __init__(self, message: str, missing: Optional[list[str]] = None, unknown_template: bool = False):
        super().__init__(message)
        self.missing = missing or []
        self.unknown_template = unknown_template


def _unpack(v: Any) -> tuple[Any, Optional[str]]:
    if isinstance(v, dict):
        return v.get("value"), v.get("unit")
    if isinstance(v, (tuple, list)) and len(v) == 2:
        return v[0], v[1]
    raise TemplateError("bad fact")


def display_facts(template_id: str, facts: dict) -> dict[str, str]:
    """Validated display strings for each fact key the template uses (extra keys ignored)."""
    if template_id not in TEMPLATES:
        raise TemplateError(f"Unknown template {template_id}", unknown_template=True)
    _, units = TEMPLATES[template_id]
    missing, out = [], {}
    for key, unit in units.items():
        if key not in facts:
            missing.append(key)
            continue
        try:
            value, u = _unpack(facts[key])
        except TemplateError:
            missing.append(key)
            continue
        if u != unit or (value is None and unit != "TEXT") or (unit == "TEXT" and not isinstance(value, str)):
            missing.append(key)
            continue
        out[key] = format_unit(value, unit)
        out[key + "__raw"] = value
    if missing:
        raise TemplateError(f"Missing or invalid facts for {template_id}: {', '.join(missing)}", missing)
    return out


def render_text(template_id: str, facts: dict) -> str:
    disp = display_facts(template_id, facts)
    text = TEMPLATES[template_id][0]

    def sub(m: re.Match) -> str:
        key, one, many = m.group(1), m.group(2), m.group(3)
        if one is None:
            return disp[key]
        n = disp[key + "__raw"]
        return f"{format_count(n)} {one if float(n) == 1 else many}"

    return PLACEHOLDER.sub(sub, text)


def sentence(template_id: str, facts: dict, generator: str = "template", text: Optional[str] = None) -> dict:
    return {"text": text if text is not None else render_text(template_id, facts), "templateId": template_id, "generator": generator}


def S(template_id: str, **facts: Any) -> dict:
    """Shorthand used by the engines: facts are (value, unit) tuples."""
    return sentence(template_id, facts)
