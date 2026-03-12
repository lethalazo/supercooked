"""Generate/clone voice for a digital being via ElevenLabs."""

from __future__ import annotations

from pathlib import Path

import yaml

from supercooked.config import IDENTITIES_DIR, get_api_key
from supercooked.identity.schemas import VoiceConfig


def load_voice_config(slug: str) -> VoiceConfig:
    """Load voice config for a being."""
    path = IDENTITIES_DIR / slug / "voice" / "config.yaml"
    if not path.exists():
        return VoiceConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return VoiceConfig(**data)


def save_voice_config(slug: str, config: VoiceConfig) -> None:
    """Save voice config."""
    path = IDENTITIES_DIR / slug / "voice" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config.model_dump(mode="json"), f, default_flow_style=False)


def set_voice_id(slug: str, voice_id: str) -> None:
    """Set the ElevenLabs voice ID for a being."""
    config = load_voice_config(slug)
    config.voice_id = voice_id
    save_voice_config(slug, config)


async def list_available_voices() -> list[dict]:
    """List available ElevenLabs voices."""
    import httpx

    api_key = get_api_key("elevenlabs")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])
