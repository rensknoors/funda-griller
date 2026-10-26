#!/usr/bin/env bash
# Start backend (:8000) and frontend (:5173). Ctrl-C stops both.
# Refuses to start when a port is taken: otherwise the frontend talks to whatever holds :8000.
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=8000
WEB_PORT=5173

for port in "$API_PORT" "$WEB_PORT"; do
  if holder=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -n +2) && [ -n "$holder" ]; then
    echo "Port $port is already in use:" >&2
    echo "$holder" >&2
    echo "Stop that process (kill <PID>) and run ./dev.sh again." >&2
    exit 1
  fi
done

(cd backend && uv sync --quiet)
(cd frontend && npm install --silent)

trap 'kill 0' EXIT INT TERM

(cd backend && uv run uvicorn app.main:create_app --factory --reload --port "$API_PORT") &
backend=$!

# Only start the frontend once this backend answers.
for _ in $(seq 1 60); do
  if ! kill -0 "$backend" 2>/dev/null; then
    echo "Backend failed to start; see the output above." >&2
    exit 1
  fi
  if curl -fsS -m 2 "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -fsS -m 2 "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
  echo "Backend did not answer on :$API_PORT within 30 seconds." >&2
  exit 1
fi

(cd frontend && npx vp dev --port "$WEB_PORT" --strictPort) &

wait
