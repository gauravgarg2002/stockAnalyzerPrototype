#!/usr/bin/env python3
"""Write an unencrypted text PDF that looks like a (fictional) CAMS consolidated statement.

stdlib only. Usage: python scripts/make_sample_cas_pdf.py [output_path]
Default output: app/data/sample/sample_cas.pdf. Tests encrypt a copy with pypdf (password SAMPLE1234).
Contains scheme 900701, scheme 900801 and one fund that is not in the fund list ("Example Gilt Fund").
"""
from __future__ import annotations

import sys
from pathlib import Path

LINES = [
    "CAMS Consolidated Account Statement",
    "01-Apr-2020 To 15-Oct-2026",
    "Sample statement for the prototype. Fictional funds and figures.",
    "Email Id: investor@example.com",
    "Sample Investor",
    "",
    "Sindhu Mutual Fund",
    "Folio No: 1234567/89 PAN: ABCDE1234F KYC: OK PAN: OK",
    "SIN700-Sindhu Large Cap Fund - Direct Plan - Growth - ISIN: INFSMP900701(Advisor: DIRECT) Registrar : CAMS",
    "Opening Unit Balance: 0.000",
    "Date Transaction Amount Units Price Unit Balance",
    "01-Apr-2023 Purchase 25,000.00 650.123 38.4500 650.123",
    "05-Jun-2024 Purchase 10,000.00 162.318 61.6100 812.441",
    "Closing Unit Balance: 812.441 NAV on 14-Oct-2026: INR 48.2201",
    "Total Cost Value: 35,000.00 Market Value on 14-Oct-2026: INR 39,176.50",
    "",
    "Ganga Mutual Fund",
    "Folio No: 5550001 PAN: ABCDE1234F KYC: OK PAN: OK",
    "GAN100-Ganga Short Duration Fund - Direct Plan - Growth - ISIN: INFSMP900801(Advisor: DIRECT) Registrar : CAMS",
    "Opening Unit Balance: 0.000",
    "10-Jan-2024 Purchase 30,000.00 1,500.250 20.0000 1,500.250",
    "Closing Unit Balance: 1,500.250 NAV on 14-Oct-2026: INR 25.3300",
    "Total Cost Value: 30,000.00 Market Value on 14-Oct-2026: INR 38,000.00",
    "",
    "Example Mutual Fund",
    "Folio No: 7654321 PAN: ABCDE1234F KYC: OK PAN: OK",
    "EXG1-Example Gilt Fund - Direct Growth - ISIN: INF000X01ABC(Advisor: DIRECT) Registrar : CAMS",
    "Opening Unit Balance: 100.000",
    "Closing Unit Balance: 100.000 NAV on 14-Oct-2026: INR 20.0000",
    "Total Cost Value: 1,900.00 Market Value on 14-Oct-2026: INR 2,000.00",
]


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines: list[str]) -> bytes:
    per_page = 48
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    objs: list[bytes] = []  # 1-based ids

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    add(b"")  # 1 catalog (patched)
    add(b"")  # 2 pages (patched)
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    kids = []
    for chunk in pages:
        ops = ["BT", "/F1 8 Tf", "10 TL", "36 800 Td"]
        for ln in chunk:
            ops.append(f"({_esc(ln)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1", "replace")
        cid = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        pid = add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {cid} 0 R "
                  f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode())
        kids.append(pid)
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def main(argv: list[str]) -> int:
    default = Path(__file__).resolve().parent.parent / "app" / "data" / "sample" / "sample_cas.pdf"
    path = Path(argv[1]) if len(argv) > 1 else default
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_pdf(LINES))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
