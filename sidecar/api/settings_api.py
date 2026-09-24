from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from config import app_paths

router = APIRouter()


def _settings_file() -> Path:
    return app_paths()["root"] / "user_settings.json"


DEFAULTS = {
    "default_niche": "interesting facts",
    "default_voice": "default",
    "default_duration": "short",
    "default_privacy": "private",
    "default_mode": "animated_short",
    "pexels_api_key": "",
    "output_path": "",
    "auto_upload": False,
}


def _load() -> dict[str, Any]:
    f = _settings_file()
    if f.exists():
        try:
            data = json.loads(f.read_text())
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def _save(data: dict[str, Any]) -> None:
    _settings_file().write_text(json.dumps(data, indent=2))


@router.get("")
def get_settings_api():
    s = _load()
    paths = app_paths()
    if not s.get("output_path"):
        s["output_path"] = str(paths["output"])
    # Never echo secrets from env in full — mask
    return s


class SettingsUpdate(BaseModel):
    default_niche: Optional[str] = None
    default_voice: Optional[str] = None
    default_duration: Optional[str] = None
    default_privacy: Optional[str] = None
    default_mode: Optional[str] = None
    pexels_api_key: Optional[str] = None
    output_path: Optional[str] = None
    auto_upload: Optional[bool] = None


@router.post("")
def update_settings(body: SettingsUpdate):
    s = _load()
    for k, v in body.model_dump(exclude_none=True).items():
        s[k] = v
    _save(s)
    return s
