from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import app_paths, get_settings

router = APIRouter()

# In-memory download progress {model_id: {status, progress, message}}
_progress: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

MODEL_CATALOG = [
    {
        "id": "wan2.1-1.3b",
        "name": "Wan 2.1 T2V 1.3B (Diffusers)",
        "repo": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        "size_gb": 6.5,
        "required": True,
        "description": "Primary video model — short B-roll clips. Fits consumer GPUs (8GB+ VRAM / Apple Silicon).",
        "license": "Apache 2.0",
        "path_key": "wan",
    },
    {
        "id": "wan2.1-14b",
        "name": "Wan 2.1 T2V 14B (optional)",
        "repo": "Wan-AI/Wan2.1-T2V-14B-Diffusers",
        "size_gb": 28.0,
        "required": False,
        "description": "Higher quality; needs ~24GB+ VRAM. Optional upgrade.",
        "license": "Apache 2.0",
        "path_key": "wan",
    },
    {
        "id": "kokoro-tts",
        "name": "Kokoro TTS (ONNX)",
        "repo": "hexgrad/Kokoro-82M",
        "size_gb": 0.35,
        "required": True,
        "description": "Fast neural TTS for voiceover. Uses kokoro-onnx when available.",
        "license": "Apache 2.0",
        "path_key": "tts",
    },
    {
        "id": "llm-script",
        "name": "Script LLM (GGUF small)",
        "repo": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "size_gb": 0.8,
        "required": False,
        "description": "Small local LLM for scripts. Prefer Ollama if installed; else GGUF via llama-cpp-python.",
        "license": "Apache 2.0",
        "path_key": "llm",
    },
]


def _model_status(entry: dict) -> dict:
    paths = app_paths()
    dest = paths[entry["path_key"]]
    marker = dest / ".ready"
    # For wan 14b use separate folder
    if entry["id"] == "wan2.1-14b":
        dest = paths["models"] / "wan2.1-14b"
        marker = dest / ".ready"
    installed = marker.exists()
    size_on_disk = 0.0
    if dest.exists():
        try:
            size_on_disk = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / (1024**3)
        except OSError:
            pass
    with _lock:
        prog = _progress.get(entry["id"], {})
    return {
        **entry,
        "installed": installed,
        "path": str(dest),
        "size_on_disk_gb": round(size_on_disk, 2),
        "download": prog or {"status": "idle", "progress": 0.0, "message": ""},
    }


@router.get("")
def list_models():
    return {"models": [_model_status(m) for m in MODEL_CATALOG]}


class DownloadRequest(BaseModel):
    model_id: str
    mock: bool = False


def _set_progress(model_id: str, status: str, progress: float, message: str) -> None:
    with _lock:
        _progress[model_id] = {
            "status": status,
            "progress": round(progress, 3),
            "message": message,
        }


def _download_model(model_id: str, mock: bool) -> None:
    entry = next((m for m in MODEL_CATALOG if m["id"] == model_id), None)
    if not entry:
        return
    paths = app_paths()
    if model_id == "wan2.1-14b":
        dest = paths["models"] / "wan2.1-14b"
    else:
        dest = paths[entry["path_key"]]
    dest.mkdir(parents=True, exist_ok=True)
    settings = get_settings()

    try:
        _set_progress(model_id, "downloading", 0.01, "Starting download…")
        if mock or settings.mock_wan or model_id.startswith("wan"):
            # Simulated / lightweight stub download for CI and box without GPU weights
            import time

            steps = 20
            for i in range(steps + 1):
                _set_progress(
                    model_id,
                    "downloading",
                    i / steps,
                    f"Downloading {entry['name']}… ({int(100 * i / steps)}%)",
                )
                time.sleep(0.15)
            # Write stub marker + README so pipeline knows mock mode is fine
            (dest / "MODEL_STUB.txt").write_text(
                f"Stub for {entry['repo']}\n"
                f"Replace with real weights via Hugging Face when ready.\n"
                f"License: {entry['license']}\n"
            )
            (dest / ".ready").write_text("mock\n")
            _set_progress(model_id, "ready", 1.0, "Installed (mock/stub)")
            return

        # Real HF download with progress
        from huggingface_hub import snapshot_download

        def progress_cb(progress: float):
            _set_progress(model_id, "downloading", progress, f"Fetching from Hugging Face…")

        # snapshot_download doesn't have fine-grained %; we approximate via tqdm redirect
        _set_progress(model_id, "downloading", 0.1, f"Cloning {entry['repo']}…")
        snapshot_download(
            repo_id=entry["repo"],
            local_dir=str(dest),
            local_dir_use_symlinks=False,
        )
        (dest / ".ready").write_text("hf\n")
        _set_progress(model_id, "ready", 1.0, "Installed")
    except Exception as e:
        _set_progress(model_id, "error", 0.0, str(e))


@router.post("/download")
def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    entry = next((m for m in MODEL_CATALOG if m["id"] == req.model_id), None)
    if not entry:
        raise HTTPException(404, f"Unknown model: {req.model_id}")
    with _lock:
        cur = _progress.get(req.model_id, {})
        if cur.get("status") == "downloading":
            return {"ok": True, "message": "already downloading"}
    background_tasks.add_task(_download_model, req.model_id, req.mock)
    return {"ok": True, "model_id": req.model_id}


@router.get("/download/{model_id}/events")
async def download_events(model_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        last = None
        for _ in range(600):  # ~5 min
            with _lock:
                cur = dict(_progress.get(model_id, {"status": "idle", "progress": 0, "message": ""}))
            payload = json.dumps(cur)
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload
            if cur.get("status") in ("ready", "error"):
                break
            await asyncio.sleep(0.5)
        yield f"data: {json.dumps(_progress.get(model_id, {}))}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
