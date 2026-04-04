"""Video and image composition via MoviePy and FFmpeg.

Assembles final content by layering video, audio, captions, and music
into deliverable MP4 files. Also composes image posts with text overlays.
No fallback - raises on any failure.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from supercooked.config import OUTPUT_DIR, load_config
from supercooked.identity.action_log import log_action


def _output_dir(slug: str) -> Path:
    """Ensure and return the output directory for a given identity."""
    d = OUTPUT_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _compose_with_moviepy(
    video_path: Path,
    audio_path: Path | None,
    music_path: Path | None,
    caption_path: Path | None,
    output_path: Path,
    config_defaults: dict,
) -> None:
    """Synchronous MoviePy composition - runs in a thread.

    Layers the following onto a base video clip:
    1. Voice-over audio (replaces or mixes with original)
    2. Background music (mixed at reduced volume)
    3. Captions (burned in via SubtitlesClip if available)

    Falls through to FFmpeg for caption burning if MoviePy subtitle
    support is insufficient.
    """
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        VideoFileClip,
    )

    fps = config_defaults.get("fps", 30)

    # Load base video
    video_clip = VideoFileClip(str(video_path))

    # Build audio layers
    audio_layers = []

    # Original video audio (if any)
    if video_clip.audio is not None:
        audio_layers.append(video_clip.audio)

    # Voice-over audio
    if audio_path is not None:
        voice_clip = AudioFileClip(str(audio_path))
        # Trim voice to video length if needed
        if voice_clip.duration > video_clip.duration:
            voice_clip = voice_clip.subclipped(0, video_clip.duration)
        audio_layers = [voice_clip]  # Voice replaces original audio

    # Background music
    if music_path is not None:
        music_clip = AudioFileClip(str(music_path))
        # Loop music if shorter than video
        if music_clip.duration < video_clip.duration:
            music_clip = music_clip.looped(duration=video_clip.duration)
        elif music_clip.duration > video_clip.duration:
            music_clip = music_clip.subclipped(0, video_clip.duration)
        # Reduce music volume so it doesn't overpower voice
        music_clip = music_clip.with_volume_scaled(0.15)
        audio_layers.append(music_clip)

    # Composite audio
    if audio_layers:
        if len(audio_layers) == 1:
            final_audio = audio_layers[0]
        else:
            final_audio = CompositeAudioClip(audio_layers)
        video_clip = video_clip.with_audio(final_audio)

    # Write output
    video_clip.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,  # Suppress MoviePy progress bar
    )

    video_clip.close()


def _load_font(font_size: int):
    """Load the best available font at the given size."""
    from PIL import ImageFont

    # Project bundled font
    bundled = Path(__file__).parent.parent.parent / "assets" / "fonts" / "Montserrat-Bold.ttf"
    if bundled.exists():
        return ImageFont.truetype(str(bundled), font_size)

    # System fonts
    for path in [
        "Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, font_size)
        except (OSError, IOError):
            continue

    return ImageFont.load_default()


def _wrap_text_by_metrics(draw, text: str, font, max_width: int) -> list[str]:
    """Wrap text using actual font metrics instead of character-count heuristic."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def _compose_image_with_pillow(
    image_path: Path,
    caption_text: str,
    output_path: Path,
) -> None:
    """Synchronous image composition with text overlay using Pillow."""
    from PIL import Image, ImageDraw

    img = Image.open(str(image_path)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    width, height = img.size

    # Larger, more readable font size
    font_size = max(48, width // 12)
    font = _load_font(font_size)

    # Wrap text using actual font metrics
    padding = 40
    lines = _wrap_text_by_metrics(draw, caption_text, font, width - padding * 2)

    # Calculate text position (bottom area with padding)
    line_height = int(font_size * 1.3)
    total_text_height = len(lines) * line_height
    y_start = height - total_text_height - max(60, height // 10)

    # Draw gradient fade overlay (transparent to dark) instead of flat bar
    bg_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_overlay)
    gradient_start = y_start - 80
    gradient_end = height
    gradient_height = gradient_end - gradient_start
    for y in range(max(0, gradient_start), gradient_end):
        progress = (y - gradient_start) / gradient_height
        alpha = int(180 * progress)
        bg_draw.rectangle([0, y, width, y + 1], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, bg_overlay)
    draw = ImageDraw.Draw(img)

    # Draw text lines centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = y_start + i * line_height

        # Stroke / outline
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        # Main text
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    # Save as RGB (drop alpha for final output)
    img.convert("RGB").save(str(output_path), quality=95)


def _compose_story_with_pillow(
    image_path: Path,
    caption_text: str,
    output_path: Path,
) -> None:
    """Compose a vertical 1080x1920 story image with centered text and dramatic gradient."""
    from PIL import Image, ImageDraw

    img = Image.open(str(image_path)).convert("RGBA")
    # Resize/crop to 1080x1920 if needed
    img = img.resize((1080, 1920), Image.LANCZOS)

    width, height = img.size

    # Large, dramatic font for stories
    font_size = max(64, width // 8)
    font = _load_font(font_size)

    draw = ImageDraw.Draw(img)
    padding = 60
    lines = _wrap_text_by_metrics(draw, caption_text, font, width - padding * 2)

    line_height = int(font_size * 1.3)
    total_text_height = len(lines) * line_height

    # Center text vertically in lower third
    y_start = height - total_text_height - height // 6

    # Dramatic gradient overlay covering bottom half
    bg_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_overlay)
    gradient_start = height // 2
    gradient_height = height - gradient_start
    for y in range(gradient_start, height):
        progress = (y - gradient_start) / gradient_height
        alpha = int(200 * progress)
        bg_draw.rectangle([0, y, width, y + 1], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, bg_overlay)
    draw = ImageDraw.Draw(img)

    # Draw text centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = y_start + i * line_height

        # Thick stroke for readability
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    img.convert("RGB").save(str(output_path), quality=95)


async def compose_short(
    slug: str,
    video_path: Path | str,
    audio_path: Path | str | None = None,
    caption_path: Path | str | None = None,
    music_path: Path | str | None = None,
    output_path: Path | str | None = None,
) -> Path:
    """Compose a short-form video by layering video, audio, captions, and music.

    Parameters
    ----------
    slug:
        Identity slug - used for output path and action logging.
    video_path:
        Path to the base video file.
    audio_path:
        Optional path to a voice-over audio file (replaces original audio).
    caption_path:
        Optional path to an .srt file for caption overlay.
    music_path:
        Optional path to a background music file.
    output_path:
        Optional explicit output path. If None, auto-generates under output/<slug>/.

    Returns
    -------
    Path to the final composed .mp4 file.

    Raises
    ------
    RuntimeError
        If MoviePy/FFmpeg is not available or composition fails.
    FileNotFoundError
        If any input file does not exist.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if audio_path is not None:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if caption_path is not None:
        caption_path = Path(caption_path)
        if not caption_path.exists():
            raise FileNotFoundError(f"Caption file not found: {caption_path}")

    if music_path is not None:
        music_path = Path(music_path)
        if not music_path.exists():
            raise FileNotFoundError(f"Music file not found: {music_path}")

    # Determine output path
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_id = uuid.uuid4().hex[:12]
        out = _output_dir(slug) / f"short_{file_id}.mp4"

    config = load_config()
    config_defaults = {
        "fps": config.defaults.video.fps,
        "resolution": config.defaults.video.resolution,
    }

    # Step 1: Compose video + audio + music with MoviePy
    try:
        await asyncio.to_thread(
            _compose_with_moviepy,
            video_path,
            audio_path,
            music_path,
            None,  # Captions handled separately via FFmpeg
            out,
            config_defaults,
        )
    except ImportError as exc:
        log_action(
            slug,
            action="compose_short",
            platform="moviepy",
            details={"video": str(video_path)},
            error=f"MoviePy not available: {exc}",
        )
        raise RuntimeError(
            f"MoviePy is not installed. Install it with: pip install moviepy. Error: {exc}"
        ) from exc
    except Exception as exc:
        log_action(
            slug,
            action="compose_short",
            platform="moviepy",
            details={"video": str(video_path)},
            error=str(exc),
        )
        raise RuntimeError(f"Video composition failed: {exc}") from exc

    # Step 2: Burn captions onto the composed video if provided
    if caption_path is not None:
        from supercooked.create.caption import overlay_captions

        captioned_path = out.with_name(out.stem + "_captioned" + out.suffix)
        try:
            await overlay_captions(out, caption_path, captioned_path)
            # Replace the uncaptioned version with the captioned one safely
            # Rename first (atomic on same filesystem), then delete backup
            backup_path = out.with_suffix(".bak")
            out.rename(backup_path)
            captioned_path.rename(out)
            backup_path.unlink()
        except Exception as exc:
            # If caption overlay fails, keep the uncaptioned version
            log_action(
                slug,
                action="compose_short",
                platform="ffmpeg",
                details={"caption_path": str(caption_path)},
                error=f"Caption overlay failed (keeping uncaptioned video): {exc}",
            )
            raise RuntimeError(f"Caption overlay failed: {exc}") from exc

    log_action(
        slug,
        action="compose_short",
        platform="moviepy",
        details={
            "video_path": str(video_path),
            "audio_path": str(audio_path) if audio_path else None,
            "caption_path": str(caption_path) if caption_path else None,
            "music_path": str(music_path) if music_path else None,
            "output_path": str(out),
        },
        result=str(out),
    )

    return out


async def compose_image_post(
    slug: str,
    image_path: Path | str,
    caption_text: str,
    output_path: Path | str | None = None,
) -> Path:
    """Compose an image post with caption text overlay.

    Parameters
    ----------
    slug:
        Identity slug - used for output path and action logging.
    image_path:
        Path to the base image.
    caption_text:
        Text to overlay on the image.
    output_path:
        Optional explicit output path. If None, auto-generates under output/<slug>/.

    Returns
    -------
    Path to the composed image.

    Raises
    ------
    RuntimeError
        If Pillow is not available or composition fails.
    FileNotFoundError
        If the image file does not exist.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_id = uuid.uuid4().hex[:12]
        out = _output_dir(slug) / f"post_{file_id}.png"

    try:
        await asyncio.to_thread(
            _compose_image_with_pillow,
            image_path,
            caption_text,
            out,
        )
    except ImportError as exc:
        log_action(
            slug,
            action="compose_image_post",
            platform="pillow",
            details={"image": str(image_path)},
            error=f"Pillow not available: {exc}",
        )
        raise RuntimeError(
            f"Pillow is not installed. Install it with: pip install Pillow. Error: {exc}"
        ) from exc
    except Exception as exc:
        log_action(
            slug,
            action="compose_image_post",
            platform="pillow",
            details={"image": str(image_path)},
            error=str(exc),
        )
        raise RuntimeError(f"Image post composition failed: {exc}") from exc

    log_action(
        slug,
        action="compose_image_post",
        platform="pillow",
        details={
            "image_path": str(image_path),
            "caption_length": len(caption_text),
            "output_path": str(out),
        },
        result=str(out),
    )

    return out


async def compose_story_image(
    slug: str,
    image_path: Path | str,
    caption_text: str,
    output_path: Path | str | None = None,
) -> Path:
    """Compose a story image with dramatic text overlay (vertical 1080x1920).

    Parameters
    ----------
    slug:
        Identity slug.
    image_path:
        Path to the base image.
    caption_text:
        Text to overlay on the story image.
    output_path:
        Optional explicit output path.

    Returns
    -------
    Path to the composed story image.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_id = uuid.uuid4().hex[:12]
        out = _output_dir(slug) / f"story_{file_id}.png"

    try:
        await asyncio.to_thread(
            _compose_story_with_pillow,
            image_path,
            caption_text,
            out,
        )
    except Exception as exc:
        log_action(
            slug,
            action="compose_story_image",
            platform="pillow",
            details={"image": str(image_path)},
            error=str(exc),
        )
        raise RuntimeError(f"Story image composition failed: {exc}") from exc

    log_action(
        slug,
        action="compose_story_image",
        platform="pillow",
        details={
            "image_path": str(image_path),
            "caption_length": len(caption_text),
            "output_path": str(out),
        },
        result=str(out),
    )

    return out
