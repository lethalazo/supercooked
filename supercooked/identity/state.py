"""Session history, strategy log, and error tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.schemas import SessionSummary, StrategyDecision, StrategyLog


# --- Session History ---


def _session_dir(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "state" / "session_history"


def create_session(slug: str) -> str:
    """Start a new session, returns session_id."""
    session_id = str(uuid.uuid4())[:8]
    session = SessionSummary(
        session_id=session_id,
        started=datetime.now(),
    )
    path = _session_dir(slug) / f"{session_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(session.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
    return session_id


def end_session(
    slug: str,
    session_id: str,
    summary: str = "",
    actions_taken: list[str] | None = None,
    insights_gained: list[str] | None = None,
) -> None:
    """End a session with summary."""
    path = _session_dir(slug) / f"{session_id}.yaml"
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    session = SessionSummary(**data)
    session.ended = datetime.now()
    session.summary = summary
    session.actions_taken = actions_taken or []
    session.insights_gained = insights_gained or []
    with open(path, "w") as f:
        yaml.dump(session.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)


def list_sessions(slug: str) -> list[SessionSummary]:
    """List all sessions for a being."""
    sessions = []
    d = _session_dir(slug)
    if not d.exists():
        return sessions
    for f in sorted(d.iterdir(), reverse=True):
        if f.suffix == ".yaml":
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            sessions.append(SessionSummary(**data))
    return sessions


# --- Strategy Log ---


def _strategy_path(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "state" / "strategy_log.yaml"


def log_strategy_decision(
    slug: str,
    decision: str,
    reasoning: str = "",
    metrics: dict[str, Any] | None = None,
) -> StrategyDecision:
    """Log a content strategy decision."""
    log = _load_strategy_log(slug)
    entry = StrategyDecision(
        timestamp=datetime.now(),
        decision=decision,
        reasoning=reasoning,
        metrics=metrics or {},
    )
    log.decisions.append(entry)
    with open(_strategy_path(slug), "w") as f:
        yaml.dump(log.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
    return entry


def _load_strategy_log(slug: str) -> StrategyLog:
    path = _strategy_path(slug)
    if not path.exists():
        return StrategyLog()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return StrategyLog(**data)


# --- Error Tracking ---


def _errors_path(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "state" / "errors.yaml"


def log_error(
    slug: str, error: str, context: str = "", learned: str = ""
) -> None:
    """Log an error and what was learned from it."""
    path = _errors_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    errors = []
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        errors = data.get("errors", [])

    errors.append({
        "timestamp": datetime.now().isoformat(),
        "error": error,
        "context": context,
        "learned": learned,
    })

    with open(path, "w") as f:
        yaml.dump({"errors": errors}, f, default_flow_style=False, sort_keys=False)
