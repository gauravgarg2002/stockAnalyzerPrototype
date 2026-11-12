"""Configuration: DEFAULTS (== config/app-config.example.yaml), deep-merge load, env APP_CONFIG."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {'app': {'sampleAsOf': '2026-10-30',
         'defaultIllustrativeAmountInr': 100000,
         'disclaimer': 'Information only, not investment advice.'},
 'ports': {'frontend': 5173, 'java': 8080, 'python': 8000},
 'services': {'pythonBaseUrl': 'http://localhost:8000', 'frontendBaseUrl': 'http://localhost:5173'},
 'adapters': {'broker': 'mock',
              'fundamentals': 'mock',
              'prices': 'mock',
              'surveillance': 'mock',
              'fundNav': 'mock',
              'fundMeta': 'mock',
              'fundHoldings': 'mock',
              'statement': 'auto'},
 'kite': {'mcpUrl': 'https://mcp.kite.trade/mcp',
          'apiKey': '',
          'apiSecret': '',
          'redirectUrl': 'http://localhost:8080/api/connect/kite/callback',
          'loginTimeoutSeconds': 300},
 'screener': {'baseUrl': 'https://www.screener.in', 'sessionCookie': '', 'minIntervalSeconds': 3},
 'nse': {'baseUrl': 'https://www.nseindia.com',
         'asmCsvUrl': 'https://nsearchives.nseindia.com/content/equities/asm_lt.csv',
         'gsmCsvUrl': 'https://nsearchives.nseindia.com/content/equities/gsm.csv',
         'esmCsvUrl': 'https://nsearchives.nseindia.com/content/equities/esm.csv',
         'minIntervalSeconds': 2},
 'mfapi': {'baseUrl': 'https://api.mfapi.in'},
 'amfi': {'navAllUrl': 'https://www.amfiindia.com/spages/NAVAll.txt'},
 'mfdata': {'baseUrl': 'https://mfdata.in/api/v1'},
 'llm': {'provider': 'none', 'model': '', 'apiKey': '', 'timeoutSeconds': 20},
 'cache': {'dir': '.cache',
           'fundamentalsHours': 24,
           'pricesHours': 12,
           'fundDataHours': 24,
           'surveillanceHours': 24,
           'javaResponseMinutes': 30},
 'storage': {'h2Path': './data/stockanalyzer'},
 'sizeBands': {'largeMinCrore': 100000, 'midMinCrore': 33000, 'smallMinCrore': 6000}}

DEFAULT_PATH = "../config/app-config.yaml"


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load(path: str | os.PathLike | None = None) -> dict:
    """Load config: defaults deep-merged with the user file (missing file -> defaults)."""
    p = path if path is not None else os.environ.get("APP_CONFIG", DEFAULT_PATH)
    cfg = copy.deepcopy(DEFAULTS)
    try:
        pp = Path(p)
        if pp.is_file():
            data = yaml.safe_load(pp.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                cfg = deep_merge(cfg, data)
    except (OSError, yaml.YAMLError):
        pass
    return cfg


def host() -> str:
    return os.environ.get("HOST", "127.0.0.1")


def any_mock(cfg: dict) -> bool:
    """True if any data adapter runs in mock mode (sample 'today' applies)."""
    a = cfg["adapters"]
    return any(a[k] == "mock" for k in ("broker", "fundamentals", "prices", "surveillance", "fundNav", "fundMeta", "fundHoldings"))
