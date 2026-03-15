"""Image generation via Nano Banana 2 on the Gemini API (google-genai SDK).

Wraps google.genai to generate images from text prompts using Nano Banana 2
(Gemini 3.1 Flash Image). Also provides character-consistent image generation
using face config. No fallback — if the Gemini API is unreachable or the key
is missing, we raise.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import yaml
from google import genai
from google.genai import types

from supercooked.config import IDENTITIES_DIR, OUTPUT_DIR, get_api_key
from supercooked.identity.action_log import log_action
from supercooked.identity.schemas import FaceConfig

NANO_BANANA_MODEL = "gemini-3.1-flash-image-preview"


def _output_dir(slug: str) -> Path:
    """Ensure and return the output directory for a given identity."""
    d = OUTPUT_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_face_config(slug: str) -> FaceConfig:
    """Load face/config.yaml for the identity."""
    path = IDENTITIES_DIR / slug / "face" / "config.yaml"
    if not path.exists():
        raise RuntimeError(
            f"Face config not found for '{slug}'. "
            f"Expected at {path}. Create the identity first."
        )
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return FaceConfig(**data)


def _parse_aspect_ratio(size: str) -> str:
    """Convert a WxH size string to an aspect ratio string.

    Examples
    --------
    "1080x1080" -> "1:1"
    "1080x1920" -> "9:16"
    "1920x1080" -> "16:9"
    """
    mapping = {
        "1080x1080": "1:1",
        "1080x1350": "4:5",
        "1080x1920": "9:16",
        "1920x1080": "16:9",
        "1024x1024": "1:1",
    }
    if size in mapping:
        return mapping[size]
    # Try to derive from dimensions
    try:
        w, h = (int(x) for x in size.lower().split("x"))
    except ValueError:
        return "1:1"
    if w == h:
        return "1:1"
    if w < h:
        return "9:16"
    return "16:9"


def _extract_and_save_image(response, out_path: Path) -> None:
    """Extract image from Nano Banana generate_content response and save."""
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = part.as_image()
            image.save(str(out_path))
            return
    raise RuntimeError("No image data found in response parts.")


async def generate_image(
    slug: str,
    prompt: str,
    size: str = "1080x1080",
    style: str | None = None,
    negative_prompt: str | None = None,
) -> Path:
    """Generate an image with Nano Banana 2 via the Gemini API.

    Parameters
    ----------
    slug:
        Identity slug — used for output path and action logging.
    prompt:
        Creative text prompt describing the desired image.
    size:
        Target resolution as "WxH" (e.g. "1080x1080", "1080x1920").
        Mapped to the closest aspect ratio.
    style:
        Optional style descriptor appended to prompt (e.g. "photorealistic",
        "digital illustration").
    negative_prompt:
        Optional things to avoid — appended as "Avoid: ..." to prompt.

    Returns
    -------
    Path to the saved .png file.

    Raises
    ------
    RuntimeError
        If the Gemini API key is missing or the generation fails.
    """
    # Build composite prompt with optional style and negative prompt
    parts = [prompt]
    if style:
        parts.append(f"Style: {style}")
    if negative_prompt:
        parts.append(f"Avoid: {negative_prompt}")
    prompt = ". ".join(parts)

    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)

    aspect_ratio = _parse_aspect_ratio(size)

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
        ),
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=NANO_BANANA_MODEL,
            contents=[prompt],
            config=config,
        )
    except Exception as exc:
        log_action(
            slug,
            action="generate_image",
            platform="gemini",
            details={"prompt": prompt, "size": size, "model": NANO_BANANA_MODEL},
            error=str(exc),
        )
        raise RuntimeError(f"Nano Banana 2 image generation failed: {exc}") from exc

    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"image_{file_id}.png"

    try:
        await asyncio.to_thread(_extract_and_save_image, response, out_path)
    except Exception as exc:
        log_action(
            slug,
            action="generate_image",
            platform="gemini",
            details={"prompt": prompt, "size": size},
            error=f"Extract/save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save generated image: {exc}") from exc

    log_action(
        slug,
        action="generate_image",
        platform="gemini",
        details={
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio,
            "model": NANO_BANANA_MODEL,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path


async def generate_character_image(
    slug: str,
    scene_description: str,
) -> Path:
    """Generate a character-consistent image using the identity's face config.

    Loads the face config (base_prompt, negative_prompt, style, consistency_seed)
    and combines it with the scene description to produce a visually consistent
    character image.

    Parameters
    ----------
    slug:
        Identity slug whose face config to load.
    scene_description:
        Description of the scene or action the character is in.

    Returns
    -------
    Path to the saved .png file.

    Raises
    ------
    RuntimeError
        If face config is missing, API key is absent, or generation fails.
    """
    face = _load_face_config(slug)

    # Build a composite prompt that anchors on the character's face config
    parts = [face.base_prompt]
    if face.style:
        parts.append(f"Style: {face.style}")
    parts.append(scene_description)
    if face.negative_prompt:
        parts.append(f"Avoid: {face.negative_prompt}")

    composite_prompt = ". ".join(parts)

    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
        ),
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=NANO_BANANA_MODEL,
            contents=[composite_prompt],
            config=config,
        )
    except Exception as exc:
        log_action(
            slug,
            action="generate_character_image",
            platform="gemini",
            details={"scene": scene_description, "base_prompt": face.base_prompt},
            error=str(exc),
        )
        raise RuntimeError(f"Character image generation failed: {exc}") from exc

    file_id = uuid.uuid4().hex[:12]
    out_dir = _output_dir(slug)
    out_path = out_dir / f"character_{file_id}.png"

    try:
        await asyncio.to_thread(_extract_and_save_image, response, out_path)
    except Exception as exc:
        log_action(
            slug,
            action="generate_character_image",
            platform="gemini",
            details={"scene": scene_description},
            error=f"Extract/save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save character image: {exc}") from exc

    # Also save a copy to the identity's face/generated/ directory
    generated_dir = IDENTITIES_DIR / slug / "face" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    gen_copy_path = generated_dir / f"character_{file_id}.png"
    try:
        import shutil
        await asyncio.to_thread(shutil.copy2, str(out_path), str(gen_copy_path))
    except Exception:
        pass  # Non-critical — output copy is the authoritative one

    log_action(
        slug,
        action="generate_character_image",
        platform="gemini",
        details={
            "scene": scene_description,
            "composite_prompt": composite_prompt,
            "model": NANO_BANANA_MODEL,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path


async def generate_images(
    slug: str,
    prompts: list[str],
    size: str = "1080x1080",
    style: str | None = None,
    negative_prompt: str | None = None,
) -> list[Path]:
    """Generate multiple images concurrently.

    Parameters
    ----------
    slug:
        Identity slug.
    prompts:
        List of prompts — one image generated per prompt.
    size:
        Target resolution for all images.
    style:
        Optional style descriptor for all images.
    negative_prompt:
        Optional negative prompt for all images.

    Returns
    -------
    List of Paths to saved .png files.
    """
    tasks = [
        generate_image(slug, p, size=size, style=style, negative_prompt=negative_prompt)
        for p in prompts
    ]
    return list(await asyncio.gather(*tasks))
