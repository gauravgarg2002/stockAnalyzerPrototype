"""Pure-logic and fake-transport tests for live adapters (no network)."""
import json
from datetime import date
from pathlib import Path

import pytest

from app.adapters import (fund_holdings_mfdata as fh, fund_meta_amfi as fm, fund_nav_mfapi as fn,
                          fundamentals_screener as fs, prices_nse_eod as pn, surveillance_nse as sn)
from app.adapters.base import PriceSeries
from app.adapters.http_util import DiskCache, RateLimiter, make_session
from app.adapters.prices_chain import ChainPrices
from app.errors import ApiError

FIX = Path(__file__).parent / "fixtures"
BANDS = {"largeMinCrore": 100000, "midMinCrore": 33000, "smallMinCrore": 6000}


class Resp:
    def __init__(self, status=200, text="", js=None):
        self.status_code, self.text, self._js = status, text, js

    def json(self):
        if self._js is None:
            raise ValueError("no json")
        return self._js


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []
        self.headers = {}

    def get(self, url, **kw):
        self.calls.append((url, kw))
        for k, v in self.routes.items():
            if url.endswith(k):
                return v if isinstance(v, Resp) else v(url, kw)
        return Resp(404)


# ---- http_util
def test_session_has_browser_ua_and_no_io():
    s = make_session()
    assert "Mozilla/5.0" in s.headers["User-Agent"]


def test_rate_limiter_spacing():
    t = [0.0]
    slept = []

    def sleep(x):
        slept.append(x)
        t[0] += x

    rl = RateLimiter(3, clock=lambda: t[0], sleep=sleep)
    assert rl.wait() == 0.0
    t[0] += 1
    assert rl.wait() == pytest.approx(2.0)
    t[0] += 10
    assert rl.wait() == 0.0 and slept == [pytest.approx(2.0)]


def test_disk_cache_ttl(tmp_path):
    now = [1000.0]
    c = DiskCache(tmp_path, 1, clock=lambda: now[0])
    assert c.get("k") is None
    c.set("k", {"a": [1, 2]})
    assert c.get("k") == {"a": [1, 2]}
    now[0] += 3601
    assert c.get("k") is None
    DiskCache(tmp_path / "ro", 1).set("x", object())  # unserialisable: silently ignored


# ---- fundamentals
def test_size_band_and_financial():
    assert [fs.size_band(x, BANDS) for x in (150000, 50000, 8000, 100, None)] == ["LARGE", "MID", "SMALL", "MICRO", "MICRO"]
    assert fs.is_financial("Financial Services", "Private Sector Bank") and not fs.is_financial("IT", "IT Services")


def make_fund_cfg(tmp_path):
    return {"screener": {"baseUrl": "https://example.test", "sessionCookie": "abc", "minIntervalSeconds": 0},
            "sizeBands": BANDS, "cache": {"dir": str(tmp_path), "fundamentalsHours": 24}}


def test_fundamentals_adapter_fallback_cache_and_cookie(tmp_path):
    html = (FIX / "screener_tcs.html").read_text(encoding="utf-8")
    sess = FakeSession({"/company/TCS/": Resp(200, html)})  # consolidated 404 -> standalone
    a = fs.ScreenerFundamentals(make_fund_cfg(tmp_path), session=sess, limiter=RateLimiter(0))
    f = a.get("tcs")
    assert f.symbol == "TCS" and f.source == "Company filings" and f.sizeBand == "LARGE"
    assert [u for u, _ in sess.calls] == ["https://example.test/company/TCS/consolidated/", "https://example.test/company/TCS/"]
    assert sess.calls[0][1]["headers"]["Cookie"] == "sessionid=abc" or sess.calls[0][1]["headers"]["Cookie"] == "abc"
    n = len(sess.calls)
    assert a.get("TCS").name == f.name and len(sess.calls) == n  # served from cache
    blob = json.dumps(f.__dict__, default=str).lower()
    assert "screener" not in blob


def test_fundamentals_unknown_and_blocked(tmp_path):
    a = fs.ScreenerFundamentals(make_fund_cfg(tmp_path), session=FakeSession({}), limiter=RateLimiter(0))
    assert a.get("NOPE") is None and a.get("bad symbol!") is None
    b = fs.ScreenerFundamentals(make_fund_cfg(tmp_path), session=FakeSession({"/consolidated/": Resp(429)}),
                                limiter=RateLimiter(0))
    with pytest.raises(ApiError) as e:
        b.get("TCS")
    assert e.value.code == "UPSTREAM_UNAVAILABLE"
    assert "screener" not in e.value.message.lower()


def test_search_json():
    assert fs.parse_search_json([{"id": 1, "name": "Tata Consultancy Services Ltd", "url": "/company/TCS/consolidated/"},
                                 {"bogus": 1}]) == [{"symbol": "TCS", "name": "Tata Consultancy Services Ltd"}]


