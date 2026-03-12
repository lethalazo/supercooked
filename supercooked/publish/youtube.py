"""YouTube Data API integration for video uploads.

Wraps the YouTube Data API v3 using OAuth credentials from the identity vault.
Uses httpx for resumable uploads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from supercooked.identity.action_log import log_action
from supercooked.identity.vault import load_credential

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"

# 256KB chunk size for resumable uploads
CHUNK_SIZE = 256 * 1024


def _get_youtube_auth(slug: str) -> dict[str, str]:
    """Load YouTube OAuth credentials from the identity vault.

    Expects the vault to contain 'youtube' credentials with:
      - access_token
      - refresh_token (optional, for token refresh)

    The master password must be provided via the SUPERCOOKED_VAULT_PASSWORD
    environment variable.
    """
    master_password = os.environ.get("SUPERCOOKED_VAULT_PASSWORD", "")
    if not master_password:
        raise RuntimeError(
            "SUPERCOOKED_VAULT_PASSWORD environment variable not set. "
            "Required to decrypt YouTube credentials from the vault."
        )

    creds = load_credential(slug, "youtube", master_password)
    access_token = creds.get("access_token", "")
    if not access_token:
        raise RuntimeError(
            f"No access_token found in vault for identity '{slug}', platform 'youtube'. "
            f"Store credentials with: supercooked vault store {slug} youtube"
        )

    return {"Authorization": f"Bearer {access_token}"}


async def upload_video(
    slug: str,
    video_path: str | Path,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
) -> dict[str, Any]:
    """Upload a video to YouTube via the Data API v3.

    Uses resumable upload for reliability with large files.

    Args:
        slug: Identity slug.
        video_path: Path to the video file (.mp4 recommended).
        title: Video title.
        description: Video description.
        tags: List of tags/keywords.
        category_id: YouTube category ID (default "22" = People & Blogs).
        privacy_status: "private", "unlisted", or "public".

    Returns:
        YouTube API response dict containing the video resource.

    Raises:
        RuntimeError: If vault credentials are missing.
        FileNotFoundError: If the video file does not exist.
        httpx.HTTPStatusError: If the API request fails.
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_file}")

    auth_headers = _get_youtube_auth(slug)

    # Build the video metadata
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    file_size = video_file.stat().st_size

    async with httpx.AsyncClient(timeout=600.0) as client:
        # Step 1: Initiate resumable upload
        init_resp = await client.post(
            YOUTUBE_UPLOAD_URL,
            params={
                "uploadType": "resumable",
                "part": "snippet,status",
            },
            headers={
                **auth_headers,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/mp4",
            },
            content=json.dumps(body),
        )
        init_resp.raise_for_status()

        # Get the resumable upload URI
        upload_url = init_resp.headers["Location"]

        # Step 2: Upload the video file in chunks
        with open(video_file, "rb") as f:
            offset = 0
            while offset < file_size:
                chunk = f.read(CHUNK_SIZE)
                chunk_end = offset + len(chunk) - 1
                content_range = f"bytes {offset}-{chunk_end}/{file_size}"

                upload_resp = await client.put(
                    upload_url,
                    headers={
                        **auth_headers,
                        "Content-Range": content_range,
                        "Content-Type": "video/mp4",
                    },
                    content=chunk,
                )

                if upload_resp.status_code == 200:
                    # Upload complete
                    result = upload_resp.json()
                    break
                elif upload_resp.status_code == 308:
                    # Resume incomplete, continue
                    offset += len(chunk)
                else:
                    upload_resp.raise_for_status()
            else:
                raise RuntimeError(
                    "Upload completed without receiving a 200 response from YouTube."
                )

    video_id = result.get("id", "unknown")

    log_action(
        slug,
        action="upload_youtube_video",
        platform="youtube",
        details={
            "video_path": str(video_file),
            "title": title,
            "tags": tags or [],
            "privacy": privacy_status,
            "video_id": video_id,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
        },
        result=f"Uploaded video '{title}' to YouTube: {video_id}",
    )

    return result
