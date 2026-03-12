"""LATE API integration for multi-platform content publishing.

Wraps the LATE (https://late.so) API to publish content across
multiple social media platforms in a single call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from supercooked.config import get_api_key
from supercooked.identity.action_log import log_action

LATE_API_BASE = "https://api.late.so/v1"


async def publish_to_late(
    slug: str,
    content_path: str | Path,
    platforms: list[str],
    caption: str = "",
    title: str = "",
    schedule_at: str | None = None,
) -> dict[str, Any]:
    """Publish content to multiple platforms via the LATE API.

    Args:
        slug: Identity slug.
        content_path: Path to the content file (video, image).
        platforms: List of platform names (e.g. ["youtube_shorts", "tiktok", "instagram"]).
        caption: Caption/description for the post.
        title: Title for the post (used on YouTube).
        schedule_at: Optional ISO 8601 datetime to schedule the post.

    Returns:
        Response dict from the LATE API with post IDs per platform.

    Raises:
        RuntimeError: If the LATE API key is not configured.
        httpx.HTTPStatusError: If the API request fails.
        FileNotFoundError: If the content file does not exist.
    """
    api_key = get_api_key("late")

    content_file = Path(content_path)
    if not content_file.exists():
        raise FileNotFoundError(f"Content file not found: {content_file}")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    # Upload the media file first
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Upload media
        with open(content_file, "rb") as f:
            upload_resp = await client.post(
                f"{LATE_API_BASE}/media/upload",
                headers=headers,
                files={"file": (content_file.name, f, _guess_mime(content_file))},
            )
        upload_resp.raise_for_status()
        media_id = upload_resp.json()["media_id"]

        # Step 2: Create post across platforms
        post_data: dict[str, Any] = {
            "media_id": media_id,
            "platforms": platforms,
            "caption": caption,
        }
        if title:
            post_data["title"] = title
        if schedule_at:
            post_data["schedule_at"] = schedule_at

        post_resp = await client.post(
            f"{LATE_API_BASE}/posts",
            headers=headers,
            json=post_data,
        )
        post_resp.raise_for_status()
        result = post_resp.json()

    log_action(
        slug,
        action="publish_via_late",
        platform=",".join(platforms),
        details={
            "content_path": str(content_file),
            "platforms": platforms,
            "caption": caption[:100],
            "media_id": media_id,
        },
        result=f"Published to {', '.join(platforms)} via LATE",
    )

    return result


def _guess_mime(path: Path) -> str:
    """Guess MIME type from file extension."""
    mime_map = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_map.get(path.suffix.lower(), "application/octet-stream")
