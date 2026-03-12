"""Business logic for being management."""

from __future__ import annotations

from supercooked.identity.manager import (
    create_identity,
    list_identities,
    load_identity,
    update_identity,
)


class BeingService:
    def list_all(self) -> list[dict]:
        identities = list_identities()
        return [i.model_dump() for i in identities]

    def get(self, slug: str) -> dict:
        identity = load_identity(slug)
        return identity.model_dump()

    def create(
        self,
        slug: str,
        name: str,
        tagline: str = "",
        archetype: str = "",
        tone: str = "",
        perspective: str = "",
        voice_traits: list[str] | None = None,
        boundaries: list[str] | None = None,
    ) -> dict:
        identity = create_identity(
            slug=slug,
            name=name,
            tagline=tagline,
            archetype=archetype,
            tone=tone,
            perspective=perspective,
            voice_traits=voice_traits,
            boundaries=boundaries,
        )
        return identity.model_dump()

    def update(self, slug: str, updates: dict) -> dict:
        identity = update_identity(slug, updates)
        return identity.model_dump()
