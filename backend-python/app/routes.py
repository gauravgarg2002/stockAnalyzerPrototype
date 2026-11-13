"""ROUTES: the single table both web wrappers (FastAPI, Starlette) are built from."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import handlers as h


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: Callable
    kind: str  # "query": params = path + query string; "json_body": params = path + {"body": parsed JSON}


ROUTES: list[Route] = [
    Route("GET", "/internal/health", h.health, "query"),
    Route("GET", "/internal/search", h.search, "query"),
    Route("GET", "/internal/stocks/{symbol}/check", h.stock_check, "query"),
    Route("POST", "/internal/funds/{schemeCode}/check", h.fund_check, "json_body"),
    Route("GET", "/internal/compare", h.compare, "query"),
    Route("GET", "/internal/glossary", h.glossary, "query"),
    Route("GET", "/internal/explain", h.explain, "query"),
    Route("POST", "/internal/instruments/bundle", h.bundle, "json_body"),
    Route("POST", "/internal/prices/points", h.prices_points, "json_body"),
    Route("POST", "/internal/broker/login/start", h.broker_login_start, "query"),
    Route("GET", "/internal/broker/login/status", h.broker_login_status, "query"),
    Route("POST", "/internal/broker/login/complete", h.broker_login_complete, "json_body"),
    Route("POST", "/internal/broker/logout", h.broker_logout, "query"),
    Route("GET", "/internal/broker/portfolio", h.broker_portfolio, "query"),
    Route("POST", "/internal/statements/parse", h.statements_parse, "json_body"),
    Route("POST", "/internal/narrate", h.narrate, "json_body"),
]
