from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .config import load_config, project_root

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _paths(cfg: dict[str, Any] | None = None) -> tuple[Path, Path]:
    root = project_root()
    secrets = Path(
        os.environ.get("YOUTUBE_CLIENT_SECRETS")
        or root / "credentials" / "client_secret.json"
    )
    token = Path(os.environ.get("YOUTUBE_TOKEN") or root / "credentials" / "token.json")
    if not secrets.is_absolute():
        secrets = root / secrets
    if not token.is_absolute():
        token = root / token
    return secrets, token


def get_youtube_service(cfg: dict[str, Any] | None = None):
    secrets, token_path = _paths(cfg)
    if not secrets.exists():
        raise FileNotFoundError(
            f"Missing OAuth client secrets at {secrets}.\n"
            "1) Create a Google Cloud project\n"
            "2) Enable YouTube Data API v3\n"
            "3) Create OAuth Desktop credentials\n"
            "4) Download JSON to credentials/client_secret.json"
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    *,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy: str = "private",
    category_id: str | None = None,
    made_for_kids: bool = False,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    channel = cfg.get("channel") or {}
    privacy = privacy or str(channel.get("default_privacy") or "private")
    category_id = category_id or str(channel.get("category_id") or "23")
    tags = list(tags or [])
    defaults = channel.get("default_tags") or []
    for t in defaults:
        if t not in tags:
            tags.append(t)
    if "Shorts" not in tags:
        tags.append("Shorts")

    if not video_path.exists():
        raise FileNotFoundError(video_path)

    youtube = get_youtube_service(cfg)
    kids = bool(channel.get("made_for_kids", False))
    if made_for_kids:
        kids = True
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:500],
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": kids,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=1024 * 1024, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] Upload {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"[youtube] Uploaded: https://youtu.be/{video_id} (privacy={privacy})")
    return response
