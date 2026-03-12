"""Content pipeline orchestration."""

from __future__ import annotations

import fcntl
from pathlib import Path

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.manager import load_identity


class ContentService:
    def list_content(self, slug: str) -> dict:
        """List all content (drafts + published) for a being."""
        identity = load_identity(slug)  # validates slug exists
        base = IDENTITIES_DIR / slug / "content"

        drafts = self._scan_content_dir(base / "drafts")
        published = self._scan_content_dir(base / "published")

        return {
            "slug": slug,
            "drafts": drafts,
            "published": published,
        }

    def get_content(self, slug: str, content_id: str) -> dict:
        """Get a specific content item."""
        base = IDENTITIES_DIR / slug / "content"

        for subdir in ["drafts", "published"]:
            meta_path = base / subdir / content_id / "metadata.yaml"
            if meta_path.exists():
                with open(meta_path) as f:
                    return yaml.safe_load(f) or {}

        raise FileNotFoundError(f"Content not found: {content_id}")

    async def create_content(
        self,
        slug: str,
        template: str,
        title: str = "",
        concept: str = "",
        caption: str = "",
    ) -> dict:
        """Trigger content creation using a template."""
        from supercooked.templates import get_template

        tmpl = get_template(template)
        spec = await tmpl.generate_spec(slug, title, concept)

        # Save spec as draft
        import uuid
        content_id = f"content-{uuid.uuid4().hex[:8]}"
        draft_dir = IDENTITIES_DIR / slug / "content" / "drafts" / content_id
        draft_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "id": content_id,
            "template": template,
            "title": spec.title,
            "caption": caption or spec.caption,
            "status": "drafted",
            "spec": spec.model_dump(),
        }

        with open(draft_dir / "metadata.yaml", "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        return metadata

    def list_ideas(self, slug: str) -> dict:
        """List content ideas for a being."""
        load_identity(slug)  # validates slug
        ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"

        if not ideas_path.exists():
            return {"slug": slug, "ideas": []}

        with open(ideas_path) as f:
            data = yaml.safe_load(f) or {}

        return {"slug": slug, "ideas": data.get("ideas", [])}

    def append_ideas(self, slug: str, ideas: list) -> None:
        """Append new ContentIdea objects to the ideas file (file-locked)."""
        load_identity(slug)
        ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"
        ideas_path.parent.mkdir(parents=True, exist_ok=True)

        # Acquire exclusive lock for the entire read-modify-write
        lock_path = ideas_path.with_suffix(".lock")
        with open(lock_path, "w") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                existing: dict = {"ideas": []}
                if ideas_path.exists():
                    with open(ideas_path) as f:
                        existing = yaml.safe_load(f) or {"ideas": []}

                current = existing.get("ideas", [])
                for idea in ideas:
                    current.append(idea.model_dump(mode="json"))

                with open(ideas_path, "w") as f:
                    yaml.dump({"ideas": current}, f, default_flow_style=False, sort_keys=False)
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    async def publish_content(self, slug: str, idea_id: str) -> dict:
        """Publish generated content (Stage 3). Delegates to pipeline."""
        from supercooked.pipeline.produce import publish_content

        return await publish_content(slug, idea_id)

    def _scan_content_dir(self, directory: Path) -> list[dict]:
        """Scan a content directory for metadata files."""
        items = []
        if not directory.exists():
            return items
        for d in sorted(directory.iterdir()):
            if d.is_dir():
                meta = d / "metadata.yaml"
                if meta.exists():
                    with open(meta) as f:
                        data = yaml.safe_load(f) or {}
                    data["id"] = d.name
                    # List actual files in the directory
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
