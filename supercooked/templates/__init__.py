"""Content templates — format blueprints for the content pipeline."""

from __future__ import annotations

from supercooked.templates.base import BaseTemplate, ContentSpec
from supercooked.templates.carousel import CarouselTemplate
from supercooked.templates.hot_take import HotTakeTemplate
from supercooked.templates.list_countdown import ListCountdownTemplate
from supercooked.templates.livestream import LivestreamTemplate
from supercooked.templates.longform import LongformTemplate
from supercooked.templates.photo_post import PhotoPostTemplate
from supercooked.templates.reaction import ReactionTemplate
from supercooked.templates.story import StoryTemplate
from supercooked.templates.talking_head import TalkingHeadTemplate
from supercooked.templates.thread import ThreadTemplate
from supercooked.templates.vlog import VlogTemplate

__all__ = [
    "BaseTemplate",
    "ContentSpec",
    "CarouselTemplate",
    "HotTakeTemplate",
    "ListCountdownTemplate",
    "LivestreamTemplate",
    "LongformTemplate",
    "PhotoPostTemplate",
    "ReactionTemplate",
    "StoryTemplate",
    "TalkingHeadTemplate",
    "ThreadTemplate",
    "VlogTemplate",
    "get_template",
    "list_templates",
]

_REGISTRY: dict[str, type[BaseTemplate]] = {
    "hot_take": HotTakeTemplate,
    "list_countdown": ListCountdownTemplate,
    "talking_head": TalkingHeadTemplate,
    "reaction": ReactionTemplate,
    "vlog": VlogTemplate,
    "story": StoryTemplate,
    "thread": ThreadTemplate,
    "photo_post": PhotoPostTemplate,
    "carousel": CarouselTemplate,
    "livestream": LivestreamTemplate,
    "longform": LongformTemplate,
}


def get_template(name: str) -> BaseTemplate:
    """Return an instantiated template by name.

    Args:
        name: Template name (e.g. "hot_take", "carousel", "longform").

    Returns:
        An instance of the matching template.

    Raises:
        KeyError: If no template matches the given name.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"Unknown template '{name}'. Available templates: {available}"
        )
    return cls()


def list_templates() -> list[str]:
    """Return all registered template names."""
    return sorted(_REGISTRY)
