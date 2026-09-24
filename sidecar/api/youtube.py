from __future__ import annotations

import json
import threading
import webbrowser
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import app_paths, get_settings

router = APIRouter()

_auth_state: dict[str, Any] = {
    "status": "disconnected",
    "channel_name": None,
    "channel_id": None,
    "error": None,
}
_lock = threading.Lock()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _token_path() -> Path:
    return app_paths()["tokens"] / "youtube_token.json"


def _load_credentials():
    """Return google credentials or None."""
    settings = get_settings()
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        return None
    token_file = _token_path()
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        return creds if creds and creds.valid else None
    except Exception:
        return None


def _refresh_status() -> dict:
    settings = get_settings()
    with _lock:
        if not settings.youtube_client_id or not settings.youtube_client_secret:
            _auth_state.update(
                {
                    "status": "needs_config",
                    "channel_name": None,
                    "channel_id": None,
                    "error": "Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env",
                }
            )
            return dict(_auth_state)

        creds = _load_credentials()
        if not creds:
            _auth_state.update(
                {
                    "status": "disconnected",
                    "channel_name": None,
                    "channel_id": None,
                    "error": None,
                }
            )
            return dict(_auth_state)

        try:
            from googleapiclient.discovery import build

            yt = build("youtube", "v3", credentials=creds)
            resp = yt.channels().list(part="snippet", mine=True).execute()
            items = resp.get("items", [])
            if items:
                sn = items[0]["snippet"]
                _auth_state.update(
                    {
                        "status": "connected",
                        "channel_name": sn.get("title"),
                        "channel_id": items[0]["id"],
                        "error": None,
                    }
                )
            else:
                _auth_state.update(
                    {"status": "connected", "channel_name": "(no channel)", "error": None}
                )
        except Exception as e:
            _auth_state.update({"status": "error", "error": str(e)})
        return dict(_auth_state)


@router.get("/auth/status")
def auth_status():
    return _refresh_status()


@router.post("/auth/start")
def auth_start():
    """Start installed-app OAuth with loopback redirect (localhost)."""
    settings = get_settings()
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        raise HTTPException(
            400,
            "Missing YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET. Copy .env.example to .env and fill in.",
        )
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        client_config = {
            "installed": {
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost", "http://127.0.0.1"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        # run_local_server opens browser and listens on a free localhost port
        creds = flow.run_local_server(port=0, open_browser=True, prompt="consent")
        token_file = _token_path()
        token_file.write_text(creds.to_json())
        return _refresh_status()
    except Exception as e:
        with _lock:
            _auth_state["status"] = "error"
            _auth_state["error"] = str(e)
        raise HTTPException(500, str(e))


@router.post("/auth/disconnect")
def auth_disconnect():
    tp = _token_path()
    if tp.exists():
        tp.unlink()
    with _lock:
        _auth_state.update(
            {
                "status": "disconnected",
                "channel_name": None,
                "channel_id": None,
                "error": None,
            }
        )
    return dict(_auth_state)


class UploadRequest(BaseModel):
    video_path: str
    title: str
    description: str = ""
    tags: list[str] = []
    privacy: str = "private"  # private | unlisted | public
    thumbnail_path: Optional[str] = None
    category_id: str = "22"  # People & Blogs


@router.post("/upload")
def upload_video(req: UploadRequest):
    creds = _load_credentials()
    if not creds:
        raise HTTPException(401, "Not connected to YouTube. Complete OAuth first.")
    path = Path(req.video_path)
    if not path.exists():
        raise HTTPException(404, f"Video not found: {req.video_path}")

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        yt = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": req.title[:100],
                "description": req.description,
                "tags": req.tags,
                "categoryId": req.category_id,
            },
            "status": {"privacyStatus": req.privacy, "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)
        request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
        video_id = response["id"]

        if req.thumbnail_path and Path(req.thumbnail_path).exists():
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(req.thumbnail_path),
            ).execute()

        return {
            "ok": True,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy": req.privacy,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
