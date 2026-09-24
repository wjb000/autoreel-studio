#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export MOCK_WAN=1
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pipeline.runner --topic "${1:-demo topic}" --niche "${2:-interesting facts}" --mock-wan --job-id "cli$(date +%s | tail -c 5)"
