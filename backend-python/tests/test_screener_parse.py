from pathlib import Path

from app.adapters import screener_parse as sp

HTML = (Path(__file__).parent / "fixtures" / "screener_tcs.html").read_text(encoding="utf-8")


def test_parse_number_cases():
    assert sp.parse_number("1,23,456.7") == 123456.7
    assert sp.parse_number("26%") == 26.0
    assert sp.parse_number("₹ 3,925") == 3925.0
    assert sp.parse_number("-12.5") == -12.5
    assert sp.parse_number("") is None and sp.parse_number("—") is None and sp.parse_number(None) is None
    assert sp.parse_numbers("₹ 4,592 / 3,311") == [4592.0, 3311.0]


def test_period_to_date():
    assert sp.period_to_date("Mar 2026") == "2026-03-31"
    assert sp.period_to_date("Sep 2025") == "2025-09-30"
    assert sp.period_to_date("Feb 2024") == "2024-02-29"
    assert sp.period_to_date("TTM") is None


def test_header_and_top_ratios():
    d = sp.parse_company_page(HTML)
    assert d["name"] == "Tata Consultancy Services Ltd"
    assert d["symbol"] == "TCS"
    assert d["sector"] == "Information Technology" and d["industry"] == "IT Services & Consulting"
    assert d["about"].startswith("Sample fixture text")
    t = d["topRatios"]
    assert t["Market Cap"] == 1420000.0 and t["Stock P/E"] == 29.8 and t["ROE"] == 51.4
    assert t["High / Low"] == 4592.0 and t["High / Low (2)"] == 3311.0
    assert t["Pledged percentage"] == 0.0 and t["Dividend Yield"] == 1.9


def test_tables():
    d = sp.parse_company_page(HTML)
    q = d["quarterly"]
    assert q["periods"] == ["Sep 2025", "Dec 2025", "Mar 2026", "Jun 2026", "Sep 2026"]
    assert q["rows"]["Sales"][-1] == 66400.0 and q["rows"]["OPM %"][0] == 24.0
    a = d["annual"]
    assert a["periods"][-1] == "Mar 2026" and a["rows"]["Net Profit"] == [42147.0, 46099.0, 48553.0, 49000.0]
    assert a["rows"]["EPS in Rs"][0] == 115.19
    b = d["balanceSheet"]
    assert b["rows"]["Borrowings"] == [8000.0, 8100.0, 8300.0]
    s = d["shareholding"]
    assert s["rows"]["Promoters"] == [71.77] * 5
    assert s["rows"]["FIIs"][0] == 12.1


def test_peers():
    p = sp.parse_company_page(HTML)["peers"]
    assert [r["Name"] for r in p["rows"]] == ["TCS", "Infosys", "HCL Technologies"]
    assert p["median"]["P/E"] == "25.6"
    assert sp.parse_number(p["rows"][1]["P/E"]) == 24.9


def test_robust_to_garbage():
    d = sp.parse_company_page("<html><body><p>nothing here")
    assert d["name"] is None and d["quarterly"] == {"periods": [], "rows": {}} and d["peers"]["rows"] == []
    assert sp.parse_company_page("")["topRatios"] == {}
