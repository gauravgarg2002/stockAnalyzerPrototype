"""AppContext: config + adapter instances built lazily from config (singleton)."""
from __future__ import annotations

import importlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from . import asof, config as cfgmod
from .errors import ApiError

# adapter kind -> {config value -> module name}
MODULES: dict[str, dict[str, str]] = {
    "broker": {"mock": "broker_mock", "kite_mcp": "broker_kite_mcp", "kite_connect": "broker_kite_connect"},
    "fundamentals": {"mock": "fundamentals_mock", "screener": "fundamentals_screener"},
    "prices": {"mock": "prices_mock", "broker_then_nse_eod": "prices_chain", "nse_eod": "prices_nse_eod", "broker": "prices_broker"},
    "surveillance": {"mock": "surveillance_mock", "nse": "surveillance_nse"},
    "fund_nav": {"mock": "fund_nav_mock", "mfapi": "fund_nav_mfapi"},
    "fund_meta": {"mock": "fund_meta_mock", "amfi": "fund_meta_amfi"},
    "fund_holdings": {"mock": "fund_holdings_mock", "mfdata": "fund_holdings_mfdata"},
}
CONFIG_KEY = {"broker": "broker", "fundamentals": "fundamentals", "prices": "prices", "surveillance": "surveillance",
              "fund_nav": "fundNav", "fund_meta": "fundMeta", "fund_holdings": "fundHoldings"}
BUILD_ORDER = ["broker", "fundamentals", "prices", "surveillance", "fund_meta", "fund_nav", "fund_holdings"]

CONTENT_DIR = Path(__file__).resolve().parent / "content"


@lru_cache(maxsize=1)
def content_categories() -> dict:
    return json.loads((CONTENT_DIR / "categories.json").read_text(encoding="utf-8"))


class AppContext:
    def __init__(self, config: dict):
        self.config = config
        self._adapters: dict[str, Any] = {}
        self._statement: Any = None
        self._statement_name: Optional[str] = None
        self._llm: Any = "unset"
        self.llm_provider_override: Any = None

    # ---------------------------------------------------------------- adapters
    def mode(self, kind: str) -> str:
        return self.config["adapters"][CONFIG_KEY[kind]]

    def adapter(self, kind: str):
        if kind in self._adapters:
            return self._adapters[kind]
        mode = self.mode(kind)
        mods = MODULES[kind]
        if mode not in mods:
            raise ApiError("INTERNAL", f"Unknown {kind} adapter mode '{mode}'.")
        for k in BUILD_ORDER:
            if k == kind:
                break
            if k not in self._adapters and k in ("broker",):
                self.adapter(k)  # live price adapters may use the broker
        mod = importlib.import_module(f"app.adapters.{mods[mode]}")
        adapter = mod.build(self.config, dict(self._adapters))
        self._adapters[kind] = adapter
        return adapter

    @property
    def broker(self): return self.adapter("broker")
    @property
    def fundamentals(self): return self.adapter("fundamentals")
    @property
    def prices(self): return self.adapter("prices")
    @property
    def surveillance(self): return self.adapter("surveillance")
    @property
    def fund_nav(self): return self.adapter("fund_nav")
    @property
    def fund_meta(self): return self.adapter("fund_meta")
    @property
    def fund_holdings(self): return self.adapter("fund_holdings")

    def statement_parser(self):
        """casparser if usable (mode auto/casparser), else fallback. Returns the parser instance."""
        if self._statement is not None:
            return self._statement
        mode = self.config["adapters"]["statement"]
        order = {"auto": ["statement_casparser", "statement_fallback"], "casparser": ["statement_casparser"], "fallback": ["statement_fallback"]}.get(mode, ["statement_fallback"])
        deps = {k: self.adapter(k) for k in ("fund_meta",)}
        last_err: Optional[Exception] = None
        for name in order:
            try:
                mod = importlib.import_module(f"app.adapters.{name}")
                self._statement = mod.build(self.config, deps)
                self._statement_name = getattr(self._statement, "name", name.replace("statement_", ""))
                return self._statement
            except Exception as e:  # ImportError when casparser is missing, or a broken module
                last_err = e
        raise ApiError("INTERNAL", f"No statement parser is available: {last_err}")

    def statement_parser_name(self) -> str:
        try:
            self.statement_parser()
            return "casparser" if self._statement_name == "casparser" else "fallback"
        except ApiError:
            return "fallback"

    # ---------------------------------------------------------------- misc
    def today(self) -> date:
        return asof.today(self.config)

    def modes(self) -> dict[str, str]:
        a = self.config["adapters"]
        return {k: a[k] for k in ("broker", "fundamentals", "prices", "surveillance", "fundNav", "fundMeta", "fundHoldings", "statement")}

    def sample(self, *kinds: str) -> bool:
        """True if any of the named adapter kinds runs in mock mode."""
        return any(self.mode(k) == "mock" for k in kinds)

    def llm(self):
        if self.llm_provider_override is not None:
            return self.llm_provider_override
        if self._llm == "unset":
            from .narrative import llm
            self._llm = llm.get_provider(self.config)
        return self._llm

    def llm_enabled(self) -> bool:
        return self.llm() is not None

    def category_record(self, name: str) -> Optional[dict]:
        rec = self.fund_meta.category(name)
        base = content_categories().get(name)
        if rec is None and base is None:
            return None
        out = dict(base or {})
        out.update(rec or {})
        return out

    def checkable_symbols(self) -> frozenset:
        try:
            return frozenset(u["symbol"] for u in self.fundamentals.universe())
        except Exception:
            return frozenset()


_CTX: Optional[AppContext] = None


def get_context() -> AppContext:
    global _CTX
    if _CTX is None:
        _CTX = AppContext(cfgmod.load())
    return _CTX


def set_context(ctx: Optional[AppContext]) -> None:
    global _CTX
    _CTX = ctx
