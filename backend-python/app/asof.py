"""Today's date: sample date when any adapter is mock, else the date in Asia/Kolkata."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import config as cfgmod


def _ist_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:  # tzdata missing
        return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def today(config: dict) -> date:
    if cfgmod.any_mock(config):
        return date.fromisoformat(config["app"]["sampleAsOf"])
    return _ist_now().date()


def now_iso() -> str:
    return _ist_now().replace(microsecond=0).isoformat()
