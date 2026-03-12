"""Image generation via Imagen on the Gemini API (google-genai SDK).

Wraps google.genai to generate images from text prompts using Imagen 4.
Also provides character-consistent image generation using face config.
No fallback — if the Gemini API is unreachable or the key is missing, we raise.
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

IMAGEN_MODEL = "imagen-4.0-generate-001"


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
    """Convert a WxH size string to an Imagen aspect ratio string.

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


async def generate_image(
    slug: str,
    prompt: str,
    size: str = "1080x1080",
) -> Path:
    """Generate an image with Imagen via the Gemini API.

    Parameters
    ----------
    slug:
        Identity slug — used for output path and action logging.
    prompt:
        Creative text prompt describing the desired image.
    size:
        Target resolution as "WxH" (e.g. "1080x1080", "1080x1920").
        Mapped to the closest Imagen aspect ratio.

    Returns
    -------
    Path to the saved .png file.

    Raises
    ------
    RuntimeError
        If the Gemini API key is missing or the generation fails.
    """
    api_key = get_api_key("gemini")
    client = genai.Client(api_key=api_key)

    aspect_ratio = _parse_aspect_ratio(size)

    image_config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio=aspect_ratio,
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_images,
            model=IMAGEN_MODEL,
            prompt=prompt,
            config=image_config,
        )
    except Exception as exc:
        log_action(
            slug,
            action="generate_image",
            platform="gemini",
            details={"prompt": prompt, "size": size},
            error=str(exc),
        )
        raise RuntimeError(f"Imagen image generation failed: {exc}") from exc

    if not response.generated_images:
        log_action(
            slug,
            action="generate_image",
            platform="gemini",
            details={"prompt": prompt, "size": size},
            error="No images returned by Imagen",
        )
        raise RuntimeError("Imagen returned no generated images.")

    generated = response.generated_images[0]

    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"image_{file_id}.png"

    try:
        # generated.image is a PIL-compatible object with a save method
        await asyncio.to_thread(generated.image.save, str(out_path))
    except Exception as exc:
        log_action(
            slug,
            action="generate_image",
            platform="gemini",
            details={"prompt": prompt, "size": size},
            error=f"Save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save Imagen image: {exc}") from exc

    log_action(
        slug,
        action="generate_image",
        platform="gemini",
        details={
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio,
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

    image_config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_images,
            model=IMAGEN_MODEL,
            prompt=composite_prompt,
            config=image_config,
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

    if not response.generated_images:
        log_action(
            slug,
            action="generate_character_image",
            platform="gemini",
            details={"scene": scene_description},
            error="No images returned",
        )
        raise RuntimeError("Imagen returned no character images.")

    generated = response.generated_images[0]

    file_id = uuid.uuid4().hex[:12]
    out_dir = _output_dir(slug)
    out_path = out_dir / f"character_{file_id}.png"

    try:
        await asyncio.to_thread(generated.image.save, str(out_path))
    except Exception as exc:
        log_action(
            slug,
            action="generate_character_image",
            platform="gemini",
            details={"scene": scene_description},
            error=f"Save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save character image: {exc}") from exc

    # Also save a copy to the identity's face/generated/ directory
    generated_dir = IDENTITIES_DIR / slug / "face" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    gen_copy_path = generated_dir / f"character_{file_id}.png"
    try:
        await asyncio.to_thread(generated.image.save, str(gen_copy_path))
    except Exception:
        pass  # Non-critical — output copy is the authoritative one

    log_action(
        slug,
        action="generate_character_image",
        platform="gemini",
        details={
            "scene": scene_description,
            "composite_prompt": composite_prompt,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
