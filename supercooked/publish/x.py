"""X/Twitter API integration for posting tweets and threads.

Wraps the X API v2 using OAuth credentials from the identity vault.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from supercooked.identity.action_log import log_action
from supercooked.identity.vault import load_credential

X_API_BASE = "https://api.x.com/2"
X_UPLOAD_BASE = "https://upload.x.com/1.1"


def _get_x_auth_headers(slug: str) -> dict[str, str]:
    """Load X/Twitter OAuth credentials from the identity vault.

    Expects the vault to contain 'x' credentials with:
      - oauth_token
      - oauth_secret
      - api_key
      - api_secret
      - bearer_token

    The master password must be provided via the SUPERCOOKED_VAULT_PASSWORD
    environment variable.
    """
    import os

    master_password = os.environ.get("SUPERCOOKED_VAULT_PASSWORD", "")
    if not master_password:
        raise RuntimeError(
            "SUPERCOOKED_VAULT_PASSWORD environment variable not set. "
            "Required to decrypt X/Twitter credentials from the vault."
        )

    creds = load_credential(slug, "x", master_password)

    bearer_token = creds.get("bearer_token", "")
    if not bearer_token:
        raise RuntimeError(
            f"No bearer_token found in vault for identity '{slug}', platform 'x'. "
            f"Store credentials with: supercooked vault store {slug} x"
        )

    return {"Authorization": f"Bearer {bearer_token}"}


async def _upload_media(slug: str, media_path: Path) -> str:
    """Upload media to X and return the media_id.

    Uses the v1.1 media upload endpoint (chunked for large files).
    """
    import os

    master_password = os.environ.get("SUPERCOOKED_VAULT_PASSWORD", "")
    creds = load_credential(slug, "x", master_password)

    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    file_size = media_path.stat().st_size
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".webp": "image/webp",
    }
    media_type = mime_map.get(media_path.suffix.lower(), "application/octet-stream")

    headers = _get_x_auth_headers(slug)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # INIT
        init_resp = await client.post(
            f"{X_UPLOAD_BASE}/media/upload.json",
            headers=headers,
            data={
                "command": "INIT",
                "total_bytes": str(file_size),
                "media_type": media_type,
            },
        )
        init_resp.raise_for_status()
        media_id = init_resp.json()["media_id_string"]

        # APPEND (single chunk for simplicity; files >5MB should use chunked)
        with open(media_path, "rb") as f:
            append_resp = await client.post(
                f"{X_UPLOAD_BASE}/media/upload.json",
                headers=headers,
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": "0",
                },
                files={"media_data": (media_path.name, f, media_type)},
            )
        append_resp.raise_for_status()

        # FINALIZE
        finalize_resp = await client.post(
            f"{X_UPLOAD_BASE}/media/upload.json",
            headers=headers,
            data={
                "command": "FINALIZE",
                "media_id": media_id,
            },
        )
        finalize_resp.raise_for_status()

    return media_id


async def post_tweet(
    slug: str,
    text: str,
    media_path: Path | str | None = None,
) -> dict[str, Any]:
    """Post a single tweet, optionally with media.

    Args:
        slug: Identity slug.
        text: Tweet text (max 280 characters).
        media_path: Optional path to image/video to attach.

    Returns:
        X API response dict containing the tweet data.

    Raises:
        RuntimeError: If vault credentials are missing.
        httpx.HTTPStatusError: If the API request fails.
    """
    headers = _get_x_auth_headers(slug)

    payload: dict[str, Any] = {"text": text}

    # Upload media if provided
    if media_path is not None:
        media_file = Path(media_path)
        media_id = await _upload_media(slug, media_file)
        payload["media"] = {"media_ids": [media_id]}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{X_API_BASE}/tweets",
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        result = resp.json()

    log_action(
        slug,
        action="post_tweet",
        platform="x",
        details={
            "text": text[:100],
            "has_media": media_path is not None,
        },
        result=f"Posted tweet: {result.get('data', {}).get('id', 'unknown')}",
    )

    return result


async def post_thread(
    slug: str,
    tweets: list[str],
) -> list[dict[str, Any]]:
    """Post a thread of tweets (each reply to the previous).

    Args:
        slug: Identity slug.
        tweets: List of tweet texts in order.

    Returns:
        List of X API response dicts, one per tweet.

    Raises:
        ValueError: If tweets list is empty.
        RuntimeError: If vault credentials are missing.
        httpx.HTTPStatusError: If any API request fails.
    """
    if not tweets:
        raise ValueError("Thread must contain at least one tweet.")

    headers = _get_x_auth_headers(slug)
    results: list[dict[str, Any]] = []
    previous_tweet_id: str | None = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, text in enumerate(tweets):
            payload: dict[str, Any] = {"text": text}
            if previous_tweet_id is not None:
                payload["reply"] = {"in_reply_to_tweet_id": previous_tweet_id}

            resp = await client.post(
                f"{X_API_BASE}/tweets",
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
            results.append(result)
            previous_tweet_id = result.get("data", {}).get("id")

    log_action(
        slug,
        action="post_thread",
        platform="x",
        details={
            "tweet_count": len(tweets),
            "first_tweet": tweets[0][:80],
        },
        result=f"Posted thread of {len(tweets)} tweets",
    )

    return results
