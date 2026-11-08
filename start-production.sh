#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

export APP_ENV="${APP_ENV:-production}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export FRONTEND_DIST_DIR="${FRONTEND_DIST_DIR:-$ROOT_DIR/frontend/dist}"
export COOKIE_SAMESITE="${COOKIE_SAMESITE:-lax}"
export WEBRTC_FALLBACK="${WEBRTC_FALLBACK:-true}"

cd "$ROOT_DIR/backend"
exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
