"""Persistent memory system for digital beings."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.schemas import Memory, MemoryEntry


def _memory_path(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "state" / "memory.yaml"


def load_memory(slug: str) -> Memory:
    """Load a being's memory."""
    path = _memory_path(slug)
    if not path.exists():
        return Memory()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Memory(**data)


def add_learning(
    slug: str,
    category: str,
    insight: str,
    confidence: float = 0.5,
    evidence: list[str] | None = None,
) -> MemoryEntry:
    """Add a new learning to the being's memory."""
    memory = load_memory(slug)
    entry = MemoryEntry(
        category=category,
        insight=insight,
        confidence=confidence,
        learned_at=datetime.now(),
        evidence=evidence or [],
    )
    memory.learnings.append(entry)
    _save_memory(slug, memory)
    return entry


def get_learnings(slug: str, category: str | None = None) -> list[MemoryEntry]:
    """Get learnings, optionally filtered by category."""
    memory = load_memory(slug)
    if category is None:
        return memory.learnings
    return [e for e in memory.learnings if e.category == category]


def update_confidence(slug: str, index: int, new_confidence: float) -> None:
    """Update confidence for a specific learning."""
    memory = load_memory(slug)
    if 0 <= index < len(memory.learnings):
        memory.learnings[index].confidence = new_confidence
        _save_memory(slug, memory)


def _save_memory(slug: str, memory: Memory) -> None:
    path = _memory_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(memory.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
