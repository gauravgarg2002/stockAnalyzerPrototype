"""Statement parser without casparser: pypdf decrypt(password) -> pdfplumber text -> cas_text_parser."""
from __future__ import annotations

import io
from typing import Any

from ..errors import ApiError
from .base import ParsedStatement
from .cas_text_parser import parse_cas_text
from .isin_map import build_statement

MAX_PAGES = 400


def _unreadable(msg: str = "We could not read this statement. Please upload the PDF as downloaded from CAMS or KFintech.",
                details: dict | None = None) -> ApiError:
    return ApiError("STATEMENT_UNREADABLE", msg, details)


def decrypt_to_bytes(pdf_bytes: bytes, password: str) -> bytes:
    """Return unencrypted PDF bytes. Raises STATEMENT_PASSWORD_INVALID / STATEMENT_UNREADABLE."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.errors import PdfReadError

    if not pdf_bytes or not pdf_bytes.lstrip()[:5] == b"%PDF-":
        raise _unreadable()
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.is_encrypted:
            return pdf_bytes
        ok = reader.decrypt(password or "")
        if not ok:  # PasswordType.NOT_DECRYPTED == 0
            raise ApiError("STATEMENT_PASSWORD_INVALID",
                           "The password did not open this statement. Please check it and try again.")
        writer = PdfWriter()
        for page in reader.pages[:MAX_PAGES]:
            writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except ApiError:
        raise
    except PdfReadError as e:
        raise _unreadable(details={"reason": type(e).__name__})
    except Exception as e:  # e.g. missing crypto backend, malformed objects
        raise _unreadable(details={"reason": type(e).__name__})


def extract_text(pdf_bytes: bytes) -> str:
    import pdfplumber

    parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:MAX_PAGES]:
                parts.append(page.extract_text() or "")
    except Exception as e:
        raise _unreadable(details={"reason": type(e).__name__})
    return "\n".join(parts)


class FallbackStatementParser:
    name = "fallback"

    def __init__(self, fund_meta: Any):
        self.fund_meta = fund_meta

    def parse(self, pdf_bytes: bytes, password: str, filename: str = "") -> ParsedStatement:
        plain = decrypt_to_bytes(pdf_bytes, password)
        text = extract_text(plain)
        parsed = parse_cas_text(text)
        if not parsed.entries:
            raise _unreadable("No mutual fund holdings were found in this statement.")
        return build_statement(parsed, self.fund_meta, self.name)


def build(config: dict, deps: dict) -> FallbackStatementParser:
    return FallbackStatementParser(deps.get("fund_meta"))
