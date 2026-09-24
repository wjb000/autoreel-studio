"""AutoReel Studio Python sidecar — local HTTP/JSON API for the Tauri UI."""
from __future__ import annotations

import sys
from pathlib import Path

_SIDECAR = Path(__file__).resolve().parent
_ROOT = _SIDECAR.parent
for p in (_ROOT, _SIDECAR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import app_paths, get_settings
from api.health import router as health_router
from api.models import router as models_router
from api.jobs import router as jobs_router
from api.youtube import router as youtube_router
from api.publish_x import router as publish_x_router
from api.settings_api import router as settings_router

app = FastAPI(
    title="AutoReel Studio Sidecar",
    version="0.1.0",
    description="Local API for Wan 2.1 animated shorts / explainers, TTS, YouTube + X publish",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(models_router, prefix="/models", tags=["models"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(youtube_router, prefix="/youtube", tags=["youtube"])
app.include_router(publish_x_router, prefix="/x", tags=["x"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])


@app.on_event("startup")
def startup() -> None:
    paths = app_paths()
    settings = get_settings()
    print(f"[AutoReel] app data: {paths['root']}")
    print(f"[AutoReel] mock_wan={settings.mock_wan}")


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "main:app",
        host=s.sidecar_host,
        port=s.sidecar_port,
        reload=True,
    )
