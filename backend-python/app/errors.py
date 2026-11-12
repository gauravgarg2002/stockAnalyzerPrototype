"""API errors (contract section 0.2)."""
from __future__ import annotations

from typing import Any

STATUS = {
    "BAD_REQUEST": 400,
    "NOT_FOUND": 404,
    "BROKER_NOT_CONNECTED": 409,
    "BROKER_FORBIDDEN_CALL": 403,
    "STATEMENT_PASSWORD_INVALID": 422,
    "STATEMENT_UNREADABLE": 422,
    "UPSTREAM_UNAVAILABLE": 502,
    "INTERNAL": 500,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status if status is not None else STATUS[code]
        self.message = message
        self.details = details

    def body(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


def bad_request(message: str, details: dict | None = None) -> ApiError:
    return ApiError("BAD_REQUEST", message, details)


def not_found(message: str, details: dict | None = None) -> ApiError:
    return ApiError("NOT_FOUND", message, details)


def broker_not_connected(message: str = "Broker is not connected.") -> ApiError:
    return ApiError("BROKER_NOT_CONNECTED", message)


def broker_forbidden(message: str, details: dict | None = None) -> ApiError:
    return ApiError("BROKER_FORBIDDEN_CALL", message, details)


def upstream_unavailable(message: str, details: dict | None = None) -> ApiError:
    return ApiError("UPSTREAM_UNAVAILABLE", message, details)
