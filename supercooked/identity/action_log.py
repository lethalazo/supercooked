"""Timestamped action logging - everything the being does."""

from __future__ import annotations

import fcntl
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.schemas import ActionEntry, ActionLog


def _log_dir(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "state" / "action_log"


def _today_path(slug: str) -> Path:
    return _log_dir(slug) / f"{date.today()}.yaml"


def log_action(
    slug: str,
    action: str,
    platform: str = "",
    details: dict[str, Any] | None = None,
    result: str = "",
    error: str | None = None,
) -> ActionEntry:
    """Log an action the being took."""
    log = _load_today(slug)
    entry = ActionEntry(
        timestamp=datetime.now(),
        action=action,
        platform=platform,
        details=details or {},
        result=result,
        error=error,
    )
    log.entries.append(entry)
    _save_log(slug, log)
    return entry


def get_today_actions(slug: str) -> list[ActionEntry]:
    """Get all actions from today."""
    return _load_today(slug).entries


def get_actions_for_date(slug: str, target_date: date) -> list[ActionEntry]:
    """Get actions for a specific date."""
    path = _log_dir(slug) / f"{target_date}.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return ActionLog(**data).entries


def get_recent_actions(slug: str, days: int = 7) -> list[ActionEntry]:
    """Get actions from the last N days."""
    entries = []
    log_dir = _log_dir(slug)
    if not log_dir.exists():
        return entries
    for f in sorted(log_dir.iterdir(), reverse=True)[:days]:
        if f.suffix == ".yaml":
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            if "entries" in data:
                entries.extend(ActionLog(**data).entries)
    return entries


def _load_today(slug: str) -> ActionLog:
    path = _today_path(slug)
    if not path.exists():
        return ActionLog(date=str(date.today()))
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return ActionLog(**data)


def _save_log(slug: str, log: ActionLog) -> None:
    path = _today_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yaml.dump(log.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
