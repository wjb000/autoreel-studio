#!/usr/bin/env bash
# Build macOS .app / .dmg — must run on a Mac with Xcode CLT.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: macOS builds require a Mac. This Linux box cannot produce .dmg/.app."
  echo "Copy this repo to your Mac, then re-run this script."
  exit 1
fi

echo "→ npm install"
npm install

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r sidecar/requirements.txt
fi

# Universal tip: build separately for arm64 and x86_64, or use --target
ARCH="$(uname -m)"
echo "→ Building for $ARCH"
npm run tauri build

echo ""
echo "Artifacts under src-tauri/target/release/bundle/"
echo "  - macos/*.app"
echo "  - dmg/*.dmg"
echo ""
echo "Apple Silicon (arm64) and Intel (x86_64):"
echo "  npm run tauri build -- --target aarch64-apple-darwin"
echo "  npm run tauri build -- --target x86_64-apple-darwin"
echo "Packaging the Python sidecar into the app bundle is a follow-up:"
echo "  ship .venv or a PyInstaller binary under resources/ and start it from Rust setup()."
