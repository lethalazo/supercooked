"""Thumbnail generation via Nano Banana 2 on the Gemini API.

Generates eye-catching thumbnails for video content using Nano Banana 2.
Combines identity face config with title text styling for platform-ready
thumbnails. No fallback - raises on any failure.
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


_TEMPLATE_STYLE_MAP: dict[str, str] = {
    "hot_take": "bold",
    "list_countdown": "bold",
    "talking_head": "vlog",
    "reaction": "gaming",
    "story": "minimal",
    "thread": "educational",
    "photo_post": "minimal",
}


def _build_thumbnail_prompt(
    face: FaceConfig,
    title: str,
    style: str,
    visual_cues: list[str] | None = None,
    concept: str | None = None,
) -> str:
    """Build a thumbnail prompt combining character, title, and style.

    The title is embedded as a conceptual guide - the model generates the
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

    # Add richer context from concept and visual cues
    if concept:
        parts.append(f"Content concept: {concept}")
    if visual_cues:
        parts.append(f"Key visuals: {', '.join(visual_cues[:3])}")

    # Face style override
    if face.style and face.style != "photorealistic":
        parts.append(f"Art style: {face.style}")

    # Negative prompt
    if face.negative_prompt:
        parts.append(f"Avoid: {face.negative_prompt}")

    return ". ".join(parts)


def _extract_and_save_image(response, out_path: Path) -> None:
    """Extract image from Nano Banana generate_content response and save."""
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = part.as_image()
            image.save(str(out_path))
            return
    raise RuntimeError("No image data found in response parts.")


async def generate_thumbnail(
    slug: str,
    title: str,
    style: str = "bold",
    concept_prompt: str | None = None,
    template: str | None = None,
    visual_cues: list[str] | None = None,
    concept: str | None = None,
) -> Path:
    """Generate a thumbnail image for video content.

    Parameters
    ----------
    slug:
        Identity slug - used for face config, output path, and action logging.
    title:
        The video/content title - used as a conceptual guide for the image.
    style:
        Thumbnail style - "bold", "minimal", "gaming", "vlog", or "educational".
    concept_prompt:
        When provided, used directly as the thumbnail prompt instead of
        building one from face config + title + style.
    template:
        Content template name - used to auto-select style if style is "bold".
    visual_cues:
        Optional visual cue descriptions for richer fallback prompts.
    concept:
        Optional content concept for richer fallback prompts.

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

    # Auto-select style from template if not explicitly set
    if template and style == "bold":
        style = _TEMPLATE_STYLE_MAP.get(template, "bold")

    if style not in _STYLE_PROMPTS:
        style = "bold"

    # Use concept_prompt directly if provided, otherwise build from components
    if concept_prompt:
        # Still prepend face config for character consistency
        parts = []
        if face.base_prompt:
            parts.append(face.base_prompt)
        parts.append(concept_prompt)
        if face.negative_prompt:
            parts.append(f"Avoid: {face.negative_prompt}")
        prompt = ". ".join(parts)
    else:
        prompt = _build_thumbnail_prompt(
            face, title, style, visual_cues=visual_cues, concept=concept
        )

    client = genai.Client(api_key=api_key)

    # Thumbnails are landscape 16:9 for YouTube/platform compatibility
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
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
            action="generate_thumbnail",
            platform="gemini",
            details={"title": title, "style": style, "prompt": prompt},
            error=str(exc),
        )
        raise RuntimeError(f"Thumbnail generation failed: {exc}") from exc

    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"thumb_{file_id}.png"

    try:
        await asyncio.to_thread(_extract_and_save_image, response, out_path)
    except Exception as exc:
        log_action(
            slug,
            action="generate_thumbnail",
            platform="gemini",
            details={"title": title, "style": style},
            error=f"Extract/save failed: {exc}",
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
            "model": NANO_BANANA_MODEL,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
