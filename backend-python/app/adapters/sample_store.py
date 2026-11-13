"""Loads app/data/sample/* once (lru_cache); typed accessors for the mock adapters."""
from __future__ import annotations

import csv
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .. import sources
from .base import FundMeta, FundPortfolio, NavSeries, PriceSeries, StockFundamentals, SurveillanceEntry

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


def _json(rel: str):
    return json.loads((DATA_DIR / rel).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def manifest() -> dict:
    return _json("manifest.json")


def as_of() -> str:
    return manifest()["asOf"]


@lru_cache(maxsize=1)
def stock_records() -> dict[str, dict]:
    return {r["symbol"]: r for r in _json("stocks.json")}


@lru_cache(maxsize=1)
def universe() -> list[dict]:
    return _json("universe.json")


@lru_cache(maxsize=1)
def fund_records() -> dict[str, dict]:
    return {r["schemeCode"]: r for r in _json("funds.json")}


@lru_cache(maxsize=1)
def categories() -> dict[str, dict]:
    return _json("fund_categories.json")


@lru_cache(maxsize=1)
def sample_user() -> dict:
    return _json("sample_user.json")


@lru_cache(maxsize=1)
def indices() -> list[dict]:
    return _json("indices.json")


def stock(symbol: str) -> Optional[StockFundamentals]:
    r = stock_records().get(symbol.upper())
    if r is None:
        return None
    return StockFundamentals(
        symbol=r["symbol"], name=r["name"], isin=r["isin"], sector=r["sector"], industry=r["industry"], sizeBand=r["sizeBand"],
        marketCapRank=r["marketCapRank"], isFinancial=r["isFinancial"], sharesOutstanding=r["sharesOutstanding"], about=r["about"],
        revenueSegments=r["revenueSegments"], peerGroup=r["peerGroup"], annual=r["annual"], quarterly=r["quarterly"],
        shareholding=r["shareholding"], valuationHistory=r["valuationHistory"], dividendYieldPct=r["dividendYieldPct"], events=r["events"],
        source=sources.SAMPLE, asOf=as_of(), exchange=r["exchange"], fictional=r["fictional"], lastPrice=r["lastPrice"])


@lru_cache(maxsize=64)
def stock_prices(symbol: str) -> Optional[PriceSeries]:
    p = DATA_DIR / "prices" / "stocks" / f"{symbol.upper()}.csv"
    if not p.is_file():
        return None
    pts = []
    with open(p, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pts.append((date.fromisoformat(row["date"]), float(row["close"]), int(row["volume"])))
    return PriceSeries(id=symbol.upper(), points=pts, source=sources.SAMPLE, asOf=as_of())


@lru_cache(maxsize=16)
def index_prices(index_id: str) -> Optional[PriceSeries]:
    p = DATA_DIR / "prices" / "indices" / f"{index_id}.csv"
    if not p.is_file():
        return None
    pts = []
    with open(p, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pts.append((date.fromisoformat(row["date"]), float(row["close"]), None))
    return PriceSeries(id=index_id, points=pts, source=sources.SAMPLE, asOf=as_of())


@lru_cache(maxsize=16)
def navs(code: str) -> Optional[NavSeries]:
    p = DATA_DIR / "navs" / f"{code}.csv"
    if not p.is_file():
        return None
    pts = []
    with open(p, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pts.append((date.fromisoformat(row["date"]), float(row["nav"])))
    return NavSeries(id=code, points=pts, source=sources.SAMPLE, asOf=as_of())


def fund_meta(code: str) -> Optional[FundMeta]:
    r = fund_records().get(code)
    if r is None:
        return None
    return FundMeta(
        schemeCode=r["schemeCode"], isin=r["isin"], name=r["name"], shortName=r["shortName"], amc=r["amc"], category=r["category"],
        categoryGroup=r["categoryGroup"], planType=r["planType"], twinSchemeCode=r["twinSchemeCode"], launchDate=date.fromisoformat(r["launchDate"]),
        aumInr=r["aumInr"], aumInr1yAgo=r["aumInr1yAgo"], terPct=r["terPct"], terAsOf=r["terAsOf"], exitLoad=r["exitLoad"],
        lockInYears=r["lockInYears"], benchmarkId=r["benchmarkId"], managers=r["managers"], source=sources.SAMPLE, asOf=as_of())


def fund_portfolio(code: str) -> Optional[FundPortfolio]:
    r = fund_records().get(code)
    if r is None:
        return None
    return FundPortfolio(schemeCode=code, portfolioDate=r["portfolioDate"], assetMix=r["assetMix"], holdings=r["holdings"],
                         previousTop10=r["previousTop10"], events=r["events"], source=sources.SAMPLE)


@lru_cache(maxsize=4)
def surveillance_entries() -> list[SurveillanceEntry]:
    out = []
    for lst in ("asm", "gsm", "esm"):
        p = DATA_DIR / "surveillance" / f"{lst}.csv"
        with open(p, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                out.append(SurveillanceEntry(symbol=row["symbol"], list=lst.upper(), stage=row["stage"], since=row["since"], name=row["name"]))
    return out
