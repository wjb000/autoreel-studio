#!/usr/bin/env bash
# Start Python sidecar + Vite (and optionally Tauri) for local development.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export MOCK_WAN="${MOCK_WAN:-1}"
export SIDECAR_HOST="${SIDECAR_HOST:-127.0.0.1}"
export SIDECAR_PORT="${SIDECAR_PORT:-8765}"

if [[ ! -d node_modules ]]; then
  echo "→ npm install"
  npm install
fi

if [[ ! -d .venv ]]; then
  echo "→ creating .venv"
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r sidecar/requirements.txt
fi

# shellcheck disable=SC1091
source .venv/bin/activate

cleanup() {
  echo "Stopping…"
  [[ -n "${SIDECAR_PID:-}" ]] && kill "$SIDECAR_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "→ sidecar on http://${SIDECAR_HOST}:${SIDECAR_PORT}"
(
  cd sidecar
  python -m uvicorn main:app --host "$SIDECAR_HOST" --port "$SIDECAR_PORT" --reload
) &
SIDECAR_PID=$!

# Wait for health
for i in {1..30}; do
  if curl -sf "http://${SIDECAR_HOST}:${SIDECAR_PORT}/health" >/dev/null; then
    echo "✓ sidecar healthy"
    break
  fi
  sleep 0.3
done

MODE="${1:-vite}"
if [[ "$MODE" == "tauri" ]]; then
  echo "→ npm run tauri dev"
  npm run tauri dev
else
  echo "→ npm run dev (Vite UI at http://localhost:1420)"
  echo "  Tip: run './scripts/dev.sh tauri' for the desktop shell"
  npm run dev
fi
