"""Banned verdict-word scan (contract 0.6)."""
from __future__ import annotations

import re
from typing import Iterable

PATTERN = (
    r"\b(buy|buys|buying|sell|sells|selling|avoid|avoids|avoided|avoiding|overvalued|undervalued|cheap|expensive|"
    r"good|bad|recommend|recommends|recommended|recommending|recommendation|recommendations|should|target\s+prices?)\b"
)
BANNED_RE = re.compile(PATTERN, re.IGNORECASE)


def mask_names(text: str, names: Iterable[str] = ()) -> str:
    """Replace each known name (longest first) with NAME."""
    for n in sorted({n for n in names if n}, key=len, reverse=True):
        text = text.replace(n, "NAME")
    return text


def scan(text: str, allow_names: Iterable[str] = ()) -> list[str]:
    """Return banned words found in text after masking names."""
    return [m.group(0) for m in BANNED_RE.finditer(mask_names(text, allow_names))]


def walk_strings(obj, path: str = "$"):
    """Yield (path, string) for every string in a nested JSON-like structure."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
