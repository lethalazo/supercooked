"""Routes for digital being (identity) management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.being_service import BeingService

router = APIRouter()
service = BeingService()


class CreateBeingRequest(BaseModel):
    slug: str
    name: str
    tagline: str = ""
    archetype: str = ""
    tone: str = ""
    perspective: str = ""
    voice_traits: list[str] = []
    boundaries: list[str] = []


class UpdateBeingRequest(BaseModel):
    name: str | None = None
    tagline: str | None = None
    tone: str | None = None
    perspective: str | None = None


@router.get("")
async def list_beings():
    """List all digital beings."""
    return service.list_all()


@router.get("/{slug}")
async def get_being(slug: str):
    """Get a specific being's full identity."""
    try:
        return service.get(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")


@router.post("", status_code=201)
async def create_being(req: CreateBeingRequest):
    """Create a new digital being."""
    return service.create(
        slug=req.slug,
        name=req.name,
        tagline=req.tagline,
        archetype=req.archetype,
        tone=req.tone,
        perspective=req.perspective,
        voice_traits=req.voice_traits,
        boundaries=req.boundaries,
    )


@router.put("/{slug}")
async def update_being(slug: str, req: UpdateBeingRequest):
    """Update a being's identity."""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    try:
        return service.update(slug, updates)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")
