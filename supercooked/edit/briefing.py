"""Assemble all analysis into a structured AI-readable briefing.

The briefing is THE protocol - a single YAML document that gives any AI
complete understanding of the footage: what's being said, what it looks
like, how the audio flows.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .models import (
    Briefing,
    FrameInfo,
    Project,
    ProjectState,
    Scene,
    SourceInfo,
    Transcript,
)


def assemble_briefing(
    source_info: SourceInfo,
    transcript: Transcript,
    scenes: list[Scene],
    audio_analysis,
    frames: list[FrameInfo],
) -> Briefing:
    """Assemble a Briefing from all analysis components.

    Cross-references transcript segments with scenes - each transcript
    segment gets tagged with its corresponding scene ID.
    """
    # Tag transcript segments with scene IDs
    for seg in transcript.segments:
        for scene in scenes:
            if scene.start <= seg.start < scene.end:
                seg.scene = scene.id
                break

    # Add transcript previews to scenes
    for scene in scenes:
        preview_parts = []
        for seg in transcript.segments:
            if seg.scene == scene.id:
                preview_parts.append(seg.text)
                if len(" ".join(preview_parts)) > 200:
                    break
        scene.transcript_preview = " ".join(preview_parts)[:200]

    # Tag frames with scene IDs if not already set
    for frame in frames:
        if frame.scene is None:
            for scene in scenes:
                if scene.start <= frame.timestamp < scene.end:
                    frame.scene = scene.id
                    break

    # Assign frame paths to scenes
    for scene in scenes:
        scene_frames = [f for f in frames if f.scene == scene.id]
        if scene_frames:
            scene.frame = scene_frames[0].path

    return Briefing(
        source=source_info,
        transcript=transcript,
        scenes=scenes,
        audio_map=audio_analysis,
        frames=frames,
    )


def save_briefing(briefing: Briefing, output_path: Path | str) -> Path:
    """Save briefing as YAML."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = briefing.model_dump(mode="json")
    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)

    return output_path


def load_briefing(path: Path | str) -> Briefing:
    """Load a briefing from YAML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Briefing not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return Briefing(**data)


def save_project(project: Project, project_dir: Path) -> Path:
    """Save project manifest as YAML."""
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / "project.yaml"

    data = project.model_dump(mode="json")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return path


def load_project(project_dir: Path) -> Project:
    """Load project manifest from YAML."""
    path = project_dir / "project.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return Project(**data)


def save_transcript(transcript: Transcript, output_path: Path | str) -> Path:
    """Save transcript as JSON (preserves word-level detail)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = transcript.model_dump(mode="json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return output_path


def load_transcript(path: Path | str) -> Transcript:
    """Load transcript from JSON."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return Transcript(**data)


def save_scenes(scenes: list[Scene], output_path: Path | str) -> Path:
    """Save scenes as JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [s.model_dump(mode="json") for s in scenes]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return output_path


def save_frames_index(frames: list[FrameInfo], output_path: Path | str) -> Path:
    """Save frame metadata index as JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [f.model_dump(mode="json") for f in frames]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return output_path


def save_audio_analysis(analysis, output_path: Path | str) -> Path:
    """Save audio analysis as JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = analysis.model_dump(mode="json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return output_path


def format_briefing_summary(briefing: Briefing) -> str:
    """Format a human-readable summary of the briefing for terminal display."""
    lines = []

    s = briefing.source
    lines.append(f"Source: {s.file}")
    lines.append(f"Duration: {s.duration} ({s.duration_seconds:.0f}s)")
    lines.append(f"Resolution: {s.resolution} @ {s.fps}fps")
    lines.append(f"Codecs: {s.codec} / {s.audio_codec}")
    lines.append(f"Size: {s.file_size_mb} MB")
    lines.append("")

    t = briefing.transcript
    lines.append(f"Transcript: {t.word_count} words, {len(t.segments)} segments ({t.language})")
    lines.append("")

    lines.append(f"Scenes: {len(briefing.scenes)}")
    for scene in briefing.scenes[:10]:
        preview = scene.transcript_preview[:60] + "..." if len(scene.transcript_preview) > 60 else scene.transcript_preview
        lines.append(f"  [{scene.id}] {scene.start:.1f}s-{scene.end:.1f}s ({scene.duration:.1f}s) {preview}")
    if len(briefing.scenes) > 10:
        lines.append(f"  ... and {len(briefing.scenes) - 10} more")
    lines.append("")

    a = briefing.audio_map
    lines.append(f"Audio: {len(a.speech_regions)} speech regions, {len(a.silence_regions)} silences")
    lines.append(f"Loudness: {a.loudness_integrated} LUFS (range {a.loudness_range}, peak {a.peak_db} dB)")
    lines.append("")

    lines.append(f"Frames: {len(briefing.frames)} keyframes extracted")

    return "\n".join(lines)
