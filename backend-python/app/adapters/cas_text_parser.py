"""Pure regex parser over the text lines of CAMS / KFintech consolidated account statements.

Input: the extracted text (str). Output: ParsedText. No I/O. Investor name, PAN, e-mail and folio numbers
are read only to detect block boundaries and are never returned.

Layouts are modelled on publicly documented statement layouts and are exercised on the hand-written fixtures
in tests/fixtures/cas_cams.txt and cas_kfintech.txt. UNVERIFIED AGAINST REAL STATEMENTS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

_MON = r"\d{1,2}-[A-Za-z]{3}-\d{4}"
_NUM = r"[\d,]+(?:\.\d+)?"
_AMT = rf"(?:INR|Rs\.?|₹)?\s*({_NUM})"

ISIN_RE = re.compile(r"\bISIN\s*:?\s*(INF[A-Z0-9]{9})", re.I)
ISIN_BARE_RE = re.compile(r"\b(INF[A-Z0-9]{9})\b")
FOLIO_RE = re.compile(r"^\s*Folio\s*(?:No\.?)?\s*:", re.I)
AMC_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9&.\-' ]{2,60}?(?:Mutual Fund|MF))\s*$")
PERIOD_RE = re.compile(rf"({_MON})\s*(?:To|-)\s*({_MON})", re.I)
ASON_RE = re.compile(rf"(?:Statement\s+Date|As\s+on|Valuation\s+as\s+on)\s*:?\s*({_MON})", re.I)
CLOSING_RE = re.compile(rf"Closing\s+(?:Unit\s+)?Balance\s*:?\s*({_NUM})", re.I)
OPENING_RE = re.compile(r"^\s*Opening\s+(?:Unit\s+)?Balance", re.I)
NAV_RE = re.compile(rf"NAV\s*(?:on|as\s+on)?\s*\(?\s*({_MON})\s*\)?\s*:?\s*{_AMT}", re.I)
COST_RE = re.compile(rf"(?:Total\s+)?Cost\s+Value\s*:?\s*{_AMT}", re.I)
VALUE_RE = re.compile(rf"(?:Market\s+Value|Valuation)(?:\s+on\s+{_MON})?\s*:?\s*{_AMT}", re.I)
PREFIX_CODE_RE = re.compile(r"^[A-Z0-9]{3,8}\s?-\s?(?=[A-Za-z])")
SCHEME_LABEL_RE = re.compile(r"^\s*(?:Scheme(?:\s+Name)?|MF\s+Scheme)\s*:\s*", re.I)
NOISE_RE = re.compile(
    r"\((?:Advisor|Formerly|Erstwhile|Non-Demat)[^)]*\)|Registrar\s*:?\s*\w+|\bISIN\s*:?\s*INF[A-Z0-9]{9}"
    r"|\(?\bPlan\s*:\s*\w+\)?|\bPAN\s*:\s*\w+|\bKYC\s*:\s*\w+", re.I)


@dataclass
class ParsedEntry:
    amc: str | None
    name: str
    isin: str | None
    units: float
    nav: float | None
    nav_date: str | None  # ISO
    value_inr: float | None
    cost_inr: float | None


@dataclass
class ParsedText:
    statement_type: str  # CAMS | KFINTECH | UNKNOWN
    statement_date: str | None  # ISO
    entries: list[ParsedEntry] = field(default_factory=list)


def to_num(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def to_iso(s: str | None) -> str | None:
    if not s:
        return None
    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s.strip().title(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def detect_type(text: str) -> str:
    t = text.upper()
    cams = len(re.findall(r"\bCAMS\b|COMPUTER AGE", t))
    kf = len(re.findall(r"KFIN|KARVY", t))
    if cams == kf:
        return "UNKNOWN"
    return "CAMS" if cams > kf else "KFINTECH"


def _clean_name(raw: str) -> str:
    s = SCHEME_LABEL_RE.sub("", raw)
    s = NOISE_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" -:\t")
    s = PREFIX_CODE_RE.sub("", s)
    return s.strip(" -:")


def _is_block_start(line: str) -> bool:
    return bool(FOLIO_RE.match(line) or ISIN_RE.search(line) or OPENING_RE.match(line))


def parse_cas_text(text: str) -> ParsedText:
    lines = [ln.rstrip() for ln in (text or "").replace("\r", "\n").split("\n")]
    stype = detect_type(text or "")

    sdate = None
    m = PERIOD_RE.search(text or "")
    if m:
        sdate = to_iso(m.group(2))
    else:
        m = ASON_RE.search(text or "")
        if m:
            sdate = to_iso(m.group(1))

    entries: list[ParsedEntry] = []
    amc: str | None = None
    cur_name: str | None = None
    cur_isin: str | None = None
    prev_text = ""

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if FOLIO_RE.match(line):
            cur_name, cur_isin = None, None
            prev_text = ""
            continue
        mi = ISIN_RE.search(line)
        if mi:
            cur_isin = mi.group(1).upper()
            nm = _clean_name(line)
            cur_name = nm or cur_name or _clean_name(prev_text) or None
            prev_text = ""
            continue
        mc = CLOSING_RE.search(line)
        if mc and cur_name:
            blob = line
            j = i
            while j < n and j < i + 3 and lines[j].strip() and not _is_block_start(lines[j]) \
                    and not CLOSING_RE.search(lines[j]) and not AMC_RE.match(lines[j].strip()):
                blob += " " + lines[j].strip()
                j += 1
            units = to_num(mc.group(1)) or 0.0
            mn = NAV_RE.search(blob)
            mv = VALUE_RE.search(blob)
            mcst = COST_RE.search(blob)
            nav = to_num(mn.group(2)) if mn else None
            value = to_num(mv.group(1)) if mv else None
            if value is None and nav is not None:
                value = round(units * nav, 2)
            if units > 0:
                entries.append(ParsedEntry(
                    amc=amc, name=cur_name, isin=cur_isin, units=units, nav=nav,
                    nav_date=to_iso(mn.group(1)) if mn else None, value_inr=value,
                    cost_inr=to_num(mcst.group(1)) if mcst else None))
            cur_name, cur_isin = None, None
            i = j
            continue
        ma = AMC_RE.match(line)
        if ma and "ISIN" not in line.upper() and not re.search(r"\d{2}-[A-Za-z]{3}-\d{4}", line):
            amc = ma.group(1).strip()
            prev_text = ""
            continue
        sm = SCHEME_LABEL_RE.match(line)
        if sm and not ISIN_RE.search(line):
            # KFintech style "Scheme : NAME" where the ISIN follows on a later line
            cur_name = _clean_name(line)
            continue
        prev_text = line
    return ParsedText(stype, sdate, entries)
