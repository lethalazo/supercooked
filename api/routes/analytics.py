"""Performance analytics routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from supercooked.intel.analytics import get_platform_stats, get_top_content

router = APIRouter()


@router.get("/beings/{slug}/analytics")
async def get_analytics(slug: str):
    """Get analytics overview for a being."""
    try:
        stats = get_platform_stats(slug)
        top = get_top_content(slug, limit=10)
        return {
            "slug": slug,
            "platform_stats": stats,
            "top_content": top,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
