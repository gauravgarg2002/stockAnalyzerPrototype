"""Glossary lookup and the 'Explain this' payload (contract B.6, B.7)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ..narrative.render import S

PATH = Path(__file__).resolve().parent / "glossary.json"


@lru_cache(maxsize=1)
def list_terms() -> list[dict]:
    return json.loads(PATH.read_text(encoding="utf-8"))["terms"]


def get_term(term_id: str) -> Optional[dict]:
    return next((t for t in list_terms() if t["id"] == term_id), None)


def iter_figures(check: dict):
    inst = check.get("instrument", {})
    for k in ("lastPrice", "marketCap", "nav"):
        if isinstance(inst.get(k), dict):
            yield inst[k]
    for block in list(check.get("answers", [])) + list(check.get("facts", [])):
        yield from block.get("figures", [])
    dd = check.get("drawdown")
    if dd:
        yield dd["worstFall"]


def explain(term: dict, check: Optional[dict], instrument_ref: Optional[dict], kind: Optional[str]) -> dict:
    """Builds the explain payload parts for a term given an already-built check payload (or None)."""
    figure = None
    if check is not None:
        for fig in iter_figures(check):
            if fig["id"] in term["figureIds"] and fig["value"] is not None:
                figure = fig
                break
    if figure is None:
        return {"term": term, "instrument": None, "thisFigure": None, "typical": None, "sentence": None}
    want = "PEERS" if kind == "STOCK" else "CATEGORY"
    typical = next((c for c in figure["comparisons"] if c["kind"] == want and c["value"] is not None), None)
    name = instrument_ref["name"]
    if typical:
        label = typical["label"]
        lab = "the " + label[0].lower() + label[1:]
        sent = S("glossary.explain.with_typical", instrumentName=(name, "TEXT"), thisFigure=(figure["display"], "TEXT"), typicalLabel=(lab, "TEXT"), typical=(typical["display"], "TEXT"))
    else:
        sent = S("glossary.explain.no_typical", instrumentName=(name, "TEXT"), thisFigure=(figure["display"], "TEXT"))
    return {"term": term, "instrument": instrument_ref, "thisFigure": figure, "typical": typical, "sentence": sent}
