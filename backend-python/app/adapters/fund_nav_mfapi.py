"""Fund NAV adapter: mfapi.in (JSON: meta + data[{date: dd-mm-yyyy, nav}], newest first). Cached."""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import requests

from .base import NavSeries
from .http_util import DEFAULT_TIMEOUT, DiskCache, make_session, unavailable

SOURCE = "AMFI"


def parse_mfapi(obj: Any) -> list[tuple[date, float]]:
    """{'meta': {...}, 'data': [{'date': '30-10-2026', 'nav': '62.4012'}, ...]} -> ascending [(date, nav)].
    Rows with an unparsable date or a non-positive NAV are dropped. Verified only against the documented shape."""
    rows = obj.get("data") if isinstance(obj, dict) else None
    out: dict[date, float] = {}
    for r in rows or []:
        try:
            d0 = datetime.strptime(str(r["date"]).strip(), "%d-%m-%Y").date()
            v = float(str(r["nav"]).replace(",", ""))
        except (KeyError, ValueError, TypeError):
            continue
        if v > 0:
            out[d0] = v
    return [(k, out[k]) for k in sorted(out)]


class MfapiNav:
    mode = "mfapi"

    def __init__(self, config: dict, session: requests.Session | None = None):
        self._base = str((config.get("mfapi", {}) or {}).get("baseUrl") or "https://api.mfapi.in").rstrip("/")
        c = config.get("cache", {}) or {}
        root = Path(str(c.get("dir") or ".cache"))
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        self._cache = DiskCache(root / "mfapi", float(c.get("fundDataHours", 24)))
        self._session = session or make_session()

    def nav_series(self, scheme_code: str) -> Optional[NavSeries]:
        code = str(scheme_code or "").strip()
        if not re.fullmatch(r"\d{3,8}", code):
            return None
        cached = self._cache.get(f"nav:{code}")
        if cached is not None:
            pts = [(date.fromisoformat(a), float(b)) for a, b in cached]
        else:
            try:
                r = self._session.get(f"{self._base}/mf/{code}", timeout=DEFAULT_TIMEOUT)
            except requests.RequestException as e:
                raise unavailable("Fund price history could not be reached. Please try again in a moment.",
                                  reason=type(e).__name__)
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                raise unavailable("Fund price history returned an error.", httpStatus=r.status_code)
            try:
                pts = parse_mfapi(r.json())
            except ValueError:
                raise unavailable("Fund price history was in an unexpected format.")
            if not pts:
                return None
            self._cache.set(f"nav:{code}", [[d.isoformat(), v] for d, v in pts])
        if not pts:
            return None
        return NavSeries(code, pts, SOURCE, pts[-1][0].isoformat())


def build(config: dict, deps: dict) -> MfapiNav:
    return MfapiNav(config)
