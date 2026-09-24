# AutoReel Studio

Local AI desktop app that makes **animated short films** and monetizable short-form content, then can auto-publish to **YouTube**, **X**, and more.

Built with Tauri + React + a Python sidecar. Video generation uses **Wan 2.1** (Apache 2.0) downloaded inside the app. Scripts and voice run locally.

## Download

Once GitHub Actions has produced a release:

1. Open [Releases](https://github.com/wjb000/autoreel-studio/releases)
2. Grab the **macOS** `.dmg` / `.app` or **Windows** `.msi` / `.exe`
3. Install, open the app, download models, connect YouTube / X, create

> First public installers appear after a `v*` tag is pushed and the release workflow finishes.

## Run from source

```bash
# prerequisites: Node 20+, Rust (for Tauri), Python 3.11+, FFmpeg
cp .env.example .env
# fill YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET (and optional X keys)
python3 -m venv .venv && source .venv/bin/activate
pip install -r sidecar/requirements.txt
npm install
./scripts/dev.sh          # sidecar + Vite UI
# desktop shell:
./scripts/dev.sh tauri
```

Mock pipeline (no GPU / no Wan weights):

```bash
MOCK_WAN=1 ./scripts/run-mock-job.sh
```

## Features

- **Animated short films** — story beats → Wan clips → voice + captions → assemble
- **Explainer / facts** mode for faceless monetizable content
- **In-app model download** (Wan 2.1 T2V 1.3B default)
- **YouTube** OAuth login + upload
- **X (Twitter)** publish (API keys in Settings)
- Local Kokoro TTS when available; macOS `say` / mock fallbacks documented in code

## Hardware

- **Recommended:** Apple Silicon M1+ 16GB+ or Windows NVIDIA 8GB+ VRAM
- Wan 2.1 **1.3B** is the default consumer model; 14B is optional and heavy
- Without a GPU, use `MOCK_WAN=1` for pipeline development

## Config

See `.env.example` for YouTube OAuth, X API keys, Pexels fallback, and sidecar settings.

## License

App code: see `LICENSE`. Wan 2.1 model weights: Apache 2.0 (Wan-AI).
