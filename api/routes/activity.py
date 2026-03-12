"""Action logs and session history routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from supercooked.identity.action_log import get_recent_actions, get_actions_for_date
from supercooked.identity.state import list_sessions

router = APIRouter()


@router.get("/beings/{slug}/activity")
async def get_activity(slug: str, days: int = 7):
    """Get recent activity for a being."""
    try:
        actions = get_recent_actions(slug, days=days)
        return {
            "slug": slug,
            "days": days,
            "actions": [a.model_dump() for a in actions],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beings/{slug}/activity/{target_date}")
async def get_activity_for_date(slug: str, target_date: str):
    """Get activity for a specific date."""
    try:
        d = date.fromisoformat(target_date)
        actions = get_actions_for_date(slug, d)
        return {
            "slug": slug,
            "date": target_date,
            "actions": [a.model_dump() for a in actions],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")


@router.get("/beings/{slug}/sessions")
async def get_sessions(slug: str):
    """Get session history for a being."""
    sessions = list_sessions(slug)
    return {
        "slug": slug,
        "sessions": [s.model_dump() for s in sessions],
    }