# ---- surveillance
CSV = """Sr.No.,Symbol,Security Name,ASM Stage,Date
1,SHIVAGRO,Shivalik Agro Polymers Ltd,Long-term ASM Stage II,14-Aug-2026
2,ABCD,Abcd Ltd,Short-term ASM Stage I,2026-10-01
,,,,
"""


def test_parse_surveillance_csv():
    r = sn.parse_surveillance_csv(CSV, "ASM")
    assert [(e.symbol, e.list, e.stage, e.since) for e in r] == [
        ("SHIVAGRO", "ASM", "Long-term ASM Stage II", "2026-08-14"), ("ABCD", "ASM", "Short-term ASM Stage I", "2026-10-01")]
    assert sn.parse_surveillance_csv("symbol,name,stage,since\nXYZ,Xyz Ltd,Stage 1,2026-01-02\n", "GSM")[0].since == "2026-01-02"
    assert sn.parse_surveillance_csv("garbage", "ESM") == [] and sn.parse_surveillance_csv("", "ESM") == []
    pre = "Report generated on 01-Nov-2026\n\n" + CSV
    assert len(sn.parse_surveillance_csv(pre, "ASM")) == 2


def test_surveillance_lookup(tmp_path):
    cfg = {"nse": {"baseUrl": "https://n.test", "asmCsvUrl": "https://n.test/asm.csv", "gsmCsvUrl": "https://n.test/gsm.csv",
                   "esmCsvUrl": "https://n.test/esm.csv", "minIntervalSeconds": 0}, "cache": {"dir": str(tmp_path)}}
    ok = FakeSession({"/asm.csv": Resp(200, CSV), "/gsm.csv": Resp(200, "symbol,name,stage,since\n"),
                      "/esm.csv": Resp(200, "symbol,name,stage,since\n")})
    a = sn.NseSurveillance(cfg, session=ok, limiter=RateLimiter(0))
    assert [e.list for e in a.lookup("shivagro")] == ["ASM"]
    assert a.lookup("TCS") == []
    bad = FakeSession({"/asm.csv": Resp(200, CSV), "/gsm.csv": Resp(500), "/esm.csv": Resp(200, "symbol\n")})
    cfg2 = dict(cfg, cache={"dir": str(tmp_path / "b")})
    b = sn.NseSurveillance(cfg2, session=bad, limiter=RateLimiter(0))
    assert b.lookup("TCS") is None and b.lookup("SHIVAGRO")[0].symbol == "SHIVAGRO"


# ---- mfapi
def test_parse_mfapi_and_adapter(tmp_path):
    obj = {"meta": {"scheme_code": 119551}, "data": [{"date": "30-10-2026", "nav": "62.4012"},
                                                    {"date": "29-10-2026", "nav": "62.10"},
                                                    {"date": "bad", "nav": "1"}, {"date": "28-10-2026", "nav": "0"}],
           "status": "SUCCESS"}
    assert fn.parse_mfapi(obj) == [(date(2026, 10, 29), 62.1), (date(2026, 10, 30), 62.4012)]
    sess = FakeSession({"/mf/119551": Resp(200, js=obj)})
    a = fn.MfapiNav({"mfapi": {"baseUrl": "https://m.test"}, "cache": {"dir": str(tmp_path)}}, session=sess)
    s = a.nav_series("119551")
    assert s.asOf == "2026-10-30" and s.source == "AMFI" and len(s.points) == 2
    assert a.nav_series("119551").asOf == "2026-10-30" and len(sess.calls) == 1
    assert a.nav_series("999999") is None and a.nav_series("abc") is None


# ---- AMFI
NAVALL = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

Open Ended Schemes(Equity Scheme - Flexi Cap Fund)

Kaveri Mutual Fund

100001;INF000A01AA1;-;Kaveri Flexi Cap Fund - Direct Plan - Growth;120.5;30-Oct-2026
100002;INF000A01AB9;-;Kaveri Flexi Cap Fund - Regular Plan - Growth;101.2;30-Oct-2026
100003;INF000A01AC7;INF000A01AD5;Kaveri Flexi Cap Fund - Direct Plan - IDCW;50.1;30-Oct-2026

Open Ended Schemes(Debt Scheme - Gilt Fund)

Ganga Mutual Fund

