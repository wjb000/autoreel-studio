"""X (Twitter) media upload + post via OAuth 1.0a + API v2 tweets.

Practical path: upload media with v1.1 media/upload, then create a tweet with
API v2 POST /2/tweets including media_ids. Requires consumer key/secret and
access token/secret from the X Developer Portal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings

router = APIRouter()

UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEET_URL = "https://api.twitter.com/2/tweets"


def _x_keys() -> dict[str, str]:
    s = get_settings()
    return {
        "api_key": (s.x_api_key or "").strip(),
        "api_secret": (s.x_api_secret or "").strip(),
        "access_token": (s.x_access_token or "").strip(),
        "access_token_secret": (s.x_access_token_secret or "").strip(),
    }


def _keys_present(keys: dict[str, str]) -> bool:
    return all(keys.values())


def _oauth1_session(keys: dict[str, str]):
    from requests_oauthlib import OAuth1Session

    return OAuth1Session(
        keys["api_key"],
        client_secret=keys["api_secret"],
        resource_owner_key=keys["access_token"],
        resource_owner_secret=keys["access_token_secret"],
    )


@router.get("/status")
def x_status():
    keys = _x_keys()
    if not _keys_present(keys):
        return {
            "status": "needs_config",
            "platform": "x",
            "connected": False,
            "error": (
                "Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, and "
                "X_ACCESS_TOKEN_SECRET in .env"
            ),
        }
    # Lightweight credential check: verify credentials endpoint
    try:
        session = _oauth1_session(keys)
        r = session.get(
            "https://api.twitter.com/1.1/account/verify_credentials.json",
            params={"skip_status": "true", "include_entities": "false"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "status": "connected",
                "platform": "x",
                "connected": True,
                "username": data.get("screen_name"),
                "user_id": str(data.get("id_str") or data.get("id") or ""),
                "error": None,
            }
        return {
            "status": "error",
            "platform": "x",
            "connected": False,
            "error": f"X auth check failed ({r.status_code}): {r.text[:300]}",
        }
    except Exception as e:
        return {
            "status": "error",
            "platform": "x",
            "connected": False,
            "error": str(e),
        }


class XPublishRequest(BaseModel):
    video_path: str
    text: str = Field(..., min_length=1, max_length=280)
    dry_run: bool = False


def _upload_media(session, video_path: Path) -> str:
    """Chunked upload for video (or simple upload for small files). Returns media_id_string."""
    size = video_path.stat().st_size
    mime = "video/mp4"
    # INIT
    init = session.post(
        UPLOAD_URL,
        data={
            "command": "INIT",
            "total_bytes": size,
            "media_type": mime,
            "media_category": "tweet_video",
        },
        timeout=60,
    )
    if init.status_code not in (200, 201, 202):
        raise RuntimeError(f"X media INIT failed ({init.status_code}): {init.text[:400]}")
    media_id = init.json().get("media_id_string") or str(init.json().get("media_id"))
    if not media_id:
        raise RuntimeError(f"X media INIT missing media_id: {init.text[:400]}")

    # APPEND in chunks
    chunk_size = 4 * 1024 * 1024
    segment = 0
    with video_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            append = session.post(
                UPLOAD_URL,
                data={"command": "APPEND", "media_id": media_id, "segment_index": segment},
                files={"media": ("chunk", chunk, "application/octet-stream")},
                timeout=120,
            )
            if append.status_code not in (200, 201, 202, 204):
                raise RuntimeError(
                    f"X media APPEND failed ({append.status_code}): {append.text[:400]}"
                )
            segment += 1

    # FINALIZE
    fin = session.post(
        UPLOAD_URL,
        data={"command": "FINALIZE", "media_id": media_id},
        timeout=60,
    )
    if fin.status_code not in (200, 201):
        raise RuntimeError(f"X media FINALIZE failed ({fin.status_code}): {fin.text[:400]}")

    # Poll STATUS if processing_info present
    info = fin.json().get("processing_info")
    import time

    while info and info.get("state") in ("pending", "in_progress"):
        wait = int(info.get("check_after_secs", 2))
        time.sleep(min(wait, 15))
        st = session.get(
            UPLOAD_URL,
            params={"command": "STATUS", "media_id": media_id},
            timeout=30,
        )
        if st.status_code != 200:
            break
        info = st.json().get("processing_info")
        if info and info.get("state") == "failed":
            raise RuntimeError(f"X media processing failed: {info}")

    return media_id


@router.post("/publish")
def publish_to_x(req: XPublishRequest):
    keys = _x_keys()
    if not _keys_present(keys):
        raise HTTPException(
            400,
            "Missing X API credentials. Set X_API_KEY, X_API_SECRET, "
            "X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET in .env",
        )

    path = Path(req.video_path)
    if not path.exists():
        raise HTTPException(404, f"Video not found: {req.video_path}")

    if req.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "platform": "x",
            "message": "Credentials present; dry_run skipped upload",
            "video_path": str(path),
            "text": req.text,
        }

    try:
        session = _oauth1_session(keys)
        media_id = _upload_media(session, path)
        tweet = session.post(
            TWEET_URL,
            json={"text": req.text, "media": {"media_ids": [media_id]}},
            timeout=60,
        )
        if tweet.status_code not in (200, 201):
            raise RuntimeError(f"X tweet create failed ({tweet.status_code}): {tweet.text[:400]}")
        data = tweet.json().get("data") or {}
        tweet_id = data.get("id")
        return {
            "ok": True,
            "platform": "x",
            "media_id": media_id,
            "tweet_id": tweet_id,
            "url": f"https://x.com/i/status/{tweet_id}" if tweet_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/platforms")
def list_platforms():
    """Connected / available publish targets for the Publish UI."""
    from api.youtube import _refresh_status as yt_status

    yt = yt_status()
    x = x_status()
    return {
        "platforms": [
            {
                "id": "youtube",
                "name": "YouTube",
                "status": yt.get("status"),
                "detail": yt.get("channel_name") or yt.get("error"),
                "available": True,
            },
            {
                "id": "x",
                "name": "X (Twitter)",
                "status": x.get("status"),
                "detail": x.get("username") or x.get("error"),
                "available": True,
            },
            {
                "id": "tiktok",
                "name": "TikTok",
                "status": "coming_soon",
                "detail": "Coming soon",
                "available": False,
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "status": "coming_soon",
                "detail": "Coming soon",
                "available": False,
            },
        ]
    }
