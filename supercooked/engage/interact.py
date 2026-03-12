"""Social media engagement via Stagehand browser automation.

Wraps Stagehand to perform engagement actions (like, follow, comment)
on platforms where no direct API is available or practical.
"""

from __future__ import annotations

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


async def _execute_stagehand_action(
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Execute a series of Stagehand automation steps.

    Creates a browser session, runs the steps, and closes the session.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create browser session
        session_resp = await client.post(
            f"{STAGEHAND_BASE}/sessions",
            json={"browser": "chromium", "headless": True},
        )
        session_resp.raise_for_status()
        session_id = session_resp.json()["session_id"]

        try:
            exec_resp = await client.post(
                f"{STAGEHAND_BASE}/sessions/{session_id}/execute",
                json={"steps": steps},
                timeout=120.0,
            )
            exec_resp.raise_for_status()
            result = exec_resp.json()
        finally:
            await client.delete(f"{STAGEHAND_BASE}/sessions/{session_id}")

    return result


async def like_post(
    slug: str,
    platform: str,
    post_url: str,
) -> dict[str, Any]:
    """Like/heart a post on a social media platform via browser automation.

    Args:
        slug: Identity slug.
        platform: Platform name (e.g. "instagram", "tiktok", "x").
        post_url: Direct URL to the post.

    Returns:
        Dict with the action result.

    Raises:
        RuntimeError: If Stagehand is not available.
    """
    await _check_stagehand()

    steps: list[dict[str, Any]] = [
        {"action": "navigate", "url": post_url},
        {"action": "wait", "selector": "body", "timeout": 10000},
        {
            "action": "click",
            "description": f"Click the like/heart button on this {platform} post",
        },
        {"action": "wait", "timeout": 2000, "description": "Wait for like to register"},
    ]

    result = await _execute_stagehand_action(steps)

    log_action(
        slug,
        action="like_post",
        platform=platform,
        details={
            "post_url": post_url,
        },
        result=f"Liked post on {platform}: {post_url}",
    )

    return {
        "action": "like",
        "platform": platform,
        "post_url": post_url,
        "status": "completed",
        "details": result,
    }


async def follow_user(
    slug: str,
    platform: str,
    user_url: str,
) -> dict[str, Any]:
    """Follow a user on a social media platform via browser automation.

    Args:
        slug: Identity slug.
        platform: Platform name (e.g. "instagram", "tiktok", "x").
        user_url: Direct URL to the user's profile.

    Returns:
        Dict with the action result.

    Raises:
        RuntimeError: If Stagehand is not available.
    """
    await _check_stagehand()

    steps: list[dict[str, Any]] = [
        {"action": "navigate", "url": user_url},
        {"action": "wait", "selector": "body", "timeout": 10000},
        {
            "action": "click",
            "description": f"Click the follow button on this {platform} profile",
        },
        {"action": "wait", "timeout": 2000, "description": "Wait for follow to register"},
    ]

    result = await _execute_stagehand_action(steps)

    log_action(
        slug,
        action="follow_user",
        platform=platform,
        details={
            "user_url": user_url,
        },
        result=f"Followed user on {platform}: {user_url}",
    )

    return {
        "action": "follow",
        "platform": platform,
        "user_url": user_url,
        "status": "completed",
        "details": result,
    }


async def comment_on_post(
    slug: str,
    platform: str,
    post_url: str,
    comment_text: str,
) -> dict[str, Any]:
    """Leave a comment on a post via browser automation.

    Args:
        slug: Identity slug.
        platform: Platform name.
        post_url: Direct URL to the post.
        comment_text: Text of the comment to leave.

    Returns:
        Dict with the action result.

    Raises:
        RuntimeError: If Stagehand is not available.
    """
    await _check_stagehand()

    steps: list[dict[str, Any]] = [
        {"action": "navigate", "url": post_url},
        {"action": "wait", "selector": "body", "timeout": 10000},
        {
            "action": "click",
            "description": f"Click the comment input field on this {platform} post",
        },
        {
            "action": "type",
            "text": comment_text,
            "description": "Type the comment text",
        },
        {
            "action": "click",
            "description": "Click the post/submit comment button",
        },
        {"action": "wait", "timeout": 3000, "description": "Wait for comment to post"},
    ]

    result = await _execute_stagehand_action(steps)

    log_action(
        slug,
        action="comment_on_post",
        platform=platform,
        details={
            "post_url": post_url,
            "comment": comment_text[:200],
        },
        result=f"Commented on {platform} post: {post_url}",
    )

    return {
        "action": "comment",
        "platform": platform,
        "post_url": post_url,
        "comment": comment_text,
        "status": "completed",
        "details": result,
    }
