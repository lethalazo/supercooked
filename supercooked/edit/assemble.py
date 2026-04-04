"""EDL execution — parse an EDL and assemble segments into a video.

Reads the Edit Decision List, cuts each segment from the source,
applies per-segment adjustments (speed, audio, grade), then
concatenates everything with transitions.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .ffmpeg import concat_segments, cut_segment, image_to_video
from .grade import load_grade_preset, build_grade_filter_chain
from .models import EDL, GradeConfig, Segment, SegmentType


def load_edl(path: Path | str) -> EDL:
    """Load an EDL from YAML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"EDL not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return EDL(**data)


def save_edl(edl: EDL, path: Path | str) -> Path:
    """Save an EDL to YAML."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = edl.model_dump(mode="json", by_alias=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)

    return path


async def execute_edl(
    edl: EDL,
    project_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """Execute an EDL: cut segments, apply grades, concatenate.

    Parameters
    ----------
    edl:
        The parsed Edit Decision List.
    project_dir:
        Project workspace directory (for resolving relative paths).
    output_path:
        Where to write the assembled video. Defaults to project_dir/assembled.mp4.

    Returns
    -------
    Path to the assembled video file.
    """
    if not edl.segments:
        raise ValueError("EDL has no segments to assemble")

    segments_dir = project_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = project_dir / "assembled.mp4"

    # Resolve source video path (may be empty for compose workflows)
    default_source = _resolve_path(edl.source, project_dir) if edl.source else None

    # Build grade filter if specified
    grade_filter = _build_grade(edl.grade)

    # Resolve output resolution for image segments
    out_res = edl.output.resolution
    out_fps = edl.output.fps

    # Cut each segment (video or image)
    segment_paths = []
    for i, seg in enumerate(edl.segments):
        source = _resolve_path(seg.source, project_dir) if seg.source else default_source
        seg_output = segments_dir / f"seg_{i:03d}_{seg.id}.mp4"

        if seg.type == SegmentType.IMAGE:
            # Convert static image to video clip
            await image_to_video(
                image_path=source,
                output_path=seg_output,
                duration=seg.duration,
                resolution=out_res,
                fps=out_fps,
                zoom=seg.zoom,
                grade_filter=grade_filter,
            )
        else:
            await cut_segment(
                video_path=source,
                output_path=seg_output,
                start=seg.in_point,
                end=seg.out_point,
                speed=seg.speed,
                mute=seg.audio.mute,
                volume=seg.audio.volume,
                grade_filter=grade_filter,
            )
        segment_paths.append(seg_output)

    # Build transition list for concatenation
    transitions = []
    for seg in edl.segments:
        t = seg.transition_out
        if t:
            transitions.append({"type": t.type.value, "duration": t.duration})
        else:
            transitions.append({"type": "cut", "duration": 0})

    # Concatenate all segments
    await concat_segments(segment_paths, output_path, transitions=transitions)

    return output_path


async def preview_segment(
    edl: EDL,
    project_dir: Path,
    segment_index: int,
    output_path: Path | None = None,
) -> Path:
    """Quickly render a single segment for preview.

    Parameters
    ----------
    segment_index:
        Zero-based index into edl.segments.

    Returns
    -------
    Path to the preview video.
    """
    if segment_index < 0 or segment_index >= len(edl.segments):
        raise ValueError(
            f"Segment index {segment_index} out of range "
            f"(0-{len(edl.segments) - 1})"
        )

    seg = edl.segments[segment_index]
    default_source = _resolve_path(edl.source, project_dir) if edl.source else None
    source = _resolve_path(seg.source, project_dir) if seg.source else default_source

    if output_path is None:
        output_path = project_dir / "segments" / f"preview_{seg.id}.mp4"

    grade_filter = _build_grade(edl.grade)

    if seg.type == SegmentType.IMAGE:
        await image_to_video(
            image_path=source,
            output_path=output_path,
            duration=seg.duration,
            resolution=edl.output.resolution,
            fps=edl.output.fps,
            zoom=seg.zoom,
            grade_filter=grade_filter,
        )
    else:
        await cut_segment(
            video_path=source,
            output_path=output_path,
            start=seg.in_point,
            end=seg.out_point,
            speed=seg.speed,
            mute=seg.audio.mute,
            volume=seg.audio.volume,
            grade_filter=grade_filter,
        )

    return output_path


def _resolve_path(path_str: str, project_dir: Path) -> Path:
    """Resolve a path relative to the project directory."""
    if not path_str:
        raise ValueError("No source path specified")
    p = Path(path_str)
    if p.is_absolute():
        return p
    return project_dir / p


def _build_grade(grade: GradeConfig) -> str | None:
    """Build an FFmpeg filter string from GradeConfig."""
    if grade.custom_filter:
        return grade.custom_filter

    if grade.preset and grade.preset != "neutral":
        try:
            preset = load_grade_preset(grade.preset)
            return build_grade_filter_chain(preset)
        except FileNotFoundError:
            pass

    # Build from individual values if any are set
    parts = []
    eq_parts = []
    if grade.brightness is not None:
        eq_parts.append(f"brightness={grade.brightness}")
    if grade.contrast is not None:
        eq_parts.append(f"contrast={grade.contrast}")
    if grade.saturation is not None:
        eq_parts.append(f"saturation={grade.saturation}")
    if grade.gamma is not None:
        eq_parts.append(f"gamma={grade.gamma}")

    if eq_parts:
        parts.append(f"eq={':'.join(eq_parts)}")

    return ",".join(parts) if parts else None
