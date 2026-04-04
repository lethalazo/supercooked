"""Final render pipeline — orchestrates the complete edit.

Takes an assembled video through grading, audio mixing, text overlays,
and watermark to produce the final deliverable. Supports multiple
export profiles (YouTube, IG Reel, TikTok, etc.).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .assemble import execute_edl, load_edl
from .audio import build_audio_mix, replace_audio
from .briefing import load_briefing, load_project, save_project
from .ffmpeg import overlay_image, probe_source_info, run_ffmpeg_checked
from .grade import build_grade_filter_chain, load_grade_preset
from .models import EDL, ExportProfile, ProjectState
from .overlay import generate_segment_overlays, generate_watermark

_PRESETS_DIR = Path(__file__).parent / "presets"


def load_export_profiles() -> dict[str, ExportProfile]:
    """Load export profiles from exports.yaml."""
    path = _PRESETS_DIR / "exports.yaml"
    if not path.exists():
        return _builtin_profiles()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    profiles = {}
    for name, values in data.get("exports", {}).items():
        profiles[name] = ExportProfile(name=name, **values)
    return profiles


def load_export_profile(name: str) -> ExportProfile:
    """Load a single export profile by name."""
    profiles = load_export_profiles()
    if name not in profiles:
        available = ", ".join(sorted(profiles.keys()))
        raise FileNotFoundError(
            f"Export profile '{name}' not found. Available: {available}"
        )
    return profiles[name]


async def render_final(
    project_dir: Path,
    profile_name: str = "youtube",
    output_path: Path | None = None,
) -> Path:
    """Execute the full render pipeline.

    Steps:
    1. Load EDL and execute it (cut + concat)
    2. Apply text overlays
    3. Mix audio (dialogue + music + SFX)
    4. Add watermark
    5. Final encode with export profile

    Parameters
    ----------
    project_dir:
        Project workspace directory.
    profile_name:
        Export profile name from exports.yaml.
    output_path:
        Where to write final output. Defaults to project_dir/final.mp4.
    """
    project = load_project(project_dir)
    edl = load_edl(project_dir / "edl.yaml")

    if output_path is None:
        output_path = project_dir / "final.mp4"

    profile = load_export_profile(profile_name)
    width, height = profile.resolution.split("x")
    w, h = int(width), int(height)

    # Step 1: Assemble (cut + concat + grade)
    assembled = project_dir / "assembled.mp4"
    await execute_edl(edl, project_dir, assembled)

    current = assembled

    # Step 2: Text overlays
    # Compute cumulative segment start times in the assembled timeline
    seg_timeline_starts: dict[str, float] = {}
    cumulative = 0.0
    for seg in edl.segments:
        seg_timeline_starts[seg.id] = cumulative
        cumulative += seg.duration

    overlays = await generate_segment_overlays(edl, project_dir, w, h)
    if overlays:
        # Apply overlays sequentially, offsetting by segment position
        for i, ov in enumerate(overlays):
            seg_offset = seg_timeline_starts.get(ov["segment_id"], 0.0)
            abs_start = seg_offset + ov["at"]
            abs_end = abs_start + ov["duration"]

            overlay_output = project_dir / "segments" / f"overlaid_{i:03d}.mp4"
            current = await overlay_image(
                video_path=current,
                image_path=ov["overlay_path"],
                output_path=overlay_output,
                x="0", y="0",
                start=abs_start,
                end=abs_end,
                fade_in=ov.get("fade_in", 0.3),
                fade_out=ov.get("fade_out", 0.3),
            )

    # Step 3: Audio mix
    briefing_path = project_dir / "analysis" / "briefing.yaml"
    speech_regions = []
    if briefing_path.exists():
        briefing = load_briefing(briefing_path)
        speech_regions = briefing.audio_map.speech_regions

    source_info = await probe_source_info(current)
    mixed_audio = await build_audio_mix(
        edl, project_dir, current, speech_regions,
        total_duration=source_info.duration_seconds,
    )
    if mixed_audio:
        audio_output = project_dir / "segments" / "with_audio.mp4"
        current = await replace_audio(current, mixed_audio, audio_output)

    # Step 4: Watermark
    if edl.watermark.text:
        wm_path = project_dir / "overlays" / "watermark.png"
        generate_watermark(edl.watermark, w, h, wm_path)
        wm_output = project_dir / "segments" / "watermarked.mp4"
        current = await overlay_image(
            video_path=current,
            image_path=wm_path,
            output_path=wm_output,
            x="0", y="0",
            fade_in=1.0,
        )

    # Step 5: Final encode with export profile
    args = [
        "-i", str(current),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(profile.fps),
        "-c:v", profile.codec,
        "-crf", str(profile.crf),
        "-preset", "slow",
        "-pix_fmt", profile.pixel_format,
        "-c:a", profile.audio_codec,
        "-b:a", profile.audio_bitrate,
    ]
    if profile.max_bitrate:
        args += ["-maxrate", profile.max_bitrate, "-bufsize", profile.max_bitrate]
    args += ["-y", str(output_path)]

    await run_ffmpeg_checked(args)

    # Update project state
    project.state = ProjectState.RENDERED
    save_project(project, project_dir)

    return output_path


def _builtin_profiles() -> dict[str, ExportProfile]:
    """Hardcoded fallback export profiles."""
    return {
        "youtube": ExportProfile(
            name="youtube",
            description="YouTube 1080p",
            resolution="1920x1080",
            fps=30,
            codec="libx264",
            crf=18,
            audio_codec="aac",
            audio_bitrate="192k",
            pixel_format="yuv420p",
        ),
        "youtube-4k": ExportProfile(
            name="youtube-4k",
            description="YouTube 4K",
            resolution="3840x2160",
            fps=30,
            codec="libx264",
            crf=16,
            audio_codec="aac",
            audio_bitrate="256k",
            pixel_format="yuv420p",
            max_bitrate="40M",
        ),
        "ig-reel": ExportProfile(
            name="ig-reel",
            description="Instagram Reel (9:16)",
            resolution="1080x1920",
            fps=30,
            codec="libx264",
            crf=20,
            audio_codec="aac",
            audio_bitrate="128k",
            pixel_format="yuv420p",
            max_bitrate="10M",
        ),
        "ig-story": ExportProfile(
            name="ig-story",
            description="Instagram Story (9:16)",
            resolution="1080x1920",
            fps=30,
            codec="libx264",
            crf=22,
            audio_codec="aac",
            audio_bitrate="128k",
            pixel_format="yuv420p",
        ),
        "tiktok": ExportProfile(
            name="tiktok",
            description="TikTok (9:16)",
            resolution="1080x1920",
            fps=30,
            codec="libx264",
            crf=20,
            audio_codec="aac",
            audio_bitrate="128k",
            pixel_format="yuv420p",
            max_bitrate="10M",
        ),
        "draft": ExportProfile(
            name="draft",
            description="Quick draft preview",
            resolution="1280x720",
            fps=30,
            codec="libx264",
            crf=28,
            audio_codec="aac",
            audio_bitrate="96k",
            pixel_format="yuv420p",
        ),
    }
