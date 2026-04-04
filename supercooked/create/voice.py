"""Voice synthesis via ElevenLabs API (elevenlabs SDK).

Wraps the elevenlabs Python package for text-to-speech synthesis.
Loads voice configuration (voice_id, model, stability, etc.) from the
identity's voice/config.yaml. No fallback - raises on any failure.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from elevenlabs.client import AsyncElevenLabs

from supercooked.config import IDENTITIES_DIR, OUTPUT_DIR, get_api_key
from supercooked.identity.action_log import log_action
from supercooked.identity.schemas import VoiceConfig


def _output_dir(slug: str) -> Path:
    """Ensure and return the output directory for a given identity."""
    d = OUTPUT_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_voice_config(slug: str) -> VoiceConfig:
    """Load voice/config.yaml for the identity."""
    path = IDENTITIES_DIR / slug / "voice" / "config.yaml"
    if not path.exists():
        raise RuntimeError(
            f"Voice config not found for '{slug}'. "
            f"Expected at {path}. Create the identity first."
        )
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return VoiceConfig(**data)


async def synthesize_speech(
    slug: str,
    text: str,
    output_path: Path | str | None = None,
) -> Path:
    """Synthesize speech from text using the identity's ElevenLabs voice.

    Parameters
    ----------
    slug:
        Identity slug - used to load voice config and for action logging.
    text:
        The text to convert to speech.
    output_path:
        Optional explicit output file path. If None, auto-generates a path
        under output/<slug>/.

    Returns
    -------
    Path to the saved .mp3 audio file.

    Raises
    ------
    RuntimeError
        If the ElevenLabs API key is missing, voice_id is not configured,
        or the synthesis fails.
    """
    api_key = get_api_key("elevenlabs")
    voice_config = _load_voice_config(slug)

    if not voice_config.voice_id:
        log_action(
            slug,
            action="synthesize_speech",
            platform="elevenlabs",
            details={"text_length": len(text)},
            error="No voice_id configured",
        )
        raise RuntimeError(
            f"No voice_id configured for '{slug}'. "
            f"Set it in identities/{slug}/voice/config.yaml"
        )

    # Determine output path
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_id = uuid.uuid4().hex[:12]
        out = _output_dir(slug) / f"speech_{file_id}.mp3"

    client = AsyncElevenLabs(api_key=api_key)

    try:
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=voice_config.voice_id,
            model_id=voice_config.model,
            voice_settings={
                "stability": voice_config.stability,
                "similarity_boost": voice_config.similarity_boost,
                "style": voice_config.style,
            },
        )

        # Collect all audio chunks
        audio_data = b""
        async for chunk in audio_stream:
            if isinstance(chunk, bytes):
                audio_data += chunk

    except Exception as exc:
        log_action(
            slug,
            action="synthesize_speech",
            platform="elevenlabs",
            details={
                "text_length": len(text),
                "voice_id": voice_config.voice_id,
                "model": voice_config.model,
            },
            error=str(exc),
        )
        raise RuntimeError(f"ElevenLabs speech synthesis failed: {exc}") from exc

    if not audio_data:
        log_action(
            slug,
            action="synthesize_speech",
            platform="elevenlabs",
            details={"text_length": len(text), "voice_id": voice_config.voice_id},
            error="No audio data received",
        )
        raise RuntimeError("ElevenLabs returned no audio data.")

    # Write audio to file
    out.write_bytes(audio_data)

    log_action(
        slug,
        action="synthesize_speech",
        platform="elevenlabs",
        details={
            "text_length": len(text),
            "voice_id": voice_config.voice_id,
            "model": voice_config.model,
            "output_path": str(out),
            "audio_bytes": len(audio_data),
        },
        result=str(out),
    )

    return out
