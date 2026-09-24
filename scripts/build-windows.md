# Building AutoReel Studio for Windows

Run these steps on a **Windows 10/11** machine (this Linux box cannot produce `.msi` / `.exe` installers).

## Prerequisites

1. [Node.js 20+](https://nodejs.org/)
2. [Rust](https://rustup.rs/) stable
3. [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with “Desktop development with C++”
4. [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) (usually preinstalled on Win11)
5. Python 3.10+ and FFmpeg on PATH (or bundle later)

## Build

```powershell
cd youtube-factory-app
npm install
python -m venv .venv
.\.venv\Scripts\pip install -r sidecar\requirements.txt
copy .env.example .env
# Edit .env with YouTube OAuth client ID/secret

npm run tauri build
```

Artifacts:

- `src-tauri\target\release\bundle\msi\*.msi`
- `src-tauri\target\release\bundle\nsis\*.exe`

## Sidecar packaging note

For a double-clickable installer, also:

1. PyInstaller-freeze `sidecar/main.py` → `autoreel-sidecar.exe`, **or** embed a portable Python + venv.
2. Register it in `tauri.conf.json` under `bundle.externalBin` / start it from Rust `setup()`.
3. Bundle `ffmpeg.exe` under app resources.

Until then, end users can run `scripts\dev` style: start uvicorn then the UI.

## GPU (Wan 2.1)

- NVIDIA CUDA 8GB+ VRAM recommended for 1.3B
- Set `MOCK_WAN=0` after downloading real weights from Hugging Face
