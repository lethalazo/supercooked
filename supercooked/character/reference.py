"""Manage reference images for character visual consistency.

Stores and retrieves reference images used by face generation
to maintain a consistent appearance across all generated content.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from supercooked.config import IDENTITIES_DIR
from supercooked.identity.action_log import log_action

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def _reference_dir(slug: str) -> Path:
    """Get the reference image directory for a being."""
    return IDENTITIES_DIR / slug / "face" / "reference"


def add_reference(slug: str, image_path: str | Path) -> Path:
    """Add a reference image for a being's face consistency.

    Copies the image to identities/<slug>/face/reference/.

    Args:
        slug: Identity slug.
        image_path: Path to the source image file.

    Returns:
        Path to the copied reference image.

    Raises:
        FileNotFoundError: If the source image does not exist.
        ValueError: If the file is not a supported image format.
    """
    source = Path(image_path)
    if not source.exists():
        raise FileNotFoundError(f"Image not found: {source}")

    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image format '{source.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    ref_dir = _reference_dir(slug)
    ref_dir.mkdir(parents=True, exist_ok=True)

    dest = ref_dir / source.name
    # If a file with the same name exists, add a numeric suffix
    if dest.exists():
        stem = source.stem
        suffix = source.suffix
        counter = 1
        while dest.exists():
            dest = ref_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(source, dest)

    log_action(
        slug,
        action="add_reference_image",
        details={
            "source": str(source),
            "destination": str(dest),
        },
        result=f"Added reference image: {dest.name}",
    )

    return dest


def list_references(slug: str) -> list[str]:
    """List reference image filenames for a being.

    Args:
        slug: Identity slug.

    Returns:
        List of reference image filenames (not full paths).
    """
    ref_dir = _reference_dir(slug)
    if not ref_dir.exists():
        return []
    return sorted(
        p.name
        for p in ref_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def get_references(slug: str) -> list[Path]:
    """Get full paths to all reference images for a being.

    Args:
        slug: Identity slug.

    Returns:
        List of Path objects for each reference image, sorted by name.
    """
    ref_dir = _reference_dir(slug)
    if not ref_dir.exists():
        return []
    return sorted(
        p
        for p in ref_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def remove_reference(slug: str, filename: str) -> None:
    """Remove a reference image by filename.

    Args:
        slug: Identity slug.
        filename: Name of the file to remove.

    Raises:
        FileNotFoundError: If the reference image does not exist.
    """
    ref_path = _reference_dir(slug) / filename
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference image not found: {filename} for identity '{slug}'"
        )
    ref_path.unlink()

    log_action(
        slug,
        action="remove_reference_image",
        details={"filename": filename},
        result=f"Removed reference image: {filename}",
    )
