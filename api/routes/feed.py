"""Unified feed across all beings."""

from __future__ import annotations

from fastapi import APIRouter

from api.services.feed_service import FeedService

router = APIRouter()
service = FeedService()


@router.get("")
async def get_feed(limit: int = 50, offset: int = 0):
    """Get unified feed across all beings, reverse chronological."""
    return service.get_unified_feed(limit=limit, offset=offset)


@router.get("/{slug}")
async def get_being_feed(slug: str, limit: int = 50, offset: int = 0):
    """Get feed for a specific being."""
    return service.get_being_feed(slug, limit=limit, offset=offset)
