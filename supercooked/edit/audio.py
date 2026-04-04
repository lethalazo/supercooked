"""Audio mixing - dialogue extraction, music ducking, SFX insertion.

Handles the complete audio pipeline: extract original dialogue,
mix in background music with intelligent ducking under speech,
and place sound effects at specific timestamps.
"""

from __future__ import annotations

from pathlib import Path

from .ffmpeg import extract_audio, mix_audio, run_ffmpeg_checked
from .models import AudioMix, AudioRegion, EDL


async def build_audio_mix(
    edl: EDL,
    project_dir: Path,
    video_path: Path,
    speech_regions: list[AudioRegion],
    total_duration: float,
    output_path: Path | None = None,
) -> Path | None:
    """Build the complete audio mix from EDL audio specification.

    Steps:
    1. Extract dialogue from assembled video
    2. Prepare music track (loop/trim, set volume)
    3. Apply ducking to music during speech
    4. Place SFX at specified times
    5. Mix all tracks together

    Returns None if no audio mixing is needed (dialogue-only).
    """
    audio_spec = edl.audio
    if not audio_spec.music and not audio_spec.sfx:
        return None

    if output_path is None:
        output_path = project_dir / "mixed_audio.m4a"

    tracks = []

    # Track 1: Original dialogue (skip if source is "none" - compose workflow)
    if audio_spec.dialogue.source == "original":
        dialogue_path = project_dir / "analysis" / "dialogue.wav"
        await extract_audio(video_path, dialogue_path, sample_rate=44100, mono=False)
        tracks.append({
            "path": str(dialogue_path),
            "volume": audio_spec.dialogue.volume,
        })

    # Track 2: Background music
    if audio_spec.music:
        music_source = _resolve_path(audio_spec.music.source, project_dir)
        music_track: dict = {
            "path": str(music_source),
            "volume": audio_spec.music.volume,
            "fade_in": audio_spec.music.fade_in,
            "fade_out": audio_spec.music.fade_out,
        }

        # Build duck regions from speech regions
        if audio_spec.music.duck_under_speech and speech_regions:
            music_track["duck_regions"] = [
                {
                    "start": region.start,
                    "end": region.end,
                    "level": audio_spec.music.duck_level,
                }
                for region in speech_regions
            ]

        tracks.append(music_track)

    # Track 3+: Sound effects
    for sfx in audio_spec.sfx:
        sfx_source = _resolve_path(sfx.source, project_dir)
        tracks.append({
            "path": str(sfx_source),
            "volume": sfx.volume,
            "delay": sfx.at,
        })

    if not tracks:
        return None

    if len(tracks) == 1:
        # Single track - just encode it directly with fades, no mixing needed
        track = tracks[0]
        afilters = []
        vol = track.get("volume", 1.0)
        if vol != 1.0:
            afilters.append(f"volume={vol}")
        fade_in = track.get("fade_in", 0.0)
        fade_out = track.get("fade_out", 0.0)
        if fade_in > 0:
            afilters.append(f"afade=t=in:d={fade_in}")
        if fade_out > 0 and total_duration:
            afilters.append(f"afade=t=out:st={total_duration - fade_out}:d={fade_out}")

        from .ffmpeg import run_ffmpeg_checked
        args = ["-i", track["path"]]
        if afilters:
            args += ["-af", ",".join(afilters)]
        if total_duration:
            args += ["-t", f"{total_duration:.3f}"]
        args += ["-c:a", "aac", "-b:a", "192k", "-y", str(output_path)]
        await run_ffmpeg_checked(args)
        return output_path

    await mix_audio(tracks, output_path, duration=total_duration)
    return output_path


async def replace_audio(
    video_path: Path | str,
    audio_path: Path | str,
    output_path: Path | str,
) -> Path:
    """Replace a video's audio track with a new one."""
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-y", str(output_path),
    ]
    await run_ffmpeg_checked(args)
    return output_path


def _resolve_path(path_str: str, project_dir: Path) -> Path:
    """Resolve a path relative to the project directory."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return project_dir / p
