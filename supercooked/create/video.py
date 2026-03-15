"""Video generation via Veo 3.1 on the Gemini API (google-genai SDK).

Wraps google.genai to generate short-form videos from text prompts.
Supports video extension to produce 15-20s clips (base 8s + extensions).
No fallback — if the Gemini API is unreachable or the key is missing, we raise.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from google import genai
from google.genai import types

from supercooked.config import OUTPUT_DIR, get_api_key
from supercooked.identity.action_log import log_action

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-3.1-generate-preview"


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


async def _poll_operation(client, operation, slug: str, prompt: str) -> object:
    """Poll a long-running operation until completion (max 30 minutes)."""
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
    return operation


def _extensions_needed(duration_seconds: int) -> int:
    """Calculate how many 7-second extensions are needed after the base 8s clip.

    Returns the number of extensions to reach the target duration.
    Each extension adds ~7 seconds to the base 8-second clip.
    """
    if duration_seconds <= 8:
        return 0
    # Each extension adds 7s: 8 + 7*n >= target
    needed = (duration_seconds - 8 + 6) // 7  # ceiling division
    return min(needed, 20)  # API max is 20 extensions


async def generate_video(
    slug: str,
    prompt: str,
    duration_seconds: int = 30,
    negative_prompt: str | None = None,
) -> Path:
    """Generate a video with Veo 3.1 via the Gemini API.

    Generates an initial 8-second clip, then extends it with sequential
    7-second segments to reach the target duration. Typical results are
    15-22 seconds for standard content.

    Parameters
    ----------
    slug:
        Identity slug — used for output path and action logging.
    prompt:
        Creative text prompt describing the desired video.
    duration_seconds:
        Target duration in seconds. The base clip is 8s, then extended
        in 7s increments (8s, 15s, 22s, 29s, ...). Default 30s.
    negative_prompt:
        Optional things to avoid — appended as "Avoid: ..." to the prompt.

    Returns
    -------
    Path to the saved .mp4 file.

    Raises
    ------
    RuntimeError
        If the Gemini API key is missing or the generation fails.
    """
    api_key = get_api_key("gemini")

    # Append negative prompt if provided
    if negative_prompt:
        prompt = f"{prompt}. Avoid: {negative_prompt}"

    client = genai.Client(api_key=api_key)

    aspect_ratio = _aspect_ratio_for_duration(duration_seconds)

    video_config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        person_generation="allow_all",
    )

    # --- Step 1: Generate base 8-second clip ---
    try:
        operation = await asyncio.to_thread(
            client.models.generate_videos,
            model=VEO_MODEL,
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

    operation = await _poll_operation(client, operation, slug, prompt)

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

    # --- Step 2: Extend video to target duration ---
    extensions = _extensions_needed(duration_seconds)
    total_duration = 8

    for ext_num in range(1, extensions + 1):
        logger.info(
            "Extending video for %s: extension %d/%d (current ~%ds)",
            slug, ext_num, extensions, total_duration,
        )

        ext_config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            person_generation="allow_all",
        )

        try:
            ext_operation = await asyncio.to_thread(
                client.models.generate_videos,
                model=VEO_MODEL,
                video=generated_video.video,
                prompt=prompt,
                config=ext_config,
            )
        except Exception as exc:
            logger.warning(
                "Video extension %d failed for %s: %s — using %ds clip",
                ext_num, slug, exc, total_duration,
            )
            break  # Use what we have so far

        try:
            ext_operation = await _poll_operation(client, ext_operation, slug, prompt)
        except Exception as exc:
            logger.warning(
                "Video extension %d polling failed for %s: %s — using %ds clip",
                ext_num, slug, exc, total_duration,
            )
            break

        if ext_operation.response and ext_operation.response.generated_videos:
            generated_video = ext_operation.response.generated_videos[0]
            total_duration += 7
        else:
            logger.warning(
                "Video extension %d returned no video for %s — using %ds clip",
                ext_num, slug, total_duration,
            )
            break

    # --- Step 3: Download and save ---
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
            "actual_duration": total_duration,
            "extensions": extensions,
            "aspect_ratio": aspect_ratio,
            "model": VEO_MODEL,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
