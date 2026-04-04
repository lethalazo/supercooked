"""FFmpeg command builder and probe utility.

Typed, safe interface to FFmpeg - no raw shell strings. Every command
is built as a list of arguments and run via asyncio subprocess.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from supercooked.config import load_config

from .models import ExportProfile, GradePreset, SourceInfo


def _ffmpeg_bin() -> str:
    """Get FFmpeg binary path from config or system."""
    config = load_config()
    return config.tools.ffmpeg


def _ffprobe_bin() -> str:
    """Get ffprobe binary path (sibling to ffmpeg)."""
    ffmpeg = _ffmpeg_bin()
    if ffmpeg == "ffmpeg":
        return "ffprobe"
    # If ffmpeg is a full path, derive ffprobe from same directory
    p = Path(ffmpeg)
    return str(p.parent / "ffprobe")


async def run_ffmpeg(args: list[str], timeout: float = 600) -> tuple[int, str, str]:
    """Run an FFmpeg command and return (returncode, stdout, stderr).

    Parameters
    ----------
    args:
        Arguments to pass AFTER the ffmpeg binary name.
    timeout:
        Maximum seconds to wait. Default 10 minutes.

    Returns
    -------
    Tuple of (return code, stdout text, stderr text).
    """
    cmd = [_ffmpeg_bin()] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"FFmpeg timed out after {timeout}s")

    return process.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def run_ffmpeg_checked(args: list[str], timeout: float = 600) -> str:
    """Run FFmpeg and raise on non-zero exit."""
    code, stdout, stderr = await run_ffmpeg(args, timeout=timeout)
    if code != 0:
        raise RuntimeError(f"FFmpeg failed (exit {code}):\n{stderr[-2000:]}")
    return stderr  # FFmpeg writes progress to stderr


async def probe(path: Path | str) -> dict:
    """Run ffprobe and return parsed JSON metadata.

    Returns the full ffprobe JSON output with format and stream info.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    cmd = [
        _ffprobe_bin(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed for {path}: {stderr.decode(errors='replace')}"
        )

    return json.loads(stdout.decode())


async def probe_source_info(path: Path | str) -> SourceInfo:
    """Probe a video file and return structured SourceInfo."""
    path = Path(path)
    data = await probe(path)

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration_s = float(fmt.get("duration", 0))
    hours = int(duration_s // 3600)
    minutes = int((duration_s % 3600) // 60)
    seconds = int(duration_s % 60)
    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)

    # Parse FPS from r_frame_rate (e.g. "30000/1001")
    fps = 0.0
    r_frame_rate = video_stream.get("r_frame_rate", "0/1")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        if int(den) > 0:
            fps = round(int(num) / int(den), 2)

    file_size_mb = round(int(fmt.get("size", 0)) / (1024 * 1024), 1)

    return SourceInfo(
        file=path.name,
        duration=duration_str,
        duration_seconds=round(duration_s, 2),
        resolution=f"{width}x{height}" if width else "",
        fps=fps,
        codec=video_stream.get("codec_name", ""),
        audio_codec=audio_stream.get("codec_name", ""),
        audio_channels=audio_stream.get("channels", 0),
        audio_sample_rate=int(audio_stream.get("sample_rate", 0)),
        file_size_mb=file_size_mb,
    )


async def extract_audio(
    video_path: Path | str,
    output_path: Path | str,
    sample_rate: int = 16000,
    mono: bool = True,
) -> Path:
    """Extract audio from video as WAV (for Whisper)."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
    ]
    if mono:
        args += ["-ac", "1"]
    args += ["-y", str(output_path)]

    await run_ffmpeg_checked(args)
    return output_path


async def extract_frame(
    video_path: Path | str,
    timestamp: float,
    output_path: Path | str,
    width: int = 960,
    height: int = 540,
) -> Path:
    """Extract a single frame as JPEG at the given timestamp."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-ss", f"{timestamp:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        "-q:v", "3",  # JPEG quality (2=best, 31=worst)
        "-y",
        str(output_path),
    ]

    await run_ffmpeg_checked(args)
    return output_path


async def detect_scenes(
    video_path: Path | str,
    threshold: float = 0.3,
) -> list[dict]:
    """Detect scene changes using FFmpeg's scdet filter.

    Returns list of dicts with 'timestamp' and 'score' keys.
    """
    video_path = Path(video_path)
    args = [
        "-i", str(video_path),
        "-vf", f"scdet=s=1:t={threshold}",
        "-f", "null",
        "-",
    ]

    _code, _stdout, stderr = await run_ffmpeg(args, timeout=1200)

    # Parse scdet output from stderr
    # Format: [scdet @ 0x...] lavfi.scd.time: 12.345 lavfi.scd.score: 0.678
    scenes = []
    for line in stderr.split("\n"):
        if "lavfi.scd.time" in line:
            try:
                parts = line.split("lavfi.scd.time:")[1]
                time_str = parts.split("lavfi.scd.score:")[0].strip()
                score_str = parts.split("lavfi.scd.score:")[1].strip().split()[0]
                scenes.append({
                    "timestamp": float(time_str),
                    "score": float(score_str),
                })
            except (IndexError, ValueError):
                continue

    return scenes


async def detect_silence(
    audio_path: Path | str,
    noise_db: float = -30,
    min_duration: float = 0.5,
) -> list[dict]:
    """Detect silence regions using FFmpeg's silencedetect filter.

    Returns list of dicts with 'start' and 'end' keys.
    """
    audio_path = Path(audio_path)
    args = [
        "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null",
        "-",
    ]

    _code, _stdout, stderr = await run_ffmpeg(args)

    # Parse silencedetect output
    # [silencedetect @ 0x...] silence_start: 12.345
    # [silencedetect @ 0x...] silence_end: 14.567 | silence_duration: 2.222
    silences = []
    current_start = None
    for line in stderr.split("\n"):
        if "silence_start:" in line:
            try:
                current_start = float(line.split("silence_start:")[1].strip().split()[0])
            except (IndexError, ValueError):
                current_start = None
        elif "silence_end:" in line and current_start is not None:
            try:
                end = float(line.split("silence_end:")[1].strip().split()[0])
                silences.append({"start": current_start, "end": end})
            except (IndexError, ValueError):
                pass
            current_start = None

    return silences


async def measure_loudness(audio_path: Path | str) -> dict:
    """Measure integrated loudness using FFmpeg's loudnorm filter (first pass).

    Returns dict with 'integrated', 'range', 'peak' keys (all floats).
    """
    audio_path = Path(audio_path)
    args = [
        "-i", str(audio_path),
        "-af", "loudnorm=print_format=json",
        "-f", "null",
        "-",
    ]

    _code, _stdout, stderr = await run_ffmpeg(args)

    # Parse the JSON block from loudnorm output
    result = {"integrated": -23.0, "range": 0.0, "peak": 0.0}
    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
        try:
            data = json.loads(stderr[json_start:json_end])
            result["integrated"] = float(data.get("input_i", -23.0))
            result["range"] = float(data.get("input_lra", 0.0))
            result["peak"] = float(data.get("input_tp", 0.0))
        except (json.JSONDecodeError, ValueError):
            pass

    return result


async def image_to_video(
    image_path: Path | str,
    output_path: Path | str,
    duration: float = 5.0,
    resolution: str = "1920x1080",
    fps: int = 30,
    zoom: float = 0.0,
    grade_filter: str | None = None,
) -> Path:
    """Convert a static image into a video clip.

    Scales the image to fill the target resolution (center-crop, no letterbox),
    then optionally applies a slow Ken Burns zoom and/or color grade.

    Parameters
    ----------
    zoom:
        Ken Burns zoom amount per second. 0 = static. 0.03 = subtle push-in.
        Implemented as zoompan filter.
    """
    image_path = Path(image_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = resolution.split("x")
    total_frames = int(duration * fps)

    vfilters = []

    if zoom > 0:
        # Ken Burns: slow zoom from 1.0x to (1 + zoom*duration)x, centered
        end_zoom = 1.0 + zoom * duration
        # zoompan: z goes from 1.0 to end_zoom linearly over total_frames
        vfilters.append(
            f"zoompan=z='1+{zoom}*in_time'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={w}x{h}:fps={fps}"
        )
    else:
        # Static: scale to fill, center-crop
        vfilters.append(
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}"
        )

    if grade_filter:
        vfilters.append(grade_filter)

    args = [
        "-loop", "1",
        "-i", str(image_path),
        "-t", f"{duration:.3f}",
        "-vf", ",".join(vfilters),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        # Generate silent audio track so concat works with video segments
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-y", str(output_path),
    ]

    await run_ffmpeg_checked(args)
    return output_path


def _build_atempo_chain(speed: float) -> list[str]:
    """Build a chain of atempo filters for the given speed.

    FFmpeg's atempo filter only accepts values in [0.5, 100.0].
    For speeds outside this range, chain multiple filters.
    E.g., speed=0.25 → atempo=0.5,atempo=0.5
    """
    filters = []
    remaining = speed
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 100.0:
        filters.append("atempo=100.0")
        remaining /= 100.0
    # Add final filter if remaining isn't 1.0 (i.e., still needs adjustment)
    if abs(remaining - 1.0) > 0.001:
        filters.append(f"atempo={remaining}")
    return filters or [f"atempo={speed}"]


async def cut_segment(
    video_path: Path | str,
    output_path: Path | str,
    start: float,
    end: float,
    speed: float = 1.0,
    mute: bool = False,
    volume: float = 1.0,
    grade_filter: str | None = None,
) -> Path:
    """Cut a segment from video with optional speed/grade adjustments.

    Uses stream copy when possible (speed=1.0, no grade), re-encodes otherwise.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if speed <= 0:
        raise ValueError(f"Speed must be positive, got {speed}")

    needs_reencode = speed != 1.0 or grade_filter or mute or volume != 1.0

    args = ["-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video_path)]

    if needs_reencode:
        # Build video filter chain
        vfilters = []
        if speed != 1.0:
            vfilters.append(f"setpts={1/speed}*PTS")
        if grade_filter:
            vfilters.append(grade_filter)

        if vfilters:
            args += ["-vf", ",".join(vfilters)]

        # Audio handling - always keep an audio track (even if silent)
        # so that concat doesn't fail on mixed muted/unmuted segments
        afilters = []
        if mute:
            afilters.append("volume=0")
        else:
            if speed != 1.0:
                # atempo only accepts 0.5-100.0, chain for extreme values
                afilters.extend(_build_atempo_chain(speed))
            if volume != 1.0:
                afilters.append(f"volume={volume}")
        if afilters:
            args += ["-af", ",".join(afilters)]

        args += ["-c:v", "libx264", "-crf", "18", "-preset", "medium"]
        args += ["-c:a", "aac", "-b:a", "192k"]
    else:
        # Stream copy - fast, no re-encode
        args += ["-c", "copy"]

    args += ["-y", str(output_path)]
    await run_ffmpeg_checked(args)
    return output_path


async def concat_segments(
    segment_paths: list[Path | str],
    output_path: Path | str,
    transitions: list[dict] | None = None,
) -> Path:
    """Concatenate video segments into a single file.

    If no transitions (all cuts), uses the concat demuxer (fast).
    If transitions exist, uses xfade filter (re-encodes).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    has_transitions = transitions and any(
        t.get("type", "cut") != "cut" for t in transitions
    )

    if not has_transitions:
        # Fast concat via demuxer
        concat_file = output_path.parent / f".concat_{output_path.stem}.txt"
        lines = [f"file '{Path(p).resolve()}'" for p in segment_paths]
        concat_file.write_text("\n".join(lines))

        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            "-y", str(output_path),
        ]
        try:
            await run_ffmpeg_checked(args)
        finally:
            concat_file.unlink(missing_ok=True)
    else:
        # xfade transitions - requires re-encoding
        # Build complex filter graph
        n = len(segment_paths)
        inputs = []
        for p in segment_paths:
            inputs += ["-i", str(Path(p).resolve())]

        # Get durations for offset calculation
        durations = []
        for p in segment_paths:
            info = await probe(p)
            d = float(info.get("format", {}).get("duration", 0))
            durations.append(d)

        if n == 1:
            # Single segment, just copy
            args = inputs + ["-c", "copy", "-y", str(output_path)]
            await run_ffmpeg_checked(args)
            return output_path

        # Build xfade chain
        filter_parts = []
        offset = 0.0
        prev_label = "[0:v]"

        for i in range(1, n):
            t = transitions[i - 1] if transitions and i - 1 < len(transitions) else {}
            t_type = t.get("type", "cut")
            t_dur = t.get("duration", 0.5)

            if t_type == "cut":
                t_type = "fade"
                t_dur = 0.0

            offset += durations[i - 1] - t_dur
            out_label = f"[v{i}]" if i < n - 1 else "[vout]"
            filter_parts.append(
                f"{prev_label}[{i}:v]xfade=transition={t_type}"
                f":duration={t_dur}:offset={offset:.3f}{out_label}"
            )
            prev_label = out_label

        # Audio concat (simple)
        audio_inputs = "".join(f"[{i}:a]" for i in range(n))
        filter_parts.append(
            f"{audio_inputs}concat=n={n}:v=0:a=1[aout]"
        )

        filter_graph = ";".join(filter_parts)
        args = inputs + [
            "-filter_complex", filter_graph,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-y", str(output_path),
        ]
        await run_ffmpeg_checked(args)

    return output_path


