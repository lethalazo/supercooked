"""Color grading presets and custom grade builder.

Provides named presets (moody, warm, cinematic, clean, neutral) that
map to FFmpeg video filter chains. Presets are defined in grades.yaml
and can be overridden per-project.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import GradePreset

_PRESETS_DIR = Path(__file__).parent / "presets"


def load_grade_presets() -> dict[str, GradePreset]:
    """Load all grade presets from grades.yaml."""
    path = _PRESETS_DIR / "grades.yaml"
    if not path.exists():
        return _builtin_presets()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    presets = {}
    for name, values in data.get("grades", {}).items():
        presets[name] = GradePreset(name=name, **values)

    return presets


def load_grade_preset(name: str) -> GradePreset:
    """Load a single grade preset by name."""
    presets = load_grade_presets()
    if name not in presets:
        available = ", ".join(sorted(presets.keys()))
        raise FileNotFoundError(
            f"Grade preset '{name}' not found. Available: {available}"
        )
    return presets[name]


def build_grade_filter_chain(preset: GradePreset) -> str:
    """Build an FFmpeg video filter string from a grade preset.

    If the preset has a raw filter_chain, use it directly.
    Otherwise build from individual parameters.
    """
    if preset.filter_chain:
        return preset.filter_chain

    filters = []

    # EQ filter for brightness, gamma, saturation, contrast
    eq_parts = []
    if preset.brightness != 0.0:
        eq_parts.append(f"brightness={preset.brightness}")
    if preset.gamma != 1.0:
        eq_parts.append(f"gamma={preset.gamma}")
    if preset.saturation != 1.0:
        eq_parts.append(f"saturation={preset.saturation}")
    if preset.contrast != 1.0:
        eq_parts.append(f"contrast={preset.contrast}")

    if eq_parts:
        filters.append(f"eq={':'.join(eq_parts)}")

    return ",".join(filters) if filters else "null"


def _builtin_presets() -> dict[str, GradePreset]:
    """Hardcoded fallback presets if grades.yaml is missing."""
    return {
        "neutral": GradePreset(
            name="neutral",
            description="No grading - pass through",
        ),
        "moody": GradePreset(
            name="moody",
            description="Dark, crushed blacks, desaturated",
            filter_chain=(
                "eq=brightness=-0.15:gamma=0.75:saturation=0.85,"
                "curves=master='0/0 0.25/0.15 0.5/0.4 0.75/0.65 1/0.85',"
                "colorbalance=rs=0.04:gs=-0.02:bs=-0.03,"
                "vignette=angle=PI/3"
            ),
        ),
        "warm": GradePreset(
            name="warm",
            description="Warm tones, slightly lifted blacks",
            filter_chain=(
                "eq=brightness=0.02:saturation=1.1,"
                "colorbalance=rs=0.06:gs=0.02:bs=-0.04,"
                "curves=master='0/0.05 0.5/0.52 1/1'"
            ),
        ),
        "cinematic": GradePreset(
            name="cinematic",
            description="High contrast, teal-orange split tone",
            filter_chain=(
                "eq=contrast=1.2:saturation=0.9,"
                "colorbalance=rs=0.05:gs=-0.02:bs=-0.05:rh=-0.03:gh=0.01:bh=0.04,"
                "curves=master='0/0 0.15/0.08 0.5/0.48 0.85/0.88 1/1',"
                "vignette=angle=PI/4"
            ),
        ),
        "clean": GradePreset(
            name="clean",
            description="Bright, slightly lifted, natural colors",
            filter_chain=(
                "eq=brightness=0.05:saturation=1.05:gamma=1.05,"
                "curves=master='0/0.03 0.5/0.52 1/1'"
            ),
        ),
    }
