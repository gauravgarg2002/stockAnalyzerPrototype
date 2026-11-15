"""Read-only guard for every outbound broker call (contract B.10).

Anything not explicitly allow-listed raises ApiError BROKER_FORBIDDEN_CALL (403) BEFORE any network I/O.
"""
from __future__ import annotations

import re

from ..errors import ApiError

# The hosted Kite MCP server exposes a few broad tools that take a `mode`; only these read-only modes may run.
MCP_ALLOWED_CALLS: dict[str, frozenset[str]] = {
    "portfolio": frozenset({"profile", "margins", "holdings", "positions"}),
    "market": frozenset({"quote", "ltp", "ohlc", "historical", "search"}),
    "mutual_funds": frozenset({"holdings"}),
    "orders": frozenset({"list", "history", "trades", "all_trades"}),
    "gtt": frozenset({"list"}),
    "session": frozenset({"status"}),
}
MCP_ALLOWED_TOOLS: frozenset[str] = frozenset(MCP_ALLOWED_CALLS)

# (method, anchored path regex). Paths are matched without query string and without a leading API host.
KITE_CONNECT_ALLOWED: tuple[tuple[str, re.Pattern], ...] = tuple(
    (m, re.compile(p)) for m, p in (
        ("GET", r"/user/profile"),
        ("GET", r"/user/margins(/equity)?"),
        ("GET", r"/portfolio/holdings"),
        ("GET", r"/portfolio/positions"),
        ("GET", r"/mf/holdings"),
        ("GET", r"/quote"),
        ("GET", r"/quote/ltp"),
        ("GET", r"/quote/ohlc"),
        ("GET", r"/instruments(/NSE)?"),
        ("GET", r"/instruments/historical/\d+/(day|minute)"),
        ("GET", r"/orders"),
        ("GET", r"/trades"),
        ("GET", r"/gtt/triggers"),
        ("POST", r"/session/token"),
        ("DELETE", r"/session/token"),
    )
)


def _forbidden(what: str, details: dict) -> ApiError:
    return ApiError(
        "BROKER_FORBIDDEN_CALL",
        "This app only reads your account. It never places, changes or cancels orders, so that call was blocked.",
        {"blocked": what, **details},
    )


def assert_allowed_mcp_tool(name: object, arguments: object = None) -> str:
    """Allow only (tool, mode) pairs on the read-only list. Raises BEFORE any network I/O."""
    modes = MCP_ALLOWED_CALLS.get(name) if isinstance(name, str) else None
    mode = arguments.get("mode") if isinstance(arguments, dict) else None
    if modes is None or not isinstance(mode, str) or mode not in modes:
        raise _forbidden("mcp_tool", {"tool": str(name), "mode": str(mode)})
    return name


def normalize_path(path: str) -> str:
    """Strip scheme/host, query and fragment; collapse '//' ; reject traversal tricks."""
    p = str(path)
    p = re.sub(r"^https?://[^/]+", "", p)
    p = p.split("?", 1)[0].split("#", 1)[0]
    if "%" in p or ".." in p or "\\" in p or ";" in p:
        raise _forbidden("kite_connect", {"path": p})
    p = re.sub(r"/{2,}", "/", p)
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    if not p.startswith("/"):
        p = "/" + p
    return p


def assert_allowed_kite_connect(method: str, path: str) -> tuple[str, str]:
    m = str(method).upper()
    try:
        p = normalize_path(path)
    except ApiError:
        raise
    for am, pat in KITE_CONNECT_ALLOWED:
        if am == m and pat.fullmatch(p):
            return m, p
    raise _forbidden("kite_connect", {"method": m, "path": p})
