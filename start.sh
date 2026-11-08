#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT_DIR/backend"
if [ ! -f ".env" ]; then
  cp .env.example .env
fi
if python3 -m venv .venv >/dev/null 2>&1 && [ -f ".venv/bin/activate" ]; then
  . .venv/bin/activate
  python3 -m pip install -r requirements.txt
else
  python3 -m pip install --break-system-packages -r requirements.txt
fi
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

cd "$ROOT_DIR/frontend"
if [ ! -f ".env" ]; then
  cp .env.example .env
fi
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev -- --host 0.0.0.0 --port 5173
