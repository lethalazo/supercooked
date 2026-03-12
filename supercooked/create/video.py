"""Video generation via Veo 3.1 on the Gemini API (google-genai SDK).

Wraps google.genai to generate short-form videos from text prompts.
No fallback — if the Gemini API is unreachable or the key is missing, we raise.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from google import genai
from google.genai import types

from supercooked.config import OUTPUT_DIR, get_api_key, load_config
from supercooked.identity.action_log import log_action


def _output_dir(slug: str) -> Path:
    """Ensure and return the output directory for a given identity."""
    d = OUTPUT_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _aspect_ratio_for_duration(duration_seconds: int) -> str:
    """Pick a sensible default aspect ratio — vertical for shorts."""
    # Vertical (9:16) for anything 60s or under, landscape otherwise
    if duration_seconds <= 60:
        return "9:16"
    return "16:9"


async def generate_video(
    slug: str,
    prompt: str,
    duration_seconds: int = 30,
) -> Path:
    """Generate a video with Veo 3.1 via the Gemini API.

    Parameters
    ----------
    slug:
        Identity slug — used for output path and action logging.
    prompt:
        Creative text prompt describing the desired video.
    duration_seconds:
        Desired duration in seconds (advisory — the model controls actual length).

    Returns
    -------
    Path to the saved .mp4 file.

    Raises
    ------
    RuntimeError
        If the Gemini API key is missing or the generation fails.
    """
    api_key = get_api_key("gemini")
    config = load_config()

    client = genai.Client(api_key=api_key)

    aspect_ratio = _aspect_ratio_for_duration(duration_seconds)

    video_config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
    )

    # Kick off generation — this returns a long-running operation
    try:
        operation = await asyncio.to_thread(
            client.models.generate_videos,
            model="veo-3.1-generate-preview",
            prompt=prompt,
            config=video_config,
        )
    except Exception as exc:
        log_action(
            slug,
            action="generate_video",
            platform="gemini",
            details={"prompt": prompt, "duration_seconds": duration_seconds},
            error=str(exc),
        )
        raise RuntimeError(f"Veo 3.1 video generation request failed: {exc}") from exc

    # Poll until the operation completes (max 30 minutes)
    max_polls = 180  # 180 * 10s = 30 minutes
    poll_count = 0
    while not operation.done:
        poll_count += 1
        if poll_count > max_polls:
            log_action(
                slug,
                action="generate_video",
                platform="gemini",
                details={"prompt": prompt},
                error="Video generation timed out after 30 minutes",
            )
            raise RuntimeError("Veo 3.1 video generation timed out after 30 minutes")
        await asyncio.sleep(10)
        try:
            operation = await asyncio.to_thread(
                client.operations.get,
                operation,
            )
        except Exception as exc:
            log_action(
                slug,
                action="generate_video",
                platform="gemini",
                details={"prompt": prompt},
                error=f"Polling failed: {exc}",
            )
            raise RuntimeError(f"Veo 3.1 polling failed: {exc}") from exc

    # Extract generated video
    if not operation.response or not operation.response.generated_videos:
        log_action(
            slug,
            action="generate_video",
            platform="gemini",
            details={"prompt": prompt},
            error="No video returned by Veo 3.1",
        )
        raise RuntimeError("Veo 3.1 returned no generated videos.")

    generated_video = operation.response.generated_videos[0]

    # Download and save
    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"video_{file_id}.mp4"

    try:
        await asyncio.to_thread(client.files.download, file=generated_video.video)
        await asyncio.to_thread(generated_video.video.save, str(out_path))
    except Exception as exc:
        log_action(
            slug,
            action="generate_video",
            platform="gemini",
            details={"prompt": prompt},
            error=f"Download/save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save Veo 3.1 video: {exc}") from exc

    log_action(
        slug,
        action="generate_video",
        platform="gemini",
        details={
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
