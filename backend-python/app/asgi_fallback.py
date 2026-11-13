"""Starlette app built from routes.ROUTES (runs without FastAPI; used for local verification and as the fallback server)."""
from __future__ import annotations

import json

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route as SRoute

from . import context
from .errors import ApiError
from .routes import ROUTES


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "details": details}}, status_code=status)


def _make_endpoint(route):
    async def endpoint(request: Request):
        params = dict(request.path_params)
        try:
            if route.kind == "query":
                params.update(dict(request.query_params))
                if route.method == "POST":
                    pass
            else:
                raw = await request.body()
                try:
                    body = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    raise ApiError("BAD_REQUEST", "Request body is not valid JSON.")
                params["body"] = body
                params.update({k: v for k, v in request.query_params.items() if k not in params})
            from anyio import to_thread
            result = await to_thread.run_sync(route.handler, context.get_context(), params)
            return JSONResponse(result)
        except ApiError as e:
            return JSONResponse(e.body(), status_code=e.status)
        except Exception as e:  # last-resort: never leak internals
            return _error(500, "INTERNAL", "Unexpected error.", {"type": type(e).__name__})
    return endpoint


def create_app() -> Starlette:
    routes = [SRoute(r.path, _make_endpoint(r), methods=[r.method]) for r in ROUTES]
    return Starlette(routes=routes)


app = create_app()
