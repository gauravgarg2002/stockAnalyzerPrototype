"""Handlers: plain functions (ctx, params) -> dict. The only place adapters meet engines.

params = path params + query params (strings) for query routes; for json_body routes params = path params + {"body": parsed JSON}.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import asdict
from datetime import date
from typing import Any

from . import errors
from .adapters.base import INDEX_NAMES
from .content import glossary as gl
from .context import AppContext
from .engines import compare as compare_engine
from .engines.fund_check import build_fund_check, fund_subtitle
from .engines.instruments import fund_entry, stock_entry
from .engines.inputs import FundInputs, StockInputs
from .engines.price_points import points_for
from .engines.search import search as search_engine
from .engines.stock_check import build_stock_check, stock_subtitle
from .narrative import narrate as narrate_mod

VERSION = "0.1.0"
STOCK_SOURCE_KINDS = ("fundamentals", "prices", "surveillance")
FUND_SOURCE_KINDS = ("fund_meta", "fund_nav", "fund_holdings", "prices")


# ------------------------------------------------------------------ health / search
def health(ctx: AppContext, p: dict) -> dict:
    return {"status": "ok", "sampleData": ctx.sample("broker", "fundamentals", "prices", "surveillance", "fund_nav", "fund_meta", "fund_holdings"),
            "asOf": ctx.today().isoformat(), "version": VERSION, "adapters": ctx.modes(), "statementParser": ctx.statement_parser_name(),
            "llmEnabled": ctx.llm_enabled()}


def _int_param(p: dict, name: str, default: int, lo: int, hi: int) -> int:
    raw = p.get(name)
    if raw is None or raw == "":
        return default
    try:
        v = int(raw)
    except (TypeError, ValueError):
        raise errors.bad_request(f"'{name}' must be a whole number.", {"param": name})
    if not lo <= v <= hi:
        raise errors.bad_request(f"'{name}' must be between {lo} and {hi}.", {"param": name})
    return v


def search(ctx: AppContext, p: dict) -> dict:
    q = (p.get("q") or "").strip()
    if not q:
        raise errors.bad_request("Query 'q' must have at least one character.", {"param": "q"})
    limit = _int_param(p, "limit", 10, 1, 10)
    stocks = ctx.fundamentals.search_stocks(q, 50)
    funds = ctx.fund_meta.search(q, 50)
    return {"sampleData": ctx.sample("fundamentals", "fund_meta"), "query": q, "results": search_engine(q, stocks, funds, limit)}


# ------------------------------------------------------------------ stock check
def _stock_inputs(ctx: AppContext, symbol: str) -> StockInputs:
    sym = symbol.strip().upper()
    f = ctx.fundamentals.get(sym)
    if f is None:
        raise errors.not_found(f"No stock found for symbol {sym}.", {"symbol": sym})
    sz = ctx.config["sizeBands"]
    return StockInputs(f=f, prices=ctx.prices.stock_series(sym), benchmark=ctx.prices.index_series("NIFTY50"), surveillance=ctx.surveillance.lookup(sym),
                       as_of=ctx.today(), size_bands=sz, checkable_symbols=ctx.checkable_symbols())


def stock_check(ctx: AppContext, p: dict) -> dict:
    return build_stock_check(_stock_inputs(ctx, p["symbol"]), ctx.sample(*STOCK_SOURCE_KINDS))


# ------------------------------------------------------------------ fund check
def _fund_inputs(ctx: AppContext, code: str, amount: float, basis: str, user_funds: list[dict]) -> FundInputs:
    m = ctx.fund_meta.get(code)
    if m is None:
        raise errors.not_found(f"No fund found for scheme code {code}.", {"schemeCode": code})
    nav = ctx.fund_nav.nav_series(code)
    if nav is None or not nav.points:
        raise errors.upstream_unavailable(f"NAV history for scheme {code} is not available.", {"schemeCode": code})
    twin = ctx.fund_meta.get(m.twinSchemeCode) if m.twinSchemeCode else None
    bench = ctx.prices.index_series(m.benchmarkId) if m.benchmarkId else None
    return FundInputs(meta=m, nav=nav, portfolio=ctx.fund_holdings.portfolio(code), benchmark=bench,
                      benchmark_name=INDEX_NAMES.get(m.benchmarkId or "", m.benchmarkId or "Benchmark"), category=ctx.category_record(m.category),
                      twin=twin, twin_category_note=None, as_of=ctx.today(), amount_inr=float(amount), amount_basis=basis, user_funds=user_funds)


def _parse_user_funds(raw: Any) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise errors.bad_request("'userFunds' must be a list.", {"field": "userFunds"})
    out = []
    for u in raw:
        try:
            out.append({"schemeCode": str(u["schemeCode"]), "name": str(u["name"]), "overlapPct": float(u["overlapPct"]), "commonCount": int(u["commonCount"])})
        except (KeyError, TypeError, ValueError):
            raise errors.bad_request("Each userFunds item needs schemeCode, name, overlapPct and commonCount.", {"field": "userFunds"})
    return out


def fund_check(ctx: AppContext, p: dict) -> dict:
    body = p.get("body")
    if not isinstance(body, dict):
        raise errors.bad_request("Body must be a JSON object.")
    try:
        amount = float(body["amountInr"])
    except (KeyError, TypeError, ValueError):
        raise errors.bad_request("'amountInr' must be a number.", {"field": "amountInr"})
    if not amount > 0:
        raise errors.bad_request("'amountInr' must be greater than zero.", {"field": "amountInr"})
    basis = body.get("amountBasis", "ILLUSTRATIVE")
    if basis not in ("HOLDING", "ILLUSTRATIVE", "USER_INPUT"):
        raise errors.bad_request("'amountBasis' must be HOLDING, ILLUSTRATIVE or USER_INPUT.", {"field": "amountBasis"})
    fi = _fund_inputs(ctx, p["schemeCode"], amount, basis, _parse_user_funds(body.get("userFunds")))
    return build_fund_check(fi, ctx.sample(*FUND_SOURCE_KINDS))


# ------------------------------------------------------------------ compare
def compare(ctx: AppContext, p: dict) -> dict:
    kind = (p.get("kind") or "").upper()
    if kind not in ("STOCK", "FUND"):
        raise errors.bad_request("'kind' must be STOCK or FUND.", {"param": "kind"})
    ids = [i.strip() for i in (p.get("ids") or "").split(",") if i.strip()]
    if not 2 <= len(ids) <= 3:
        raise errors.bad_request("Provide 2 or 3 ids, comma-separated.", {"param": "ids"})
    refs, checks = [], []
    if kind == "STOCK":
        for sid in ids:
            si = _stock_inputs(ctx, sid)
            checks.append(build_stock_check(si, True))
            refs.append({"kind": "STOCK", "id": si.f.symbol, "name": si.f.name, "subtitle": stock_subtitle(si.f.sector, si.f.sizeBand), "checkPath": f"/stock/{si.f.symbol}"})
        sample = ctx.sample(*STOCK_SOURCE_KINDS)
    else:
        raw = p.get("amountInr")
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            raise errors.bad_request("'amountInr' is required for funds.", {"param": "amountInr"})
        if not amount > 0:
            raise errors.bad_request("'amountInr' must be greater than zero.", {"param": "amountInr"})
        for code in ids:
            fi = _fund_inputs(ctx, code, amount, "COMPARE", [])
            checks.append(build_fund_check(fi, True))
            refs.append({"kind": "FUND", "id": fi.meta.schemeCode, "name": fi.meta.name, "subtitle": fund_subtitle(fi.meta.category, fi.meta.planType),
                         "checkPath": f"/fund/{fi.meta.schemeCode}"})
        sample = ctx.sample(*FUND_SOURCE_KINDS)
    return compare_engine.build_compare(kind, ctx.today().isoformat(), sample, refs, checks)


# ------------------------------------------------------------------ glossary / explain
def glossary(ctx: AppContext, p: dict) -> dict:
    return {"sampleData": False, "terms": gl.list_terms()}


def explain(ctx: AppContext, p: dict) -> dict:
    term = gl.get_term(p.get("term") or "")
    if term is None:
        raise errors.not_found(f"No glossary term '{p.get('term')}'.", {"term": p.get("term")})
    kind, iid = p.get("kind"), p.get("id")
    if bool(kind) != bool(iid):
        raise errors.bad_request("Provide both 'kind' and 'id', or neither.", {"param": "kind"})
    if not kind:
        return {"sampleData": False, **gl.explain(term, None, None, None)}
    kind = kind.upper()
    if kind == "STOCK":
        si = _stock_inputs(ctx, iid)
        check = build_stock_check(si, True)
        ref = {"kind": "STOCK", "id": si.f.symbol, "name": si.f.name, "subtitle": stock_subtitle(si.f.sector, si.f.sizeBand)}
        sample = ctx.sample(*STOCK_SOURCE_KINDS)
    elif kind == "FUND":
        fi = _fund_inputs(ctx, iid, float(ctx.config["app"]["defaultIllustrativeAmountInr"]), "ILLUSTRATIVE", [])
        check = build_fund_check(fi, True)
        ref = {"kind": "FUND", "id": fi.meta.schemeCode, "name": fi.meta.name, "subtitle": fund_subtitle(fi.meta.category, fi.meta.planType)}
        sample = ctx.sample(*FUND_SOURCE_KINDS)
    else:
        raise errors.bad_request("'kind' must be STOCK or FUND.", {"param": "kind"})
    return {"sampleData": sample, **gl.explain(term, check, ref, kind)}


# ------------------------------------------------------------------ bundle / points
def bundle(ctx: AppContext, p: dict) -> dict:
    body = p.get("body")
    if not isinstance(body, dict):
        raise errors.bad_request("Body must be a JSON object.")
    stocks_req, funds_req = body.get("stocks") or [], body.get("funds") or []
    if not isinstance(stocks_req, list) or not isinstance(funds_req, list):
        raise errors.bad_request("'stocks' and 'funds' must be lists.")
    as_of = ctx.today()
    out_stocks, out_funds, nf = [], [], []
    for s in stocks_req:
        sym = str(s).upper()
        f = ctx.fundamentals.get(sym)
        if f is None:
            nf.append({"kind": "STOCK", "id": str(s)})
            continue
        out_stocks.append(stock_entry(f, ctx.prices.stock_series(sym), as_of, f.source))
    checkable = ctx.checkable_symbols()
    universe = {u["symbol"]: u for u in _universe_for_lookup(ctx)}
    for code in funds_req:
        code = str(code)
        m = ctx.fund_meta.get(code)
        if m is None:
            nf.append({"kind": "FUND", "id": code})
            continue
        twin = ctx.fund_meta.get(m.twinSchemeCode) if m.twinSchemeCode else None
        out_funds.append(fund_entry(m, ctx.fund_nav.nav_series(code), ctx.fund_holdings.portfolio(code), twin, ctx.category_record(m.category), as_of, checkable, universe))
    return {"sampleData": ctx.sample("fundamentals", "prices", "fund_meta", "fund_nav", "fund_holdings"), "asOf": as_of.isoformat(),
            "stocks": out_stocks, "funds": out_funds, "notFound": nf}


def _universe_for_lookup(ctx: AppContext) -> list[dict]:
    """Sector/size lookup for fund constituents that do not carry them (mock mode: bundled universe)."""
    try:
        if ctx.mode("fundamentals") == "mock":
            from .adapters import sample_store
            return sample_store.universe() + ctx.fundamentals.universe()
        return ctx.fundamentals.universe()
    except Exception:
        return []


def prices_points(ctx: AppContext, p: dict) -> dict:
    body = p.get("body")
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise errors.bad_request("Body must contain an 'items' list.")
    items = []
    for it in body["items"]:
        try:
            kind, iid, dates = it["kind"], str(it["id"]), [str(d) for d in it["dates"]]
            for d in dates:
                date.fromisoformat(d)
        except (KeyError, TypeError, ValueError):
            raise errors.bad_request("Each item needs kind, id and ISO dates.")
        if kind == "STOCK":
            s = ctx.prices.stock_series(iid.upper())
            series = [(x[0], x[1]) for x in s.points] if s else None
        elif kind == "INDEX":
            s = ctx.prices.index_series(iid)
            series = [(x[0], x[1]) for x in s.points] if s else None
        elif kind == "FUND":
            n = ctx.fund_nav.nav_series(iid)
            series = list(n.points) if n else None
        else:
            raise errors.bad_request("kind must be STOCK, FUND or INDEX.")
        items.append({"kind": kind, "id": iid, "values": points_for(series, dates)})
    return {"sampleData": ctx.sample("prices", "fund_nav"), "asOf": ctx.today().isoformat(), "items": items}


# ------------------------------------------------------------------ broker
def broker_login_start(ctx: AppContext, p: dict) -> dict:
    return ctx.broker.login_start()


def broker_login_status(ctx: AppContext, p: dict) -> dict:
    return ctx.broker.login_status()


def broker_login_complete(ctx: AppContext, p: dict) -> dict:
    body = p.get("body")
    token = body.get("requestToken") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise errors.bad_request("'requestToken' is required.", {"field": "requestToken"})
    return ctx.broker.login_complete(token)


def broker_logout(ctx: AppContext, p: dict) -> dict:
    return ctx.broker.logout()


def broker_portfolio(ctx: AppContext, p: dict) -> dict:
    bp = ctx.broker.portfolio()
    d = asdict(bp)
    return {"sampleData": d.pop("sampleData"), "source": d["source"], "asOf": d["asOf"], "accountLabel": d["accountLabel"], "stocks": d["stocks"],
            "funds": d["funds"], "idleCashInr": d["idleCashInr"], "unmatched": d["unmatched"]}


# ------------------------------------------------------------------ statements
def statements_parse(ctx: AppContext, p: dict) -> dict:
    body = p.get("body")
    if not isinstance(body, dict):
        raise errors.bad_request("Body must be a JSON object.")
    b64, pw = body.get("fileBase64"), body.get("password")
    if not isinstance(b64, str) or not b64:
        raise errors.bad_request("'fileBase64' is required.", {"field": "fileBase64"})
    try:
        raw = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError):
        raise errors.bad_request("'fileBase64' is not valid base64.", {"field": "fileBase64"})
    res = ctx.statement_parser().parse(raw, pw if isinstance(pw, str) else "", str(body.get("filename") or ""))
    return {"sampleData": res.sampleData, "parser": res.parser, "statementType": res.statementType, "statementDate": res.statementDate,
            "funds": res.funds, "unmatched": res.unmatched}


# ------------------------------------------------------------------ narrate
def narrate(ctx: AppContext, p: dict) -> dict:
    return narrate_mod.narrate(p.get("body"), ctx.llm())