100010;INF000B01BB2;-;Ganga Gilt Fund - Direct Plan - Growth;30.0;30-Oct-2026
bad line;x
"""


def test_parse_navall_and_index():
    rows = fm.parse_navall(NAVALL)
    assert [r["code"] for r in rows] == ["100001", "100002", "100003", "100010"]
    assert rows[0]["amc"] == "Kaveri Mutual Fund" and rows[0]["category"] == "Flexi Cap Fund"
    assert rows[3]["amc"] == "Ganga Mutual Fund" and rows[3]["groupText"] == "Debt Scheme"
    metas = fm.build_index(rows, "2026-11-12")
    d, r, idcw, g = (metas[c] for c in ("100001", "100002", "100003", "100010"))
    assert (d.planType, r.planType, d.categoryGroup, g.categoryGroup) == ("DIRECT", "REGULAR", "EQUITY", "DEBT")
    assert d.twinSchemeCode == "100002" and r.twinSchemeCode == "100001" and idcw.twinSchemeCode is None
    assert d.terPct is None and d.source == "AMFI" and d.shortName == "Kaveri Flexi Cap Fund"
    assert [m.schemeCode for m in fm.search_metas(metas, "kaveri flexi", 10)] == ["100001", "100002"]


def test_amfi_adapter(tmp_path):
    sess = FakeSession({"NAVAll.txt": Resp(200, NAVALL)})
    a = fm.AmfiFundMeta({"amfi": {"navAllUrl": "https://a.test/NAVAll.txt"}, "cache": {"dir": str(tmp_path)}}, session=sess)
    assert a.get("100001").name.startswith("Kaveri") and a.find_by_isin("inf000a01ad5").schemeCode == "100003"
    assert a.get("1") is None and a.find_by_isin("INF999") is None and a.category("Flexi Cap Fund") is None
    assert set(a.all_codes()) == {"100001", "100002", "100003", "100010"} and len(sess.calls) == 1
    bad = fm.AmfiFundMeta({"amfi": {"navAllUrl": "https://a.test/NAVAll.txt"}, "cache": {"dir": str(tmp_path / "x")}},
                          session=FakeSession({"NAVAll.txt": Resp(200, "<html>blocked</html>")}))
    with pytest.raises(ApiError) as e:
        bad.get("1")
    assert e.value.code == "UPSTREAM_UNAVAILABLE"


# ---- mfdata
def test_parse_mfdata_and_fallback(tmp_path):
    obj = {"data": {"as_of": "2026-09-30", "holdings": [
        {"name": "HDFC Bank Ltd", "isin": "INE040A01034", "symbol": "HDFCBANK", "sector": "Financial Services", "weight": "8.12"},
        {"name": "Govt Sec", "isin": "IN0020200001", "weight": 5.0},
        {"name": "Zero", "isin": "INE000000001", "weight": 0}],
        "asset_allocation": {"equity": 96.5, "debt": 0, "cash": 3.5, "other": 0}}}
    fp = fh.parse_mfdata_holdings(obj, "900101")
    assert fp.portfolioDate == "2026-09-30" and fp.holdings[0]["weightPct"] == 8.12 and len(fp.holdings) == 1
    assert fp.assetMix == {"equityPct": 96.5, "debtPct": 0.0, "cashPct": 3.5, "otherPct": 0.0}
    assert fh.parse_mfdata_holdings({"data": {}}, "1") is None

    funds = tmp_path / "funds.json"
    funds.write_text(json.dumps([{"schemeCode": "900101", "portfolioDate": "2026-09-30",
                                  "assetMix": {"equityPct": 96.5, "debtPct": 0, "cashPct": 3.5, "otherPct": 0},
                                  "holdings": [{"symbol": "X", "weightPct": 1.0}]}]), encoding="utf-8")
    assert fh.load_starter("900101", funds).source == "Sample data" and fh.load_starter("42", funds) is None
    assert fh.load_starter("900101", tmp_path / "missing.json") is None
    a = fh.MfdataHoldings({"mfdata": {"baseUrl": "https://f.test/api/v1"}, "cache": {"dir": str(tmp_path / "c")}},
                          session=FakeSession({"/schemes/123456/holdings": Resp(200, js=obj)}))
    assert a.portfolio("123456").source == "Fund factsheet"
    assert a.portfolio("not-a-code") is None


# ---- NSE price parsing and chain
def test_nse_parsers_and_chunks():
    eq = {"data": [{"CH_TIMESTAMP": "2026-10-30", "CH_CLOSING_PRICE": 3925.4, "CH_TOT_TRADED_QTY": 1000},
                   {"CH_TIMESTAMP": "2026-10-29", "CH_CLOSING_PRICE": "3,900.5", "CH_TOT_TRADED_QTY": None},
                   {"CH_TIMESTAMP": "bad", "CH_CLOSING_PRICE": 1}]}
    assert pn.parse_equity_history(eq) == [(date(2026, 10, 29), 3900.5, None), (date(2026, 10, 30), 3925.4, 1000)]
    ix = {"data": {"indexCloseOnlineRecords": [{"EOD_TIMESTAMP": "30-Oct-2026", "EOD_CLOSE_INDEX_VAL": "26,000.5"}]}}
    assert pn.parse_index_history(ix) == [(date(2026, 10, 30), 26000.5, None)]
    assert pn.parse_equity_history(None) == [] and pn.parse_index_history({}) == []
    ch = pn.chunks(date(2021, 1, 1), date(2022, 6, 1))
    assert ch[0][0] == date(2021, 1, 1) and ch[-1][1] == date(2022, 6, 1) and len(ch) == 2
    assert all((b - a).days < 360 for a, b in ch) and ch[1][0] == date.fromordinal(ch[0][1].toordinal() + 1)
    rt = pn.from_cache(pn.to_cache([(date(2026, 1, 2), 1.5, None)]))
    assert rt == [(date(2026, 1, 2), 1.5, None)]


def test_nse_adapter_with_fake_session(tmp_path):
    def eq(url, kw):
        return Resp(200, js={"data": [{"CH_TIMESTAMP": "2026-10-30", "CH_CLOSING_PRICE": 10.0, "CH_TOT_TRADED_QTY": 5}]})
    sess = FakeSession({"/api/historical/cm/equity": eq, "nseindia.test/": Resp(200, "ok")})
    a = pn.NseEodPrices({"nse": {"baseUrl": "https://nseindia.test", "minIntervalSeconds": 0}, "cache": {"dir": str(tmp_path)}},
                        session=sess, limiter=RateLimiter(0))
    s = a.stock_series("tcs")
    assert s.points[-1][1] == 10.0 and s.source == "NSE" and sess.calls[0][0] == "https://nseindia.test/"
    assert a.index_series("NIFTY50_TRI") is None


class StubPrices:
    mode = "stub"

    def __init__(self, series=None, err=None):
        self.series, self.err = series, err

    def stock_series(self, s):
        if self.err:
            raise self.err
        return self.series

    index_series = stock_series


def test_chain_prefers_primary_then_falls_back():
    good = PriceSeries("TCS", [(date(2026, 10, 30), 1.0, None)], "NSE", "2026-10-30")
    other = PriceSeries("TCS", [(date(2026, 10, 30), 2.0, None)], "NSE", "2026-10-30")
    assert ChainPrices(StubPrices(good), StubPrices(other)).stock_series("TCS").points[0][1] == 1.0
    assert ChainPrices(StubPrices(None), StubPrices(other)).stock_series("TCS").points[0][1] == 2.0
    nc = ApiError("BROKER_NOT_CONNECTED", "x")
    assert ChainPrices(StubPrices(err=nc), StubPrices(other)).stock_series("TCS").points[0][1] == 2.0
    up = ApiError("UPSTREAM_UNAVAILABLE", "down")
    with pytest.raises(ApiError):
        ChainPrices(StubPrices(None), StubPrices(err=up)).stock_series("TCS")
    assert ChainPrices(StubPrices(None), StubPrices(None)).stock_series("TCS") is None


# ---- construction convention
MODULES = ["broker_kite_mcp", "broker_kite_connect", "fundamentals_screener", "prices_broker", "prices_nse_eod",
           "prices_chain", "surveillance_nse", "fund_nav_mfapi", "fund_meta_amfi", "fund_holdings_mfdata",
           "statement_fallback", "statement_casparser", "broker_guard", "http_util", "isin_map", "cas_text_parser",
           "screener_parse"]


def test_import_and_build_do_no_network(monkeypatch, tmp_path):
    import importlib
    import socket

    def deny(*a, **k):
        raise AssertionError("network I/O attempted")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    for m in MODULES:
        importlib.reload(importlib.import_module(f"app.adapters.{m}"))
    from app import config as cfgmod
    from app.adapters import base

    cfg = cfgmod.deep_merge(cfgmod.DEFAULTS, {"cache": {"dir": str(tmp_path)}})
    built = {}
    for key, mod, proto in [("broker", "broker_kite_mcp", base.BrokerAdapter), ("broker", "broker_kite_connect", base.BrokerAdapter),
                            ("fundamentals", "fundamentals_screener", base.FundamentalsAdapter),
                            ("prices", "prices_nse_eod", base.PriceAdapter), ("prices", "prices_chain", base.PriceAdapter),
                            ("surveillance", "surveillance_nse", base.SurveillanceAdapter),
                            ("fund_nav", "fund_nav_mfapi", base.FundNavAdapter),
                            ("fund_meta", "fund_meta_amfi", base.FundMetaAdapter),
                            ("fund_holdings", "fund_holdings_mfdata", base.FundHoldingsAdapter),
                            ("statement", "statement_fallback", base.StatementParser)]:
        a = importlib.import_module(f"app.adapters.{mod}").build(cfg, built)
        assert isinstance(a, proto), mod
        assert isinstance(a.mode if hasattr(a, "mode") else a.name, str)
        built.setdefault(key, a)
    from app.adapters import prices_broker
    assert isinstance(prices_broker.build(cfg, built), base.PriceAdapter)
