"""Shared HTTP helpers for live adapters: Session factory, RateLimiter, DiskCache.

Importing this module performs no network I/O.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

import requests

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = (5.0, 20.0)  # connect, read


def make_session(user_agent: str = BROWSER_UA, headers: dict[str, str] | None = None) -> requests.Session:
    """requests.Session with a browser-like User-Agent. Callers pass timeout=DEFAULT_TIMEOUT per request."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/json,text/csv,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    })
    if headers:
        s.headers.update(headers)
    return s


class RateLimiter:
    """Blocks so that successive wait() calls are at least min_interval_seconds apart (thread-safe)."""

    def __init__(self, min_interval_seconds: float, clock=time.monotonic, sleep=time.sleep):
        self.min_interval = max(0.0, float(min_interval_seconds))
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> float:
        """Sleep as needed, record the call time, and return the seconds slept."""
        with self._lock:
            slept = 0.0
            now = self._clock()
            if self._last is not None:
                remaining = self.min_interval - (now - self._last)
                if remaining > 0:
                    self._sleep(remaining)
                    slept = remaining
            self._last = self._clock()
            return slept


class DiskCache:
    """Tiny JSON-or-text file cache with a TTL in hours. Keys are hashed into file names."""

    def __init__(self, directory: str | Path, ttl_hours: float, clock=time.time):
        self.dir = Path(directory)
        self.ttl_seconds = float(ttl_hours) * 3600.0
        self._clock = clock

    def _path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]
        return self.dir / f"{h}.json"

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        try:
            with p.open("r", encoding="utf-8") as f:
                rec = json.load(f)
            if self._clock() - float(rec["t"]) > self.ttl_seconds:
                return None
            return rec["v"]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            p = self._path(key)
            tmp = p.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump({"k": key, "t": self._clock(), "v": value}, f)
            tmp.replace(p)
        except (OSError, TypeError, ValueError):
            pass  # cache failures never break a request
