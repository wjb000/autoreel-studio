from __future__ import annotations

import platform
import shutil
from pathlib import Path

import psutil
from fastapi import APIRouter

from config import app_paths, get_settings

router = APIRouter()


def _gpu_info() -> dict:
    info = {"available": False, "name": None, "backend": "cpu", "vram_gb": None}
    # CUDA
    try:
        import torch

        if torch.cuda.is_available():
            info["available"] = True
            info["backend"] = "cuda"
            info["name"] = torch.cuda.get_device_name(0)
            try:
                props = torch.cuda.get_device_properties(0)
                info["vram_gb"] = round(props.total_memory / (1024**3), 1)
            except Exception:
                pass
            return info
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["available"] = True
            info["backend"] = "mps"
            info["name"] = "Apple Silicon (MPS)"
            return info
    except ImportError:
        pass
    # Heuristic for Apple Silicon without torch
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        info["name"] = "Apple Silicon (torch not installed)"
        info["backend"] = "mps-capable"
    return info


@router.get("/health")
def health():
    return {"status": "ok", "service": "autoreel-sidecar", "version": "0.1.0"}


@router.get("/system")
def system_info():
    paths = app_paths()
    disk = shutil.disk_usage(str(paths["root"]))
    mem = psutil.virtual_memory()
    cpu_count = psutil.cpu_count(logical=True) or 1
    settings = get_settings()
    ffmpeg = shutil.which("ffmpeg")
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": cpu_count,
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_gb": round(mem.total / (1024**3), 1),
        "ram_available_gb": round(mem.available / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "gpu": _gpu_info(),
        "ffmpeg": ffmpeg or "not found",
        "mock_wan": settings.mock_wan,
        "app_data": str(paths["root"]),
        "recommended_ram_gb": 16,
        "ready_for_wan": mem.total >= 12 * (1024**3),
    }
