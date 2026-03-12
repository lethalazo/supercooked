"""Content scheduling and calendar management.

Stores a YAML-based content schedule per identity for coordinating
when content should be published across platforms.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.action_log import log_action


def _schedule_path(slug: str) -> Path:
    """Get the schedule file path for a being."""
    return IDENTITIES_DIR / slug / "content" / "schedule.yaml"


def _load_schedule(slug: str) -> list[dict[str, Any]]:
    """Load the schedule from YAML."""
    path = _schedule_path(slug)
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("schedule", [])


def _save_schedule(slug: str, schedule: list[dict[str, Any]]) -> None:
    """Save the schedule to YAML."""
    path = _schedule_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            {"schedule": schedule},
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def schedule_content(
    slug: str,
    content_id: str,
    publish_at: str | datetime,
    platforms: list[str] | None = None,
    title: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Schedule a content piece for future publishing.

    Args:
        slug: Identity slug.
        content_id: Unique identifier for the content piece.
        publish_at: When to publish (ISO 8601 string or datetime).
        platforms: Target platforms. Defaults to all enabled platforms.
        title: Content title for the calendar view.
        notes: Additional notes about the scheduled post.

    Returns:
        The created schedule entry dict.

    Raises:
        ValueError: If publish_at cannot be parsed as a datetime.
    """
    schedule = _load_schedule(slug)

    # Parse publish_at
    if isinstance(publish_at, str):
        try:
            publish_dt = datetime.fromisoformat(publish_at)
        except ValueError:
            raise ValueError(
                f"Invalid datetime format: '{publish_at}'. "
                f"Use ISO 8601 format (e.g. '2025-01-15T14:00:00')."
            )
    else:
        publish_dt = publish_at

    entry: dict[str, Any] = {
        "content_id": content_id,
        "publish_at": publish_dt.isoformat(),
        "platforms": platforms or [],
        "title": title,
        "notes": notes,
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
    }

    schedule.append(entry)
    _save_schedule(slug, schedule)

    log_action(
        slug,
        action="schedule_content",
        details={
            "content_id": content_id,
            "publish_at": publish_dt.isoformat(),
            "platforms": platforms or [],
        },
        result=f"Scheduled content '{content_id}' for {publish_dt.isoformat()}",
    )

    return entry


def get_schedule(
    slug: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Get the full content schedule for a being.

    Args:
        slug: Identity slug.
        status: Optional filter by status ("scheduled", "published", "cancelled").

    Returns:
        List of schedule entries sorted by publish_at time.
    """
    schedule = _load_schedule(slug)

    if status is not None:
        schedule = [e for e in schedule if e.get("status") == status]

    # Sort by publish_at
    schedule.sort(key=lambda e: e.get("publish_at", ""))
    return schedule


def get_due_content(slug: str) -> list[dict[str, Any]]:
    """Get all scheduled content that is due for publishing (publish_at <= now).

    Args:
        slug: Identity slug.

    Returns:
        List of schedule entries that are due, sorted by publish_at.
    """
    now = datetime.now()
    schedule = _load_schedule(slug)

    due = []
    for entry in schedule:
        if entry.get("status") != "scheduled":
            continue
        publish_at = entry.get("publish_at", "")
        if publish_at:
            try:
                dt = datetime.fromisoformat(publish_at)
                if dt <= now:
                    due.append(entry)
            except ValueError:
                continue

    due.sort(key=lambda e: e.get("publish_at", ""))
    return due


def mark_published(slug: str, content_id: str) -> None:
    """Mark a scheduled content item as published.

    Args:
        slug: Identity slug.
        content_id: The content ID to mark as published.
    """
    schedule = _load_schedule(slug)
    for entry in schedule:
        if entry.get("content_id") == content_id and entry.get("status") == "scheduled":
            entry["status"] = "published"
            entry["published_at"] = datetime.now().isoformat()
            break
    _save_schedule(slug, schedule)


def cancel_scheduled(slug: str, content_id: str) -> None:
    """Cancel a scheduled content item.

    Args:
        slug: Identity slug.
        content_id: The content ID to cancel.
    """
    schedule = _load_schedule(slug)
    for entry in schedule:
        if entry.get("content_id") == content_id and entry.get("status") == "scheduled":
            entry["status"] = "cancelled"
            entry["cancelled_at"] = datetime.now().isoformat()
            break
    _save_schedule(slug, schedule)
