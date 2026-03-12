"""Face generation via Google Imagen (Gemini API).

Wraps the google.genai client to generate consistent character faces
using reference images and face config stored per identity.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from google import genai
from google.genai import types

from supercooked.config import IDENTITIES_DIR, get_api_key
from supercooked.identity.action_log import log_action
from supercooked.identity.schemas import FaceConfig

IMAGEN_MODEL = "imagen-4.0-generate-001"


def _load_face_config(slug: str) -> FaceConfig:
    """Load face config from identities/<slug>/face/config.yaml."""
    path = IDENTITIES_DIR / slug / "face" / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Face config not found at {path}. "
            f"Create the identity first with 'supercooked create'."
        )
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return FaceConfig(**data)


def _get_reference_images(slug: str) -> list[Path]:
    """Get all reference images for a being."""
    ref_dir = IDENTITIES_DIR / slug / "face" / "reference"
    if not ref_dir.exists():
        return []
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted(
        p for p in ref_dir.iterdir()
        if p.suffix.lower() in extensions
    )


async def generate_face(
    slug: str,
    expression: str = "neutral",
    output_path: Path | None = None,
) -> Path:
    """Generate a face image for a digital being using Imagen via Gemini API.

    Loads the face config from identities/<slug>/face/config.yaml,
    uses reference images for visual consistency, and saves the result
    to face/generated/.

    Args:
        slug: Identity slug.
        expression: Facial expression to generate (e.g. "neutral", "happy", "angry").
        output_path: Optional custom output path. Defaults to face/generated/<timestamp>.png.

    Returns:
        Path to the generated image file.

    Raises:
        RuntimeError: If the Gemini API key is missing or generation fails.
        FileNotFoundError: If face config doesn't exist.
    """
    api_key = get_api_key("gemini")
    face_config = _load_face_config(slug)

    # Build the prompt
    prompt_parts = [face_config.base_prompt]
    if expression != "neutral":
        prompt_parts.append(f"{expression} expression")
    if face_config.style:
        prompt_parts.append(f"style: {face_config.style}")
    if face_config.negative_prompt:
        prompt_parts.append(f"avoid: {face_config.negative_prompt}")
    prompt = ", ".join(prompt_parts)

    # Initialize the Gemini client
    client = genai.Client(api_key=api_key)

    # Generate using Imagen model (same pattern as image.py, selfie.py, thumbnail.py)
    image_config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
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
            action="generate_face",
            platform="imagen",
            details={"expression": expression, "prompt": prompt},
            error=str(exc),
        )
        raise RuntimeError(f"Imagen face generation failed: {exc}") from exc

    if not response.generated_images:
        raise RuntimeError(
            f"Imagen returned no image data for slug='{slug}', expression='{expression}'. "
            f"Check your face config and API quota."
        )

    image_bytes = response.generated_images[0].image.image_bytes

    # Determine output path
    if output_path is None:
        gen_dir = IDENTITIES_DIR / slug / "face" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        output_path = gen_dir / f"{expression}_{timestamp}_{unique_id}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    log_action(
        slug,
        action="generate_face",
        platform="imagen",
        details={
            "expression": expression,
            "prompt": prompt,
            "output_path": str(output_path),
        },
        result=f"Generated face image at {output_path}",
    )

    return output_path
