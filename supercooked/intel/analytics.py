"""Performance tracking and analytics for content and platforms.

Stores content performance metrics and platform-level stats in YAML
files within the identity's analytics directory.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.action_log import log_action
from supercooked.identity.schemas import ContentPerformance, PlatformStats


def _content_log_path(slug: str) -> Path:
    """Path to the content performance log."""
    return IDENTITIES_DIR / slug / "analytics" / "content_log.yaml"


def _platforms_path(slug: str) -> Path:
    """Path to the platform stats file."""
    return IDENTITIES_DIR / slug / "analytics" / "platforms.yaml"


def _load_content_log(slug: str) -> list[dict[str, Any]]:
    """Load all content performance entries."""
    path = _content_log_path(slug)
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("entries", [])


def _save_content_log(slug: str, entries: list[dict[str, Any]]) -> None:
    """Save content performance entries."""
    path = _content_log_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            {"entries": entries},
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def _load_platform_stats(slug: str) -> list[dict[str, Any]]:
    """Load platform-level stats."""
    path = _platforms_path(slug)
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("platforms", [])


def _save_platform_stats(slug: str, platforms: list[dict[str, Any]]) -> None:
    """Save platform-level stats."""
    path = _platforms_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            {"platforms": platforms},
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def record_performance(
    slug: str,
    content_id: str,
    metrics: dict[str, Any],
) -> ContentPerformance:
    """Record or update performance metrics for a content piece.

    If an entry with the given content_id already exists, it is updated.
    Otherwise, a new entry is created.

    Args:
        slug: Identity slug.
        content_id: Unique content identifier.
        metrics: Dict of performance metrics. Supported keys:
            title, platform, published_at, views, likes, comments,
            shares, engagement_rate.

    Returns:
        The created/updated ContentPerformance object.
    """
    entries = _load_content_log(slug)

    # Find existing entry or create new
    existing_idx = None
    for i, entry in enumerate(entries):
        if entry.get("content_id") == content_id:
            existing_idx = i
            break

    if existing_idx is not None:
        # Update existing entry
        entries[existing_idx].update(metrics)
        entries[existing_idx]["content_id"] = content_id
        entries[existing_idx]["updated_at"] = datetime.now().isoformat()
        perf_data = entries[existing_idx]
    else:
        # Create new entry
        perf_data = {
            "content_id": content_id,
            "created_at": datetime.now().isoformat(),
            **metrics,
        }
        entries.append(perf_data)

    _save_content_log(slug, entries)

    perf = ContentPerformance(
        content_id=content_id,
        title=perf_data.get("title", ""),
        platform=perf_data.get("platform", ""),
        published_at=perf_data.get("published_at"),
        views=perf_data.get("views", 0),
        likes=perf_data.get("likes", 0),
        comments=perf_data.get("comments", 0),
        shares=perf_data.get("shares", 0),
        engagement_rate=perf_data.get("engagement_rate", 0.0),
    )

    log_action(
        slug,
        action="record_performance",
        details={
            "content_id": content_id,
            "metrics": metrics,
        },
        result=f"Recorded performance for content '{content_id}'",
    )

    return perf


def get_top_content(
    slug: str,
    limit: int = 10,
    sort_by: str = "views",
) -> list[ContentPerformance]:
    """Get top-performing content sorted by a metric.

    Args:
        slug: Identity slug.
        limit: Maximum number of results. Defaults to 10.
        sort_by: Metric to sort by ("views", "likes", "comments", "shares",
                 "engagement_rate"). Defaults to "views".

    Returns:
        List of ContentPerformance objects sorted by the given metric.

    Raises:
        ValueError: If sort_by is not a valid metric.
    """
    valid_metrics = {"views", "likes", "comments", "shares", "engagement_rate"}
    if sort_by not in valid_metrics:
        raise ValueError(
            f"Invalid sort metric '{sort_by}'. Valid: {', '.join(sorted(valid_metrics))}"
        )

    entries = _load_content_log(slug)

    # Sort by the specified metric (descending)
    entries.sort(key=lambda e: e.get(sort_by, 0), reverse=True)

    results: list[ContentPerformance] = []
    for entry in entries[:limit]:
        results.append(ContentPerformance(
            content_id=entry.get("content_id", ""),
            title=entry.get("title", ""),
            platform=entry.get("platform", ""),
            published_at=entry.get("published_at"),
            views=entry.get("views", 0),
            likes=entry.get("likes", 0),
            comments=entry.get("comments", 0),
            shares=entry.get("shares", 0),
            engagement_rate=entry.get("engagement_rate", 0.0),
        ))

    return results


def get_platform_stats(slug: str) -> list[PlatformStats]:
    """Get aggregated stats per platform.

    Computes platform-level statistics by aggregating content performance
    data across all content for each platform.

    Args:
        slug: Identity slug.

    Returns:
        List of PlatformStats objects, one per platform.
    """
    entries = _load_content_log(slug)

    # Aggregate by platform
    platform_data: dict[str, dict[str, Any]] = {}
    for entry in entries:
        platform = entry.get("platform", "unknown")
        if platform not in platform_data:
            platform_data[platform] = {
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "count": 0,
                "total_engagement": 0.0,
            }
        pd = platform_data[platform]
        pd["total_views"] += entry.get("views", 0)
        pd["total_likes"] += entry.get("likes", 0)
        pd["total_comments"] += entry.get("comments", 0)
        pd["total_engagement"] += entry.get("engagement_rate", 0.0)
        pd["count"] += 1

    # Load stored platform stats for follower counts
    stored_stats = _load_platform_stats(slug)
    stored_by_platform = {s.get("platform", ""): s for s in stored_stats}

    results: list[PlatformStats] = []
    for platform, data in platform_data.items():
        stored = stored_by_platform.get(platform, {})
        avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0.0
        results.append(PlatformStats(
            platform=platform,
            followers=stored.get("followers", 0),
            total_views=data["total_views"],
            total_likes=data["total_likes"],
            total_comments=data["total_comments"],
            engagement_rate=round(avg_engagement, 4),
            last_updated=datetime.now(),
        ))

    return results


def update_platform_followers(
    slug: str,
    platform: str,
    followers: int,
) -> None:
    """Update the follower count for a platform.

    Args:
        slug: Identity slug.
        platform: Platform name.
        followers: Current follower count.
    """
    stats = _load_platform_stats(slug)

    found = False
    for entry in stats:
        if entry.get("platform") == platform:
            entry["followers"] = followers
            entry["last_updated"] = datetime.now().isoformat()
            found = True
            break

    if not found:
        stats.append({
            "platform": platform,
            "followers": followers,
            "last_updated": datetime.now().isoformat(),
        })

    _save_platform_stats(slug, stats)
