"""Peer / category median helpers."""
from __future__ import annotations

from typing import Optional

from ..adapters.base import StockFundamentals
from .figures import comparison


def peer_label(f: StockFundamentals) -> str:
    return f"Median of {f.peerGroup.get('name', 'its')} peers"


def peer_median(f: StockFundamentals, key: str) -> Optional[float]:
    return (f.peerGroup.get("medians") or {}).get(key)


def peer_comparison(f: StockFundamentals, key: str, unit: str) -> dict:
    return comparison("PEERS", peer_label(f), peer_median(f, key), unit)


def category_median(cat: Optional[dict], key: str) -> Optional[float]:
    return ((cat or {}).get("medians") or {}).get(key)
