"""CRUD for digital being identities."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.schemas import (
    BeingInfo,
    ContentStrategy,
    FaceConfig,
    Identity,
    IdeasFile,
    Memory,
    Persona,
    Platforms,
    StrategyLog,
    VoiceConfig,
)

import re

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


def _validate_slug(slug: str) -> None:
    """Validate slug to prevent path traversal and invalid names."""
    if not slug or not _SLUG_PATTERN.match(slug):
        raise ValueError(
            f"Invalid slug: '{slug}'. "
            "Slugs must be lowercase alphanumeric with hyphens, starting with a letter or digit."
        )


VOICE_MD_TEMPLATE = """# {name} — Voice & Personality Guide

## Who I Am
{tagline}

## Tone
{tone}

## Perspective
{perspective}

## Voice Traits
{voice_traits}

## Boundaries
{boundaries}

---
Use this guide as a system prompt when generating content as {name}.
This file defines how {name} writes, speaks, and presents itself.
"""


def _identity_dir(slug: str) -> Path:
    _validate_slug(slug)
    return IDENTITIES_DIR / slug


def _ensure_dirs(slug: str) -> Path:
    """Create all subdirectories for a being."""
    base = _identity_dir(slug)
    subdirs = [
        "credentials",
        "state/action_log",
        "state/session_history",
        "face/reference",
        "face/generated",
        "voice/samples",
        "content/ideas",
        "content/series",
        "content/drafts",
        "content/published",
        "life",
        "analytics",
    ]
    for d in subdirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    return base


def create_identity(
    slug: str,
    name: str,
    tagline: str = "",
    archetype: str = "",
    tone: str = "",
    perspective: str = "",
    voice_traits: list[str] | None = None,
    boundaries: list[str] | None = None,
) -> Identity:
    """Create a new digital being with full directory structure."""
    base = _ensure_dirs(slug)

    identity = Identity(
        being=BeingInfo(
            slug=slug,
            name=name,
            tagline=tagline,
            created=str(date.today()),
        ),
        persona=Persona(
            archetype=archetype,
            tone=tone,
            perspective=perspective,
            voice_traits=voice_traits or [],
            boundaries=boundaries or [],
        ),
    )

    # Write identity.yaml
    with open(base / "identity.yaml", "w") as f:
        yaml.dump(identity.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)

    # Write VOICE.md
    traits_str = "\n".join(f"- {t}" for t in (voice_traits or []))
    bounds_str = "\n".join(f"- {b}" for b in (boundaries or []))
    voice_md = VOICE_MD_TEMPLATE.format(
        name=name,
        tagline=tagline,
        tone=tone,
        perspective=perspective,
        voice_traits=traits_str,
        boundaries=bounds_str,
    )
    with open(base / "VOICE.md", "w") as f:
        f.write(voice_md)

    # Initialize config files
    face_config = FaceConfig(base_prompt=f"portrait of {name}, {archetype}")
    with open(base / "face" / "config.yaml", "w") as f:
        yaml.dump(face_config.model_dump(mode="json"), f, default_flow_style=False)

    voice_config = VoiceConfig()
    with open(base / "voice" / "config.yaml", "w") as f:
        yaml.dump(voice_config.model_dump(mode="json"), f, default_flow_style=False)

    # Initialize state files
    memory = Memory()
    with open(base / "state" / "memory.yaml", "w") as f:
        yaml.dump(memory.model_dump(mode="json"), f, default_flow_style=False)

    strategy = StrategyLog()
    with open(base / "state" / "strategy_log.yaml", "w") as f:
        yaml.dump(strategy.model_dump(mode="json"), f, default_flow_style=False)

    with open(base / "state" / "audience.yaml", "w") as f:
        yaml.dump({"total_followers": {}, "demographics": {}, "top_interests": []}, f)

    with open(base / "state" / "errors.yaml", "w") as f:
        yaml.dump({"errors": []}, f)

    # Initialize content ideas
    ideas = IdeasFile()
    with open(base / "content" / "ideas.yaml", "w") as f:
        yaml.dump(ideas.model_dump(mode="json"), f, default_flow_style=False)

    # Initialize life
    with open(base / "life" / "location.yaml", "w") as f:
        yaml.dump({"current": "the cloud", "history": []}, f)

    with open(base / "life" / "journal.md", "w") as f:
        f.write(f"# {name}'s Journal\n\n")

    with open(base / "life" / "relationships.yaml", "w") as f:
        yaml.dump({"relationships": []}, f)

    # Initialize analytics
    with open(base / "analytics" / "platforms.yaml", "w") as f:
        yaml.dump({"platforms": []}, f)

    with open(base / "analytics" / "content_log.yaml", "w") as f:
        yaml.dump({"entries": []}, f)

    return identity


def list_identities() -> list[Identity]:
    """List all digital beings."""
    identities = []
    if not IDENTITIES_DIR.exists():
        return identities
    for d in sorted(IDENTITIES_DIR.iterdir()):
        if d.is_dir() and (d / "identity.yaml").exists():
            identities.append(load_identity(d.name))
    return identities


def load_identity(slug: str) -> Identity:
    """Load a being's identity from YAML."""
    path = _identity_dir(slug) / "identity.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Identity not found: {slug}")
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Identity(**data)


def update_identity(slug: str, updates: dict) -> Identity:
    """Update a being's identity."""
    identity = load_identity(slug)
    data = identity.model_dump()
    _deep_merge(data, updates)
    updated = Identity(**data)

    path = _identity_dir(slug) / "identity.yaml"
    with open(path, "w") as f:
        yaml.dump(updated.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
    return updated


def get_voice_md(slug: str) -> str:
    """Load VOICE.md for a being."""
    path = _identity_dir(slug) / "VOICE.md"
    if not path.exists():
        return ""
    return path.read_text()


def get_identity_dir(slug: str) -> Path:
    """Get the directory for a being."""
    return _identity_dir(slug)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
