#!/usr/bin/env bash
# Starts the Python service, the Java backend and the frontend dev server. Ctrl+C stops all three.
# Needs: Python 3.11+, Java 21 + Maven, Node 20+. Runs in mock mode unless config/app-config.yaml says otherwise.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/.run"
export APP_CONFIG="${APP_CONFIG:-$ROOT/config/app-config.yaml}"

pids=()
cleanup() {
  echo
  echo "Stopping services..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[1/3] Python service (logs: .run/python.log)"
cd "$ROOT/backend-python"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/pip install -q -r requirements-optional.txt || echo "  optional packages not installed (statement parsing uses the built-in fallback)"
fi
.venv/bin/python -m app.serve >"$ROOT/.run/python.log" 2>&1 &
pids+=($!)

echo "[2/3] Java backend (logs: .run/java.log)"
cd "$ROOT/backend-java"
mvn -q spring-boot:run >"$ROOT/.run/java.log" 2>&1 &
pids+=($!)

echo "[3/3] Frontend"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
pids+=($!)

echo
echo "Frontend  http://localhost:5173"
echo "Java API  http://localhost:8080/api/meta"
echo "Python    http://localhost:8000/internal/health"
wait
