#!/usr/bin/env bash
# Makes sure backend-python/.venv exists, was built from Python 3.11+, and has the required packages.
# Picks the interpreter from $PYTHON, else the newest of python3.13 / python3.12 / python3.11 / python3.
# Safe to run every time: it only rebuilds or reinstalls when something is missing or too old.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY_DIR="$ROOT/backend-python"
VENV="$PY_DIR/.venv"

version_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; }

pick_python() {
  if [ -n "${PYTHON:-}" ]; then
    if version_ok "$PYTHON"; then echo "$PYTHON"; return 0; fi
    echo "PYTHON=$PYTHON is older than 3.11." >&2; return 1
  fi
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && version_ok "$c"; then echo "$c"; return 0; fi
  done
  return 1
}

if [ -x "$VENV/bin/python" ] && ! version_ok "$VENV/bin/python"; then
  echo "  existing .venv uses $("$VENV/bin/python" --version 2>&1); rebuilding with Python 3.11+"
  rm -rf "$VENV"
fi

if [ ! -x "$VENV/bin/python" ]; then
  if ! PY="$(pick_python)"; then
    echo "ERROR: Python 3.11 or newer is needed for the Python service." >&2
    [ -n "${PYTHON:-}" ] || echo "  python3 on your PATH is: $(python3 --version 2>&1 || echo 'not found')." >&2
    echo "  Install one (macOS: brew install python@3.12), then run again, or set PYTHON=/path/to/python3.12." >&2
    exit 1
  fi
  echo "  creating .venv with $("$PY" --version 2>&1)"
  "$PY" -m venv "$VENV"
fi

if ! "$VENV/bin/python" -c 'import uvicorn, fastapi, pydantic, yaml, requests, pypdf, pdfplumber' 2>/dev/null; then
  echo "  installing Python packages"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$PY_DIR/requirements.txt"
  "$VENV/bin/pip" install -q -r "$PY_DIR/requirements-optional.txt" \
    || echo "  optional packages not installed (statement parsing uses the built-in fallback)"
fi
