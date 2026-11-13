"""Entry point: python -m app.serve. Uses the FastAPI app if importable, else the Starlette fallback."""
from __future__ import annotations

import importlib

import uvicorn

from . import config


def load_app():
    try:
        importlib.import_module("fastapi")
        return "app.main:app"
    except ImportError:
        return "app.asgi_fallback:app"


def main() -> None:
    cfg = config.load()
    target = load_app()
    print(f"Serving {target} on {config.host()}:{cfg['ports']['python']}")
    uvicorn.run(target, host=config.host(), port=int(cfg["ports"]["python"]), log_level="info")


if __name__ == "__main__":
    main()
