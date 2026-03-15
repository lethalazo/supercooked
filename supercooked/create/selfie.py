"""Character selfie generation via Nano Banana 2 on the Gemini API.

Generates "selfie" images of a digital being's character using their
face config for visual consistency. Wraps google.genai Nano Banana 2.
No fallback — raises on any failure.
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
from supercooked.identity.manager import load_identity
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


def _build_selfie_prompt(
    face: FaceConfig,
    name: str,
    location: str,
    mood: str,
) -> str:
    """Build a detailed selfie prompt from face config and context.

    Combines the character's base appearance prompt with location and mood
    to create a natural-looking "selfie" photograph.
    """
    parts = []

    # Core character appearance
    parts.append(face.base_prompt)

    # Selfie-specific framing
    parts.append(
        "selfie photo, first-person perspective, looking at camera, "
        "natural smartphone selfie, candid expression"
    )

    # Style
    if face.style:
        parts.append(f"Style: {face.style}")

    # Location context
    if location:
        parts.append(f"Location: {location}")
    else:
        parts.append("casual indoor setting, natural lighting")

    # Mood / expression
    if mood:
        parts.append(f"Mood and expression: {mood}")
    else:
        parts.append("relaxed, friendly expression")

    # Negative prompt as avoidance instruction
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


async def take_selfie(
    slug: str,
    location: str = "",
    mood: str = "",
) -> Path:
    """Generate a selfie image of the character.

    Loads the identity's face config and builds a prompt that creates
    a natural-looking selfie photo of the character in the given context.

    Parameters
    ----------
    slug:
        Identity slug whose character to photograph.
    location:
        Where the selfie is taken (e.g. "coffee shop", "beach at sunset").
    mood:
        The character's mood/expression (e.g. "happy", "contemplative").

    Returns
    -------
    Path to the saved selfie .png file.

    Raises
    ------
    RuntimeError
        If face config is missing, API key is absent, or generation fails.
    """
    api_key = get_api_key("gemini")
    face = _load_face_config(slug)
    identity = load_identity(slug)
    name = identity.being.name

    prompt = _build_selfie_prompt(face, name, location, mood)

    client = genai.Client(api_key=api_key)

    # Portrait orientation — natural selfie ratio
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="3:4",
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
            action="take_selfie",
            platform="gemini",
            details={"location": location, "mood": mood, "prompt": prompt},
            error=str(exc),
        )
        raise RuntimeError(f"Selfie generation failed: {exc}") from exc

    file_id = uuid.uuid4().hex[:12]
    out_path = _output_dir(slug) / f"selfie_{file_id}.png"

    try:
        await asyncio.to_thread(_extract_and_save_image, response, out_path)
    except Exception as exc:
        log_action(
            slug,
            action="take_selfie",
            platform="gemini",
            details={"location": location, "mood": mood},
            error=f"Extract/save failed: {exc}",
        )
        raise RuntimeError(f"Failed to save selfie image: {exc}") from exc

    # Also save to the identity's face/generated/ directory
    generated_dir = IDENTITIES_DIR / slug / "face" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    gen_copy_path = generated_dir / f"selfie_{file_id}.png"
    try:
        import shutil
        await asyncio.to_thread(shutil.copy2, str(out_path), str(gen_copy_path))
    except Exception:
        pass  # Non-critical — output copy is authoritative

    log_action(
        slug,
        action="take_selfie",
        platform="gemini",
        details={
            "location": location,
            "mood": mood,
            "prompt": prompt,
            "model": NANO_BANANA_MODEL,
            "output_path": str(out_path),
        },
        result=str(out_path),
    )

    return out_path
