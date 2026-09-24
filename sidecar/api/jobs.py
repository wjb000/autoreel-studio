from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import app_paths

router = APIRouter()

_jobs: dict[str, dict[str, Any]] = {}
_events: dict[str, list[dict[str, Any]]] = {}
_lock = threading.Lock()


class CreateJobRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    niche: str = "general facts"
    duration: str = "short"  # short | medium | long
    voice: str = "default"
    upload: bool = False
    privacy: str = "private"  # private | unlisted | public
    mock: bool = True
    # Content mode: animated_short | explainer (default keeps prior API behavior)
    mode: str = "explainer"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(job_id: str, stage: str, progress: float, message: str, **extra: Any) -> None:
    evt = {
        "ts": _now(),
        "stage": stage,
        "progress": round(progress, 3),
        "message": message,
        **extra,
    }
    with _lock:
        _events.setdefault(job_id, []).append(evt)
        if job_id in _jobs:
            _jobs[job_id]["stage"] = stage
            _jobs[job_id]["progress"] = evt["progress"]
            _jobs[job_id]["message"] = message
            if stage == "done":
                _jobs[job_id]["status"] = "completed"
            elif stage == "error":
                _jobs[job_id]["status"] = "failed"


def _run_job(job_id: str, req: CreateJobRequest) -> None:
    from pipeline.runner import run_pipeline

    try:
        with _lock:
            _jobs[job_id]["status"] = "running"
        out = run_pipeline(
            job_id=job_id,
            topic=req.topic,
            niche=req.niche,
            duration=req.duration,
            voice=req.voice,
            mock=req.mock,
            mode=req.mode,
            emit=lambda stage, prog, msg, **kw: _emit(job_id, stage, prog, msg, **kw),
        )
        with _lock:
            _jobs[job_id]["output"] = out
            _jobs[job_id]["finished_at"] = _now()
        _emit(job_id, "done", 1.0, "Video ready", output=out)
    except Exception as e:
        _emit(job_id, "error", 0.0, str(e))
        with _lock:
            _jobs[job_id]["finished_at"] = _now()
            _jobs[job_id]["error"] = str(e)


@router.post("")
def create_job(req: CreateJobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    paths = app_paths()
    job_dir = paths["jobs"] / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "id": job_id,
        "topic": req.topic,
        "niche": req.niche,
        "duration": req.duration,
        "voice": req.voice,
        "upload": req.upload,
        "privacy": req.privacy,
        "mock": req.mock,
        "mode": req.mode,
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "message": "Queued",
        "created_at": _now(),
        "finished_at": None,
        "output": None,
        "error": None,
        "job_dir": str(job_dir),
    }
    with _lock:
        _jobs[job_id] = record
        _events[job_id] = []
    background_tasks.add_task(_run_job, job_id, req)
    return record


@router.get("")
def list_jobs():
    with _lock:
        jobs = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)
    return {"jobs": jobs}


@router.get("/{job_id}")
def get_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}/events")
async def job_events(job_id: str):
    with _lock:
        if job_id not in _jobs:
            raise HTTPException(404, "Job not found")

    async def gen() -> AsyncGenerator[str, None]:
        idx = 0
        while True:
            with _lock:
                evts = list(_events.get(job_id, []))
                status = _jobs.get(job_id, {}).get("status")
            while idx < len(evts):
                yield f"data: {json.dumps(evts[idx])}\n\n"
                idx += 1
            if status in ("completed", "failed"):
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream")
