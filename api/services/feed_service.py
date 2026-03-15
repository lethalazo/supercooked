"""Aggregate feeds across beings."""

from __future__ import annotations

from pathlib import Path

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.manager import list_identities


class FeedService:
    def get_unified_feed(self, limit: int = 50, offset: int = 0) -> dict:
        """Get content from all beings, reverse chronological."""
        all_items = []
        identities = list_identities()

        for identity in identities:
            slug = identity.being.slug
            items = self._get_published(slug)
            for item in items:
                item["being"] = {
                    "slug": slug,
                    "name": identity.being.name,
                    "tagline": identity.being.tagline,
                }
            all_items.extend(items)

        # Sort by published_at descending
        all_items.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True,
        )

        return {
            "total": len(all_items),
            "offset": offset,
            "limit": limit,
            "items": all_items[offset : offset + limit],
        }

    def get_being_feed(self, slug: str, limit: int = 50, offset: int = 0) -> dict:
        """Get content for a specific being."""
        items = self._get_published(slug)
        items.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        return {
            "slug": slug,
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "items": items[offset : offset + limit],
        }

    def _get_published(self, slug: str) -> list[dict]:
        """Get all published content for a being."""
        published_dir = IDENTITIES_DIR / slug / "content" / "published"
        items = []

        if not published_dir.exists():
            return items

        for d in published_dir.iterdir():
            if d.is_dir():
                meta = d / "metadata.yaml"
                if meta.exists():
                    with open(meta) as f:
                        data = yaml.safe_load(f) or {}
                    data["id"] = d.name
                    data["slug"] = slug
                    # Scan for media files (same pattern as ContentService)
                    media_files = []
                    for f_path in sorted(d.iterdir()):
                        if f_path.is_file() and f_path.suffix in (
                            ".png", ".jpg", ".jpeg", ".mp4", ".mp3",
                            ".wav", ".txt", ".srt",
                        ):
                            media_files.append({
                                "name": f_path.name,
                                "type": f_path.suffix.lstrip("."),
                                "size": f_path.stat().st_size,
                            })
                    if media_files:
                        data["media_files"] = media_files
                    items.append(data)

        return items
