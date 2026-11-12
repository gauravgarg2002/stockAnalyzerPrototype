import base64
import io
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import cas_text_parser as cp
from app.errors import ApiError

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


def test_cams_text():
    r = cp.parse_cas_text((FIX / "cas_cams.txt").read_text(encoding="utf-8"))
    assert r.statement_type == "CAMS" and r.statement_date == "2026-10-15"
    assert [e.isin for e in r.entries] == ["INFSMP900701", "INF000X01ABC"]  # zero-balance scheme skipped
    a, b = r.entries
    assert a.name == "Sindhu Large Cap Fund - Direct Plan - Growth"
    assert a.amc == "Sindhu Mutual Fund"
    assert (a.units, a.nav, a.nav_date, a.value_inr, a.cost_inr) == (812.441, 48.2201, "2026-10-14", 39176.5, 35000.0)
    assert b.name == "Example Gilt Fund - Direct Growth" and b.units == 100.0 and b.value_inr == 2000.0
    assert b.cost_inr == 1900.0  # values on the wrapped line are picked up


def test_kfintech_text():
    r = cp.parse_cas_text((FIX / "cas_kfintech.txt").read_text(encoding="utf-8"))
    assert r.statement_type == "KFINTECH" and r.statement_date == "2026-10-15"
    assert len(r.entries) == 2
    a, b = r.entries
    assert a.isin == "INFSMP900801" and a.name == "Ganga Short Duration Fund - Direct Plan - Growth"
    assert (a.units, a.nav, a.value_inr, a.cost_inr) == (1500.25, 25.33, 38000.0, 30000.0)
    assert b.name == "Kaveri Flexi Cap Fund - Regular Plan - Growth" and b.units == 250.5
    assert b.value_inr == 15631.51 and b.cost_inr is None


def test_no_pii_in_entries():
    for f in ("cas_cams.txt", "cas_kfintech.txt"):
        r = cp.parse_cas_text((FIX / f).read_text(encoding="utf-8"))
        blob = repr(r)
        for s in ("ABCDE1234F", "investor@example.com", "Test Investor", "1234567", "9876543210"):
            assert s not in blob


def test_garbage_text():
    r = cp.parse_cas_text("hello world\nnothing")
    assert r.entries == [] and r.statement_type == "UNKNOWN" and r.statement_date is None


def test_helpers():
    assert cp.to_num("1,500.250") == 1500.25 and cp.to_iso("15-Oct-2026") == "2026-10-15"
    assert cp.to_iso("15-OCT-2026") == "2026-10-15" and cp.to_iso("bad") is None


# ---- full path: sample PDF -> encrypt -> parse (fallback parser)

class FakeMeta:
    mode = "mock"

    def __init__(self):
        from app.adapters.base import FundMeta
        self.FundMeta = FundMeta
        self.items = {
            "INFSMP900701": ("900701", "Sindhu Large Cap Fund - Direct Plan - Growth", "Sindhu Mutual Fund"),
            "INFSMP900801": ("900801", "Ganga Short Duration Fund - Direct Plan - Growth", "Ganga Mutual Fund"),
        }

    def find_by_isin(self, isin):
        x = self.items.get(isin)
        if not x:
            return None
        return self.FundMeta(schemeCode=x[0], isin=isin, name=x[1], shortName=x[1], amc=x[2], category="X",
                             categoryGroup="EQUITY", planType="DIRECT", twinSchemeCode=None, launchDate=None,
                             aumInr=None, aumInr1yAgo=None, terPct=None, terAsOf=None, exitLoad=None,
                             lockInYears=None, benchmarkId=None)

    def search(self, q, limit):
        return []


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    out = tmp_path_factory.mktemp("cas") / "sample_cas.pdf"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_sample_cas_pdf.py"), str(out)], check=True,
                   cwd=str(ROOT))
    return out.read_bytes()


def encrypt(pdf_bytes: bytes, password: str) -> bytes:
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_bytes)))
    try:
        w.encrypt(password, algorithm="AES-256")
    except Exception:
        w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_bytes)))
        w.encrypt(password, algorithm="RC4-128")
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_sample_pdf_default_location_is_committed_or_generated():
    # make_sample_cas_pdf.py without args writes app/data/sample/sample_cas.pdf
    p = ROOT / "app" / "data" / "sample" / "sample_cas.pdf"
    if not p.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "make_sample_cas_pdf.py")], check=True, cwd=str(ROOT))
    assert p.read_bytes().startswith(b"%PDF")


