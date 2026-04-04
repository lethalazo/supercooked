"""Caption generation via OpenAI Whisper and styled SRT overlay.

Wraps openai-whisper for transcription and MoviePy/FFmpeg for burning
captions onto video. No fallback - raises on any failure.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from supercooked.config import OUTPUT_DIR, load_config


def _output_dir_generic() -> Path:
    """Ensure and return the generic output directory."""
    d = OUTPUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _style_text_capcut(text: str) -> str:
    """Apply CapCut-style formatting - uppercase, one or two words per line.

    CapCut-style captions typically show 1-3 words at a time in bold uppercase
    for maximum readability on mobile.
    """
    words = text.strip().split()
    # Group into chunks of 2 words for that punchy CapCut look
    chunks = []
    for i in range(0, len(words), 2):
        chunk = " ".join(words[i : i + 2])
        chunks.append(chunk.upper())
    return "\n".join(chunks)


def _style_text_default(text: str) -> str:
    """Default styling - clean text, no transformation."""
    return text.strip()


def _style_text(text: str, style: str) -> str:
    """Apply a text style to caption text."""
    styles = {
        "capcut": _style_text_capcut,
        "default": _style_text_default,
    }
    fn = styles.get(style, _style_text_default)
    return fn(text)


def _segments_to_srt(segments: list[dict], style: str) -> str:
    """Convert Whisper segments to SRT format with styling.

    Parameters
    ----------
    segments:
        List of dicts with 'start', 'end', 'text' keys from Whisper.
    style:
        Caption style to apply ("capcut", "default").

    Returns
    -------
    SRT file content as a string.
    """
    srt_lines = []

    if style == "capcut":
        # For CapCut style, break each segment into word-level chunks
        counter = 1
        for seg in segments:
            words = seg["text"].strip().split()
            if not words:
                continue
            duration = seg["end"] - seg["start"]
            word_duration = duration / len(words) if words else duration

            # Group into chunks of 2 words
            for i in range(0, len(words), 2):
                chunk_words = words[i : i + 2]
                chunk_text = " ".join(chunk_words).upper()
                chunk_start = seg["start"] + i * word_duration
                chunk_end = min(seg["start"] + (i + len(chunk_words)) * word_duration, seg["end"])

                srt_lines.append(str(counter))
                srt_lines.append(
                    f"{_format_srt_timestamp(chunk_start)} --> "
                    f"{_format_srt_timestamp(chunk_end)}"
                )
                srt_lines.append(chunk_text)
                srt_lines.append("")
                counter += 1
    else:
        # Default: one subtitle per Whisper segment
        for idx, seg in enumerate(segments, start=1):
            srt_lines.append(str(idx))
            srt_lines.append(
                f"{_format_srt_timestamp(seg['start'])} --> "
                f"{_format_srt_timestamp(seg['end'])}"
            )
            srt_lines.append(_style_text(seg["text"], style))
            srt_lines.append("")

    return "\n".join(srt_lines)


async def generate_captions(
    audio_path: Path | str,
    output_path: Path | str | None = None,
    style: str = "capcut",
) -> Path:
    """Transcribe audio with Whisper and generate a styled SRT file.

    Parameters
    ----------
    audio_path:
        Path to the audio file to transcribe.
    output_path:
        Optional explicit output path for the .srt file.
    style:
        Caption style - "capcut" (word-by-word uppercase) or "default".

    Returns
    -------
    Path to the generated .srt file.

    Raises
    ------
    RuntimeError
        If Whisper is not available or transcription fails.
    FileNotFoundError
        If the audio file does not exist.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    config = load_config()
    whisper_model_name = config.tools.whisper_model

    # Import whisper at call time - it's heavy and optional
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "openai-whisper is not installed. "
            "Install it with: pip install openai-whisper"
        ) from exc

    # Load model and transcribe in a thread to avoid blocking the event loop
    try:
        model = await asyncio.to_thread(whisper.load_model, whisper_model_name)
        result = await asyncio.to_thread(
            model.transcribe,
            str(audio_path),
            word_timestamps=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Whisper transcription failed: {exc}") from exc

    segments = result.get("segments", [])
    if not segments:
        raise RuntimeError(f"Whisper produced no segments for: {audio_path}")

    # Generate SRT content
    srt_content = _segments_to_srt(segments, style)

    # Determine output path
    if output_path is not None:
        out = Path(output_path)
    else:
        out = audio_path.with_suffix(".srt")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt_content, encoding="utf-8")

    return out


async def overlay_captions(
    video_path: Path | str,
    srt_path: Path | str,
    output_path: Path | str,
) -> Path:
    """Burn SRT captions onto a video using FFmpeg.

    Parameters
    ----------
    video_path:
        Path to the input video file.
    srt_path:
        Path to the .srt caption file.
    output_path:
        Path for the output video with captions burned in.

    Returns
    -------
    Path to the output video.

    Raises
    ------
    RuntimeError
        If FFmpeg is not available or the overlay fails.
    FileNotFoundError
        If the video or SRT file does not exist.
    """
    video_path = Path(video_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not srt_path.exists():
        raise FileNotFoundError(f"SRT file not found: {srt_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = load_config()
    ffmpeg_bin = config.tools.ffmpeg
    caption_defaults = config.defaults.captions

    # Build FFmpeg subtitles filter with styling
    # Escape special characters in the SRT path for the filter
    srt_escaped = str(srt_path).replace("\\", "\\\\").replace(":", "\\:")
    subtitles_filter = (
        f"subtitles='{srt_escaped}'"
        f":force_style='FontName={caption_defaults.font}"
        f",FontSize={caption_defaults.font_size}"
        f",PrimaryColour=&H00{caption_defaults.color.lstrip('#')[-2:]}"
        f"{caption_defaults.color.lstrip('#')[2:4]}"
        f"{caption_defaults.color.lstrip('#')[:2]}"
        f",OutlineColour=&H00{caption_defaults.stroke_color.lstrip('#')[-2:]}"
        f"{caption_defaults.stroke_color.lstrip('#')[2:4]}"
        f"{caption_defaults.stroke_color.lstrip('#')[:2]}"
        f",Outline={caption_defaults.stroke_width}"
        f",Alignment=2"
        f",MarginV=60'"
    )

    cmd = [
        ffmpeg_bin,
        "-i", str(video_path),
        "-vf", subtitles_filter,
        "-c:a", "copy",
        "-y",
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
    except FileNotFoundError:
        raise RuntimeError(
            f"FFmpeg not found at '{ffmpeg_bin}'. "
            f"Install FFmpeg or set tools.ffmpeg in supercooked.yaml"
        )

    if process.returncode != 0:
        error_msg = stderr.decode(errors="replace")
        raise RuntimeError(f"FFmpeg caption overlay failed (exit {process.returncode}): {error_msg}")

    if not output_path.exists():
        raise RuntimeError(f"FFmpeg completed but output file not found: {output_path}")

    return output_path
