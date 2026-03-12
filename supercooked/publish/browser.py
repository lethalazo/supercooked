"""Browser automation publishing via Stagehand.

Wraps the Stagehand browser automation tool for publishing content
to platforms that lack a proper API (e.g. TikTok, Instagram).
Requires the Stagehand server to be running.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from supercooked.identity.action_log import log_action

STAGEHAND_BASE = "http://localhost:3000"


async def _check_stagehand() -> None:
    """Verify Stagehand server is running and reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{STAGEHAND_BASE}/health")
            resp.raise_for_status()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
        raise RuntimeError(
            "Stagehand browser automation server is not available. "
            "Start Stagehand with: npx stagehand start\n"
            f"Connection error: {e}"
        )


async def browser_publish(
    slug: str,
    platform: str,
    content_path: str | Path,
    caption: str = "",
) -> dict[str, Any]:
    """Publish content via browser automation for platforms without API access.

    Uses Stagehand to automate the browser-based upload flow for platforms
    like TikTok and Instagram that require browser interaction.

    Args:
        slug: Identity slug.
        platform: Target platform ("tiktok", "instagram", "linkedin", etc.).
        content_path: Path to the content file to upload.
        caption: Post caption/description.

    Returns:
        Dict with publish result including status and any platform response.

    Raises:
        RuntimeError: If Stagehand is not running or the automation fails.
        FileNotFoundError: If the content file does not exist.
        ValueError: If the platform is not supported for browser automation.
    """
    await _check_stagehand()

    content_file = Path(content_path)
    if not content_file.exists():
        raise FileNotFoundError(f"Content file not found: {content_file}")

    supported_platforms = {"tiktok", "instagram", "linkedin", "facebook", "pinterest"}
    if platform.lower() not in supported_platforms:
        raise ValueError(
            f"Platform '{platform}' is not supported for browser automation. "
            f"Supported: {', '.join(sorted(supported_platforms))}"
        )

    # Build the Stagehand automation script
    automation_steps = _build_upload_steps(platform.lower(), content_file, caption)

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Create a new browser session
        session_resp = await client.post(
            f"{STAGEHAND_BASE}/sessions",
            json={"browser": "chromium", "headless": True},
        )
        session_resp.raise_for_status()
        session_id = session_resp.json()["session_id"]

        try:
            # Execute the automation steps
            exec_resp = await client.post(
                f"{STAGEHAND_BASE}/sessions/{session_id}/execute",
                json={"steps": automation_steps},
                timeout=300.0,
            )
            exec_resp.raise_for_status()
            result = exec_resp.json()
        finally:
            # Always close the browser session
            await client.delete(f"{STAGEHAND_BASE}/sessions/{session_id}")

    log_action(
        slug,
        action="browser_publish",
        platform=platform,
        details={
            "content_path": str(content_file),
            "caption": caption[:100],
            "session_id": session_id,
        },
        result=f"Published to {platform} via browser automation",
    )

    return {
        "status": "published",
        "platform": platform,
        "session_id": session_id,
        "details": result,
    }


def _build_upload_steps(
    platform: str,
    content_file: Path,
    caption: str,
) -> list[dict[str, Any]]:
    """Build platform-specific Stagehand automation steps."""
    platform_urls = {
        "tiktok": "https://www.tiktok.com/upload",
        "instagram": "https://www.instagram.com/",
        "linkedin": "https://www.linkedin.com/feed/",
        "facebook": "https://www.facebook.com/",
        "pinterest": "https://www.pinterest.com/pin-creation-tool/",
    }

    url = platform_urls[platform]

    steps: list[dict[str, Any]] = [
        {"action": "navigate", "url": url},
        {"action": "wait", "selector": "body", "timeout": 10000},
        {
            "action": "upload_file",
            "file_path": str(content_file),
            "description": f"Upload {content_file.suffix} content file",
        },
    ]

    if caption:
        steps.append({
            "action": "type",
            "text": caption,
            "description": "Enter caption/description",
        })

    steps.append({
        "action": "click",
        "description": "Click publish/post button",
    })

    steps.append({
        "action": "wait",
        "timeout": 15000,
        "description": "Wait for upload to complete",
    })

    return steps