async def apply_grade(
    video_path: Path | str,
    output_path: Path | str,
    filter_chain: str,
) -> Path:
    """Apply a color grading filter chain to a video."""
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "-i", str(video_path),
        "-vf", filter_chain,
        "-c:a", "copy",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-y", str(output_path),
    ]
    await run_ffmpeg_checked(args)
    return output_path


async def overlay_image(
    video_path: Path | str,
    image_path: Path | str,
    output_path: Path | str,
    x: str = "0",
    y: str = "0",
    start: float | None = None,
    end: float | None = None,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> Path:
    """Overlay a PNG image on video with optional fade and timing."""
    video_path = Path(video_path)
    image_path = Path(image_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build filter for the overlay input
    overlay_filters = []

    if fade_in > 0 and start is not None:
        overlay_filters.append(
            f"fade=t=in:st={start}:d={fade_in}:alpha=1"
        )
    if fade_out > 0 and end is not None:
        overlay_filters.append(
            f"fade=t=out:st={end - fade_out}:d={fade_out}:alpha=1"
        )

    # Build the filter complex
    if overlay_filters:
        overlay_filter_str = ",".join(overlay_filters)
        filter_complex = (
            f"[1:v]{overlay_filter_str}[ovr];[0:v][ovr]overlay={x}:{y}"
        )
    else:
        filter_complex = f"[0:v][1:v]overlay={x}:{y}"

    if start is not None and end is not None:
        filter_complex += f":enable='between(t,{start},{end})'"

    # Probe video duration so the looped PNG covers the full timeline
    video_info = await probe(video_path)
    video_duration = float(video_info.get("format", {}).get("duration", 60))

    args = [
        "-i", str(video_path),
        "-loop", "1", "-t", f"{video_duration:.3f}",
        "-i", str(image_path),
        "-filter_complex", filter_complex,
        "-c:a", "copy",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-shortest",
        "-y", str(output_path),
    ]
    await run_ffmpeg_checked(args)
    return output_path


async def mix_audio(
    tracks: list[dict],
    output_path: Path | str,
    duration: float | None = None,
) -> Path:
    """Mix multiple audio tracks together.

    Each track dict: {path, volume, delay, fade_in, fade_out,
                      duck_regions: [{start, end, level}]}

    fade_in/fade_out: seconds to fade the track in/out (applied after volume).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inputs = []
    filters = []

    for i, track in enumerate(tracks):
        inputs += ["-i", str(track["path"])]
        vol = track.get("volume", 1.0)
        delay = track.get("delay", 0.0)
        fade_in = track.get("fade_in", 0.0)
        fade_out = track.get("fade_out", 0.0)

        afilters = []
        if delay > 0:
            afilters.append(f"adelay={int(delay * 1000)}|{int(delay * 1000)}")
        if vol != 1.0:
            afilters.append(f"volume={vol}")

        # Ducking: lower volume during speech regions
        duck_regions = track.get("duck_regions", [])
        for region in duck_regions:
            duck_level = region.get("level", 0.1)
            afilters.append(
                f"volume=enable='between(t,{region['start']},{region['end']})':"
                f"volume={duck_level}"
            )

        # Fade in/out
        if fade_in > 0:
            afilters.append(f"afade=t=in:d={fade_in}")
        if fade_out > 0 and duration:
            afilters.append(f"afade=t=out:st={duration - fade_out}:d={fade_out}")

        if afilters:
            filters.append(f"[{i}:a]{','.join(afilters)}[a{i}]")
        else:
            filters.append(f"[{i}:a]acopy[a{i}]")

    # Amerge all tracks
    n = len(tracks)
    merge_inputs = "".join(f"[a{i}]" for i in range(n))
    filters.append(f"{merge_inputs}amix=inputs={n}:duration=longest[out]")

    filter_graph = ";".join(filters)

    args = inputs + [
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
    ]
    if duration:
        args += ["-t", f"{duration:.3f}"]
    args += ["-y", str(output_path)]

    await run_ffmpeg_checked(args)
    return output_path


def build_grade_filter(preset: GradePreset) -> str:
    """Build an FFmpeg video filter string from a grade preset."""
    if preset.filter_chain:
        return preset.filter_chain

    filters = []
    if preset.brightness != 0.0 or preset.gamma != 1.0 or preset.saturation != 1.0:
        parts = []
        if preset.brightness != 0.0:
            parts.append(f"brightness={preset.brightness}")
        if preset.gamma != 1.0:
            parts.append(f"gamma={preset.gamma}")
        if preset.saturation != 1.0:
            parts.append(f"saturation={preset.saturation}")
        filters.append(f"eq={':'.join(parts)}")

    if preset.contrast != 1.0:
        filters.append(f"eq=contrast={preset.contrast}")

    return ",".join(filters) if filters else "null"


def build_export_args(profile: ExportProfile) -> list[str]:
    """Build FFmpeg output encoding arguments from an export profile."""
    width, height = profile.resolution.split("x")
    args = [
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(profile.fps),
        "-c:v", profile.codec,
        "-crf", str(profile.crf),
        "-preset", "medium",
        "-pix_fmt", profile.pixel_format,
        "-c:a", profile.audio_codec,
        "-b:a", profile.audio_bitrate,
    ]
    if profile.max_bitrate:
        args += ["-maxrate", profile.max_bitrate, "-bufsize", f"{profile.max_bitrate}"]
    return args