def test_fallback_encrypted_pdf(sample_pdf):
    from app.adapters.statement_fallback import FallbackStatementParser
    enc = encrypt(sample_pdf, "SAMPLE1234")
    assert b"Sindhu" not in enc  # really encrypted
    parser = FallbackStatementParser(FakeMeta())
    res = parser.parse(enc, "SAMPLE1234", "cas.pdf")
    assert res.parser == "fallback" and res.statementType in ("CAMS", "KFINTECH", "UNKNOWN")
    assert res.statementDate == "2026-10-15"
    codes = {f["schemeCode"]: f for f in res.funds}
    assert set(codes) == {"900701", "900801"}
    f = codes["900701"]
    assert f["units"] == 812.441 and f["nav"] == 48.2201 and f["navDate"] == "2026-10-14"
    assert f["valueInr"] == 39176.5 and f["avgCostNav"] == round(35000.0 / 812.441, 4)
    assert set(f) == {"schemeCode", "isin", "name", "amc", "units", "nav", "navDate", "valueInr", "avgCostNav"}
    assert [u["name"] for u in res.unmatched] == ["Example Gilt Fund - Direct Growth"]
    assert res.unmatched[0]["reason"] == "Fund not found in fund list."
    assert res.unmatched[0]["isin"] == "INF000X01ABC"


def test_fallback_wrong_password(sample_pdf):
    from app.adapters.statement_fallback import FallbackStatementParser
    enc = encrypt(sample_pdf, "SAMPLE1234")
    with pytest.raises(ApiError) as e:
        FallbackStatementParser(FakeMeta()).parse(enc, "WRONG", "cas.pdf")
    assert e.value.code == "STATEMENT_PASSWORD_INVALID" and e.value.status == 422


def test_fallback_unreadable():
    from app.adapters.statement_fallback import FallbackStatementParser
    with pytest.raises(ApiError) as e:
        FallbackStatementParser(FakeMeta()).parse(b"not a pdf at all", "x", "x.pdf")
    assert e.value.code == "STATEMENT_UNREADABLE"
    with pytest.raises(ApiError) as e:
        FallbackStatementParser(FakeMeta()).parse(b"", "x", "x.pdf")
    assert e.value.code == "STATEMENT_UNREADABLE"


def test_unencrypted_pdf_ignores_password(sample_pdf):
    from app.adapters.statement_fallback import FallbackStatementParser
    res = FallbackStatementParser(FakeMeta()).parse(sample_pdf, "", "cas.pdf")
    assert len(res.funds) == 2


def test_casparser_mapping_pure():
    from app.adapters.statement_casparser import map_casparser_dict
    data = {
        "statement_period": {"from": "2020-04-01", "to": "2026-10-15"}, "file_type": "CAMS", "cas_type": "DETAILED",
        "investor_info": {"name": "X", "email": "x@y.z"},
        "folios": [{"folio": "123", "amc": "Sindhu Mutual Fund", "PAN": "ABCDE1234F", "schemes": [
            {"scheme": "Sindhu Large Cap Fund - Direct Plan - Growth", "isin": "INFSMP900701", "close": "812.441",
             "valuation": {"date": "2026-10-14", "nav": "48.2201", "value": "39176.50", "cost": "35000.00"}},
            {"scheme": "Zero Fund", "isin": "INFSMP900801", "close": "0.000",
             "valuation": {"date": "2026-10-14", "nav": "25.33", "value": "0.00"}}]}]}
    pt = map_casparser_dict(data)
    assert pt.statement_type == "CAMS" and pt.statement_date == "2026-10-15"
    assert len(pt.entries) == 1
    e = pt.entries[0]
    assert (e.isin, e.units, e.nav, e.nav_date, e.value_inr, e.cost_inr) == (
        "INFSMP900701", 812.441, 48.2201, "2026-10-14", 39176.5, 35000.0)
    assert "ABCDE1234F" not in repr(pt)


def test_casparser_build_raises_import_error_when_missing():
    try:
        import casparser  # noqa: F401
        pytest.skip("casparser installed")
    except ImportError:
        pass
    from app.adapters import statement_casparser
    with pytest.raises(ImportError):
        statement_casparser.build({}, {})
