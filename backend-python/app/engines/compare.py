"""Rows of answers across 2-3 instruments (contract B.5)."""
from __future__ import annotations


def build_compare(kind: str, as_of: str, sample: bool, instruments: list[dict], checks: list[dict]) -> dict:
    """instruments: InstrumentRef+checkPath dicts; checks: stock/fund check payloads in the same order."""
    rows = []
    for i, ans in enumerate(checks[0]["answers"]):
        cells = []
        for inst, chk in zip(instruments, checks):
            a = chk["answers"][i]
            cells.append({"instrumentId": inst["id"], "sentences": a["sentences"], "figures": a["figures"]})
        rows.append({"id": ans["id"], "order": ans["order"], "question": ans["question"], "cells": cells})
    return {"sampleData": sample, "asOf": as_of, "kind": kind, "instruments": instruments, "rows": rows}
