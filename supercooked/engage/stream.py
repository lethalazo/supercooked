"""Live stream management via OBS WebSocket + ElevenLabs TTS.

Wraps OBS WebSocket for stream control and ElevenLabs for real-time
text-to-speech responses to chat messages during live streams.
"""

from __future__ import annotations

from typing import Any

import httpx

from supercooked.config import get_api_key
from supercooked.engage.respond import generate_reply
from supercooked.identity.action_log import log_action
from supercooked.identity.voice_gen import load_voice_config

OBS_WS_URL = "http://localhost:4455"

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


async def _check_obs() -> None:
    """Verify OBS WebSocket server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OBS_WS_URL)
            # OBS WebSocket may not respond to plain HTTP GET with 200,
            # but a connection should succeed
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise RuntimeError(
            "OBS WebSocket server is not available at localhost:4455. "
            "Start OBS Studio and enable the WebSocket server plugin.\n"
            f"Connection error: {e}"
        )


async def _obs_request(request_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a request to OBS WebSocket via the HTTP interface."""
    payload: dict[str, Any] = {
        "request-type": request_type,
    }
    if data:
        payload.update(data)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(OBS_WS_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def start_stream(slug: str) -> dict[str, Any]:
    """Start a live stream via OBS WebSocket.

    Verifies OBS is running and sends the StartStreaming command.

    Args:
        slug: Identity slug.

    Returns:
        OBS WebSocket response dict.

    Raises:
        RuntimeError: If OBS WebSocket is not available.
    """
    await _check_obs()

    result = await _obs_request("StartStreaming")

    log_action(
        slug,
        action="start_stream",
        platform="obs",
        details={"obs_response": result},
        result="Live stream started via OBS",
    )

    return result


async def stop_stream(slug: str) -> dict[str, Any]:
    """Stop the live stream via OBS WebSocket.

    Args:
        slug: Identity slug.

    Returns:
        OBS WebSocket response dict.

    Raises:
        RuntimeError: If OBS WebSocket is not available.
    """
    await _check_obs()
    result = await _obs_request("StopStreaming")

    log_action(
        slug,
        action="stop_stream",
        platform="obs",
        details={"obs_response": result},
        result="Live stream stopped",
    )

    return result


async def _generate_tts(slug: str, text: str) -> bytes:
    """Generate TTS audio for a text using ElevenLabs.

    Args:
        slug: Identity slug (to load voice config).
        text: Text to convert to speech.

    Returns:
        Audio bytes (mp3 format).

    Raises:
        RuntimeError: If ElevenLabs API key or voice_id is missing.
    """
    api_key = get_api_key("elevenlabs")
    voice_config = load_voice_config(slug)

    if not voice_config.voice_id:
        raise RuntimeError(
            f"No ElevenLabs voice_id configured for identity '{slug}'. "
            f"Set it in identities/{slug}/voice/config.yaml"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_TTS_URL}/{voice_config.voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": voice_config.model,
                "voice_settings": {
                    "stability": voice_config.stability,
                    "similarity_boost": voice_config.similarity_boost,
                    "style": voice_config.style,
                },
            },
        )
        resp.raise_for_status()
        return resp.content


async def handle_chat_message(
    slug: str,
    username: str,
    message: str,
) -> dict[str, Any]:
    """Handle an incoming live stream chat message.

    Generates an in-character text reply via Claude, then converts it to
    speech via ElevenLabs, and plays it through OBS.

    Args:
        slug: Identity slug.
        username: Chat username who sent the message.
        message: The chat message text.

    Returns:
        Dict with the reply text and audio status.

    Raises:
        RuntimeError: If any required service is unavailable.
    """
    # Generate in-character text reply
    full_message = f"[from {username}]: {message}"
    reply_text = await generate_reply(
        slug,
        comment_text=full_message,
        platform="twitch",
        max_tokens=200,
    )

    # Generate TTS audio
    audio_bytes = await _generate_tts(slug, reply_text)

    # Send audio to OBS for playback via a media source
    # This writes the audio to a temp file that OBS monitors
    from pathlib import Path
    import tempfile

    audio_dir = Path(tempfile.gettempdir()) / "supercooked" / "stream_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "latest_response.mp3"
    audio_path.write_bytes(audio_bytes)

    # Trigger OBS to refresh the media source
    await _obs_request("SetSourceSettings", {
        "sourceName": "TTS_Response",
        "sourceSettings": {
            "local_file": str(audio_path),
            "restart_on_activate": True,
        },
    })

    log_action(
        slug,
        action="handle_chat_message",
        platform="twitch",
        details={
            "username": username,
            "message": message[:200],
            "reply": reply_text[:200],
            "audio_size_bytes": len(audio_bytes),
        },
        result=f"Replied to {username} in stream chat",
    )

    return {
        "reply_text": reply_text,
        "audio_generated": True,
        "audio_path": str(audio_path),
        "username": username,
    }
