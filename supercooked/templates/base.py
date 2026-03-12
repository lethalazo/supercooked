"""Base template interface for content generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ContentSpec(BaseModel):
    """Specification for a piece of content."""

    title: str
    script: str = ""
    duration_seconds: int = 30
    resolution: str = "1080x1920"
    voice_prompt: str = ""
    image_prompts: list[str] = Field(default_factory=list)
    video_prompt: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    platform_targets: list[str] = Field(default_factory=list)


class BaseTemplate(ABC):
    """Abstract base for all content templates."""

    name: str
    format_type: str  # "short", "image", "text", "story", "thread", "livestream", "longform"

    @abstractmethod
    async def generate_spec(
        self, slug: str, idea_title: str, idea_concept: str
    ) -> ContentSpec:
        """Generate a content specification from an idea."""
        ...
