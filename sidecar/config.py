"""App paths and settings for AutoReel Studio sidecar."""
from __future__ import annotations

import os
import platform
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from project root if present
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def default_app_data() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "AutoReelStudio"
    if system == "Windows":
        base = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        return Path(base) / "AutoReelStudio"
    # Linux / box
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "AutoReelStudio"


class Settings(BaseSettings):
    sidecar_host: str = "127.0.0.1"
    sidecar_port: int = 8765
    mock_wan: bool = True
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    # X / Twitter OAuth 1.0a
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    x_client_id: str = ""
    x_client_secret: str = ""
    pexels_api_key: str = ""
    # Override app data for box/dev
    app_data_dir: str = ""

    class Config:
        env_file = str(_ROOT / ".env")
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def app_paths() -> dict[str, Path]:
    s = get_settings()
    root = Path(s.app_data_dir) if s.app_data_dir else default_app_data()
    # On the Linux box during development, prefer project-local app-data
    if not s.app_data_dir and platform.system() == "Linux":
        local = _ROOT / "app-data"
        root = local
    paths = {
        "root": root,
        "models": root / "models",
        "wan": root / "models" / "wan2.1-1.3b",
        "tts": root / "models" / "kokoro",
        "llm": root / "models" / "llm",
        "output": root / "output",
        "jobs": root / "jobs",
        "tokens": root / "tokens",
        "ffmpeg": root / "bin",
        "cache": root / "cache",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths
