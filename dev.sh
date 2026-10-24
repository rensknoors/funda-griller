#!/usr/bin/env bash
# Start backend (:8000) and frontend (:5173). Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

(cd backend && uv sync --quiet)
(cd frontend && npm install --silent)

trap 'kill 0' EXIT INT TERM

(cd backend && uv run uvicorn app.main:create_app --factory --reload --port 8000) &
(cd frontend && npx vp dev --port 5173) &

wait
