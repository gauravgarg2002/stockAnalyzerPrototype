"""Pure HTML parsing for public company pages (stdlib html.parser only; no I/O).

The fetch site's name must not appear in any user-facing string; this module only returns plain dicts.
UNVERIFIED AGAINST LIVE SERVICE: the element ids/classes below mirror the publicly visible page layout
(top ratios list, sections #quarters, #profit-loss, #balance-sheet, #shareholding, #peers) and are exercised
only on the hand-written fixture in tests/fixtures/screener_tcs.html.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

_VOID = {"br", "hr", "img", "input", "meta", "link", "col", "area", "base", "source", "wbr"}
_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*|-?\.\d+")


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def parse_number(text: str | None) -> float | None:
    """'1,23,456.7' -> 123456.7; '26%' -> 26.0; '₹ 3,925' -> 3925.0; '' / '—' -> None. First number only."""
    if text is None:
        return None
    t = clean_text(text)
    if not t or t in {"-", "--", "—", "–", "NA", "N/A"}:
        return None
    m = _NUM_RE.search(t.replace("₹", " "))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_numbers(text: str | None) -> list[float]:
    t = clean_text(text or "").replace("₹", " ")
    out = []
    for m in _NUM_RE.finditer(t):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str, frozenset]] = []
        self.h1 = ""
        self.about_parts: list[str] = []
        self.sections: dict[str, list[list[list[str]]]] = {}  # section id -> tables -> rows -> cells
        self.top_ratios: list[tuple[str, str]] = []
        self.links: list[tuple[str, dict[str, str], str]] = []  # (href, attrs, text) of anchors
        self._cur_table: list[list[str]] | None = None
        self._cur_row: list[str] | None = None
        self._cur_cell: list[str] | None = None
        self._li_name: list[str] | None = None
        self._li_vals: list[list[str]] | None = None
        self._span_kind: str | None = None
        self._span_buf: list[str] | None = None
        self._li_pairs_name = ""
        self._li_pairs_vals: list[str] = []
        self._a_attrs: dict[str, str] | None = None
        self._a_buf: list[str] | None = None
        self._h1_buf: list[str] | None = None

    # ---- helpers
    def _in(self, tag: str) -> bool:
        return any(t == tag for t, _, _ in self.stack)

    def _section_id(self) -> str | None:
        for t, i, _ in reversed(self.stack):
            if t == "section" and i:
                return i
        return None

    def _in_id(self, ident: str) -> bool:
        return any(i == ident for _, i, _ in self.stack)

    def _in_class(self, cls: str) -> bool:
        return any(cls in c for _, _, c in self.stack)

    # ---- events
    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        classes = frozenset(a.get("class", "").split())
        if tag in _VOID:
            if tag == "br" and self._cur_cell is not None:
                self._cur_cell.append(" ")
            return
        self.stack.append((tag, a.get("id", ""), classes))
        if tag == "h1" and not self.h1:
            self._h1_buf = []
        elif tag == "table":
            self._cur_table = []
        elif tag == "tr" and self._cur_table is not None:
            self._cur_row = []
        elif tag in ("td", "th") and self._cur_row is not None:
            self._cur_cell = []
        elif tag == "li" and self._in_id("top-ratios"):
            self._li_pairs_name = ""
            self._li_pairs_vals = []
        elif tag == "span" and self._in_id("top-ratios"):
            if "name" in classes:
                self._span_kind, self._span_buf = "name", []
            elif "number" in classes:
                self._span_kind, self._span_buf = "number", []
        elif tag == "a":
            self._a_attrs, self._a_buf = a, []

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if tag == "h1" and self._h1_buf is not None:
            self.h1 = clean_text("".join(self._h1_buf))
            self._h1_buf = None
        elif tag in ("td", "th") and self._cur_cell is not None and self._cur_row is not None:
            self._cur_row.append(clean_text("".join(self._cur_cell)))
            self._cur_cell = None
        elif tag == "tr" and self._cur_row is not None and self._cur_table is not None:
            if self._cur_row:
                self._cur_table.append(self._cur_row)
            self._cur_row = None
        elif tag == "table" and self._cur_table is not None:
            sid = self._section_id() or "_none"
            self.sections.setdefault(sid, []).append(self._cur_table)
            self._cur_table = None
        elif tag == "span" and self._span_buf is not None:
            txt = clean_text("".join(self._span_buf))
            if self._span_kind == "name":
                self._li_pairs_name = txt
            elif self._span_kind == "number":
                self._li_pairs_vals.append(txt)
            self._span_kind, self._span_buf = None, None
        elif tag == "li" and self._in_id("top-ratios") and self._li_pairs_name:
            self.top_ratios.append((self._li_pairs_name, " / ".join(self._li_pairs_vals)))
            self._li_pairs_name, self._li_pairs_vals = "", []
        elif tag == "a" and self._a_buf is not None:
            self.links.append((self._a_attrs.get("href", "") if self._a_attrs else "",
                               self._a_attrs or {}, clean_text("".join(self._a_buf))))
            self._a_attrs, self._a_buf = None, None
        # pop to matching open tag (tolerate unclosed tags)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._h1_buf is not None:
            self._h1_buf.append(data)
        if self._cur_cell is not None:
            self._cur_cell.append(data)
        if self._span_buf is not None:
            self._span_buf.append(data)
        if self._a_buf is not None:
            self._a_buf.append(data)
        if self._in_class("about") and not self._in("script") and not self._in("style"):
            self.about_parts.append(data)


def _table_to_series(table: list[list[str]]) -> dict[str, Any]:
    """First row = header labels (first cell blank). Returns {'periods': [...], 'rows': {label: [float|None]}}."""
    if not table:
        return {"periods": [], "rows": {}}
    header = table[0]
    periods = header[1:]
    rows: dict[str, list[float | None]] = {}
    for r in table[1:]:
        if not r:
            continue
        label = re.sub(r"\s*[+\-]$", "", r[0]).strip()
        vals = [parse_number(c) for c in r[1:]]
        vals += [None] * (len(periods) - len(vals))
        if label and label not in rows:
            rows[label] = vals[: len(periods)]
    return {"periods": periods, "rows": rows}


def _peers_table(table: list[list[str]]) -> dict[str, Any]:
    if not table:
        return {"columns": [], "rows": []}
    header = [clean_text(h) for h in table[0]]
    rows = []
    for r in table[1:]:
        if len(r) < 2 or not r[1]:
            continue
        # skip the trailing "Median" row; keep it separately
        rows.append({header[i] if i < len(header) else str(i): r[i] for i in range(len(r))})
    return {"columns": header, "rows": rows}


def parse_company_page(html: str) -> dict[str, Any]:
    """Return a plain dict:
    name, symbol, about, sector, industry, topRatios{name: float|None}, topRatiosRaw{name: text},
    quarterly/annual/balanceSheet/shareholding {periods, rows}, peers {columns, rows, median}.
    Missing sections give empty structures; never raises on odd HTML."""
    c = _Collector()
    try:
        c.feed(html or "")
        c.close()
    except Exception:  # html.parser is lenient, but never let a bad page crash a request
        pass

    def first_table(sid: str) -> list[list[str]]:
        t = c.sections.get(sid) or []
        return t[0] if t else []

    sector = industry = None
    symbol = None
    for href, attrs, text in c.links:
        title = attrs.get("title", "")
        if title.lower() in {"broad sector", "sector"} and sector is None:
            sector = text
        elif title.lower() in {"industry", "broad industry"} and industry is None:
            industry = text
        if symbol is None:
            m = re.search(r"nseindia\.com/get-quotes/equity\?symbol=([A-Za-z0-9&\-]+)", href)
            if m:
                symbol = m.group(1).upper()
    top_raw = {n: v for n, v in c.top_ratios}
    top = {}
    for n, v in c.top_ratios:
        nums = parse_numbers(v)
        top[n] = nums[0] if nums else None
        if len(nums) == 2:  # "High / Low"
            top[n + " (2)"] = nums[1]

    peers_tbl = first_table("peers")
    peers = _peers_table(peers_tbl)
    median = None
    members = []
    for r in peers["rows"]:
        if any(str(v).lower().startswith("median") for v in list(r.values())[:2]):
            median = r
        else:
            members.append(r)
    peers["rows"] = members
    peers["median"] = median

    return {
        "name": c.h1 or None,
        "symbol": symbol,
        "about": clean_text(" ".join(c.about_parts)) or None,
        "sector": sector,
        "industry": industry,
        "topRatios": top,
        "topRatiosRaw": top_raw,
        "quarterly": _table_to_series(first_table("quarters")),
        "annual": _table_to_series(first_table("profit-loss")),
        "balanceSheet": _table_to_series(first_table("balance-sheet")),
        "shareholding": _table_to_series(first_table("shareholding")),
        "peers": peers,
    }


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def period_to_date(label: str) -> str | None:
    """'Mar 2026' -> '2026-03-31' (month end)."""
    m = re.match(r"^([A-Za-z]{3})[a-z]*\s+(\d{4})$", clean_text(label))
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    mon, yr = _MONTHS[m.group(1).lower()], int(m.group(2))
    import calendar

    return f"{yr:04d}-{mon:02d}-{calendar.monthrange(yr, mon)[1]:02d}"
