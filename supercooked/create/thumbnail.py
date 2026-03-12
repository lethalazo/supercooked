"""Thumbnail generation via Imagen on the Gemini API.

Generates eye-catching thumbnails for video content using Imagen.
Combines identity face config with title text styling for platform-ready
thumbnails. No fallback — raises on any failure.
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


# --- Thumbnail style builders ---

_STYLE_PROMPTS = {
    "bold": (
        "YouTube thumbnail style, bold dramatic composition, "
        "vibrant saturated colors, high contrast, cinematic lighting, "
        "attention-grabbing, professional, 4K quality"
    ),
    "minimal": (
        "clean minimal thumbnail, simple composition, "
        "soft neutral colors, modern aesthetic, elegant, "
        "subtle gradient background, professional"
    ),
    "gaming": (
        "gaming thumbnail style, neon glow effects, dark background, "
        "energetic composition, bright accent colors, dynamic angles, "
        "esports aesthetic"
    ),
    "vlog": (
        "vlog thumbnail, warm natural lighting, candid feel, "
        "lifestyle photography style, inviting composition, "
        "soft bokeh background, approachable"
    ),
    "educational": (
        "educational content thumbnail, clean professional look, "
        "informative layout, bright clear lighting, "
        "trustworthy academic aesthetic, organized composition"
    ),
}


def _build_thumbnail_prompt(
    face: FaceConfig,
    title: str,
    style: str,
) -> str:
    """Build a thumbnail prompt combining character, title, and style.

    The title is embedded as a conceptual guide — Imagen generates the
    visual concept, not literal text rendering (text is overlaid separately
    via compose if needed).
    """
    parts = []

    # Character base appearance
    if face.base_prompt:
        parts.append(face.base_prompt)

    # Style
    style_prompt = _STYLE_PROMPTS.get(style, _STYLE_PROMPTS["bold"])
    parts.append(style_prompt)

    # Title as conceptual guide
    parts.append(f"Visual concept for: {title}")

    # Face style override
    if face.style and face.style != "photorealistic":
        parts.append(f"Art style: {face.style}")

    # Negative prompt
    if face.negative_prompt:
        parts.append(f"Avoid: {face.negative_prompt}")

    return ". ".join(parts)


async def generate_thumbnail(
    slug: str,
    title: str,
    style: str = "bold",
) -> Path:
    """Generate a thumbnail image for video content.

    Parameters
    ----------
    slug:
        Identity slug — used for face config, output path, and action logging.
    title:
        The video/content title — used as a conceptual guide for the image.
    style:
        Thumbnail style — "bold", "minimal", "gaming", "vlog", or "educational".

    Returns
    -------
    Path to the saved thumbnail .png file.

    Raises
    ------
    RuntimeError
        If face config is missing, API key is absent, or generation fails.
    """
    api_key = get_api_key("gemini")
    face = _load_face_config(slug)

    if style not in _STYLE_PROMPTS:
        available = ", ".join(sorted(_STYLE_PROMPTS.keys()))
        raise RuntimeError(
            f"Unknown thumbnail style '{style}'. Available styles: {available}"
        )

    prompt = _build_thumbnail_prompt(face, title, style)

    client = genai.Client(api_key=api_key)

    # Thumbnails are landscape 16:9 for YouTube/platform compatibility
    image_config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="16:9",
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
            action="generate_thumbnail",
            platform="gemini",
            details={"title": title, "style": style, "prompt": prompt},
            error=str(exc),
        )
        raise RuntimeError(f"Thumbnail generation failed: {exc}") from exc

    if not response.generated_images:
        log_action(
            slug,
            action="generate_thumbnail",
            platform="gemini",
            details={"title": title, "style": style},
            error="No images returned by Imagen",
        )
        raise RuntimeError("Imagen returned no thumbnail images.")

    generated = response.generated_images[0]

    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"thumb_{file_id}.png"

    try:
        await asyncio.to_thread(generated.image.save, str(out_path))
    except Exception as exc:
        log_action(
            slug,
            action="generate_thumbnail",
            platform="gemini",
            details={"title": title, "style": style},
            error=f"Save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save thumbnail image: {exc}") from exc

    log_action(
        slug,
        action="generate_thumbnail",
        platform="gemini",
        details={
            "title": title,
            "style": style,
            "prompt": prompt,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
