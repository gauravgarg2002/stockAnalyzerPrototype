"""FastAPI wiring built from routes.ROUTES.

NOTE: written against the FastAPI API but NOT executed in the authoring sandbox (fastapi was not installable there).
asgi_fallback.py serves the same ROUTES table and is the verified path.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import context
from .errors import ApiError
from .routes import ROUTES

app = FastAPI(title="Stock & fund checker - internal API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(ApiError)
async def _api_error(request: Request, exc: ApiError):
    return JSONResponse(exc.body(), status_code=exc.status)


@app.exception_handler(Exception)
async def _unexpected(request: Request, exc: Exception):
    return JSONResponse({"error": {"code": "INTERNAL", "message": "Unexpected error.", "details": {"type": type(exc).__name__}}}, status_code=500)


def _register(route):
    async def endpoint(request: Request):
        from starlette.concurrency import run_in_threadpool
        params = dict(request.path_params)
        if route.kind == "query":
            params.update(dict(request.query_params))
        else:
            raw = await request.body()
            try:
                params["body"] = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                raise ApiError("BAD_REQUEST", "Request body is not valid JSON.")
            params.update({k: v for k, v in request.query_params.items() if k not in params})
        result = await run_in_threadpool(route.handler, context.get_context(), params)
        return JSONResponse(result)

    endpoint.__name__ = f"{route.method.lower()}_{route.handler.__name__}"
    app.add_api_route(route.path, endpoint, methods=[route.method])


for _r in ROUTES:
    _register(_r)
