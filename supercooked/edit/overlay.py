"""Text overlay PNG generation using Pillow.

Generates transparent PNG overlays for titles, lower thirds, captions,
and watermarks. These are composited onto video via FFmpeg's overlay
filter (same pattern as nooraana IG reel production).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .models import TextOverlay, TextPosition, TextStyle, WatermarkConfig

# Lazy-loaded font paths
_FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"


def _load_font(name: str, size: int):
    """Load a font, falling back to default if not found."""
    from PIL import ImageFont

    # Try bundled fonts first
    candidates = [
        _FONT_DIR / f"{name}.ttf",
        _FONT_DIR / f"{name}.otf",
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)

    # Fall back to Montserrat-Bold (always available in SuperCooked)
    default = _FONT_DIR / "Montserrat-Bold.ttf"
    if default.exists():
        return ImageFont.truetype(str(default), size)

    return ImageFont.load_default()


# Style → font/size/position defaults
_STYLE_DEFAULTS = {
    TextStyle.TITLE: {
        "font": "Montserrat-Bold",
        "size": 72,
        "color": (255, 255, 255, 255),
        "stroke_color": (0, 0, 0, 200),
        "stroke_width": 3,
        "position": TextPosition.CENTER,
    },
    TextStyle.LOWER_THIRD: {
        "font": "Montserrat-Bold",
        "size": 42,
        "color": (255, 255, 255, 255),
        "stroke_color": (0, 0, 0, 180),
        "stroke_width": 2,
        "position": TextPosition.BOTTOM_LEFT,
        "bg_color": (0, 0, 0, 140),
        "bg_padding": 20,
    },
    TextStyle.CAPTION: {
        "font": "Montserrat-Bold",
        "size": 48,
        "color": (255, 255, 255, 255),
        "stroke_color": (0, 0, 0, 200),
        "stroke_width": 3,
        "position": TextPosition.BOTTOM_CENTER,
    },
    TextStyle.WATERMARK: {
        "font": "Montserrat-Bold",
        "size": 20,
        "color": (255, 255, 255, 128),
        "stroke_color": None,
        "stroke_width": 0,
        "position": TextPosition.BOTTOM_RIGHT,
    },
}


def _position_to_xy(
    position: TextPosition,
    text_width: int,
    text_height: int,
    canvas_width: int,
    canvas_height: int,
    padding: int = 40,
) -> tuple[int, int]:
    """Convert a TextPosition enum to (x, y) coordinates."""
    positions = {
        TextPosition.TOP_LEFT: (padding, padding),
        TextPosition.TOP_CENTER: ((canvas_width - text_width) // 2, padding),
        TextPosition.TOP_RIGHT: (canvas_width - text_width - padding, padding),
        TextPosition.CENTER: (
            (canvas_width - text_width) // 2,
            (canvas_height - text_height) // 2,
        ),
        TextPosition.BOTTOM_LEFT: (padding, canvas_height - text_height - padding),
        TextPosition.BOTTOM_CENTER: (
            (canvas_width - text_width) // 2,
            canvas_height - text_height - padding,
        ),
        TextPosition.BOTTOM_RIGHT: (
            canvas_width - text_width - padding,
            canvas_height - text_height - padding,
        ),
    }
    return positions.get(position, (padding, padding))


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within max_width using font metrics."""
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines or [text]


def generate_text_overlay(
    text_spec: TextOverlay,
    width: int = 1920,
    height: int = 1080,
    output_path: Path | str | None = None,
) -> Path:
    """Generate a transparent PNG with styled text.

    Parameters
    ----------
    text_spec:
        Text content, style, and position specification.
    width, height:
        Canvas dimensions (should match video resolution).
    output_path:
        Where to save the PNG. Auto-generated if None.

    Returns
    -------
    Path to the generated PNG.
    """
    from PIL import Image, ImageDraw

    style_defaults = _STYLE_DEFAULTS.get(text_spec.style, _STYLE_DEFAULTS[TextStyle.CAPTION])

    font_size = text_spec.font_size or style_defaults["size"]
    font = _load_font(style_defaults["font"], font_size)

    # Parse color from hex
    color = _hex_to_rgba(text_spec.color) if text_spec.color != "#FFFFFF" else style_defaults["color"]
    stroke_color = style_defaults.get("stroke_color")
    stroke_width = style_defaults.get("stroke_width", 0)

    # Create transparent canvas
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Wrap text
    max_text_width = int(width * 0.8)
    lines = _wrap_text(draw, text_spec.content, font, max_text_width)

    # Calculate text block dimensions
    line_height = font_size + 8
    total_text_height = len(lines) * line_height
    max_line_width = max(
        draw.textbbox((0, 0), line, font=font)[2] for line in lines
    )

    # Position
    position = text_spec.position or style_defaults.get("position", TextPosition.CENTER)
    base_x, base_y = _position_to_xy(
        position, max_line_width, total_text_height, width, height,
    )

    # Optional background bar (for lower thirds)
    bg_color = style_defaults.get("bg_color")
    bg_padding = style_defaults.get("bg_padding", 0)
    if bg_color:
        draw.rectangle(
            [
                base_x - bg_padding,
                base_y - bg_padding // 2,
                base_x + max_line_width + bg_padding,
                base_y + total_text_height + bg_padding // 2,
            ],
            fill=bg_color,
        )

    # Draw text
    for i, line in enumerate(lines):
        y = base_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]

        # Center each line within the text block for centered positions
        if position in (TextPosition.CENTER, TextPosition.TOP_CENTER, TextPosition.BOTTOM_CENTER):
            x = (width - line_width) // 2
        else:
            x = base_x

        # Stroke/outline
        if stroke_color and stroke_width > 0:
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=stroke_color)

        # Main text
        draw.text((x, y), line, font=font, fill=color)

    # Save
    if output_path is None:
        output_path = Path(f"/tmp/overlay_{id(text_spec)}.png")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")

    return output_path


def generate_watermark(
    config: WatermarkConfig,
    width: int = 1920,
    height: int = 1080,
    output_path: Path | str | None = None,
) -> Path:
    """Generate a watermark overlay PNG."""
    if not config.text:
        raise ValueError("Watermark text is empty")

    overlay = TextOverlay(
        content=config.text,
        style=TextStyle.WATERMARK,
        position=config.position,
        font_size=config.font_size,
        color=f"#FFFFFF{int(255 * config.opacity):02x}",
    )
    return generate_text_overlay(overlay, width, height, output_path)


async def generate_segment_overlays(
    edl,
    project_dir: Path,
    width: int = 1920,
    height: int = 1080,
) -> list[dict]:
    """Generate all text overlay PNGs for all segments in the EDL.

    Returns list of dicts: {segment_id, overlay_path, at, duration, position}
    """
    overlays_dir = project_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for seg in edl.segments:
        for j, text in enumerate(seg.text):
            fname = f"{seg.id}_text_{j:02d}.png"
            out_path = overlays_dir / fname

            await asyncio.to_thread(
                generate_text_overlay,
                text,
                width,
                height,
                out_path,
            )

            results.append({
                "segment_id": seg.id,
                "overlay_path": str(out_path),
                "at": text.at,
                "duration": text.duration,
                "position": text.position.value if text.position else "center",
                "fade_in": text.fade_in,
                "fade_out": text.fade_out,
            })

    return results


def _hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Convert hex color string to RGBA tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    elif len(h) == 8:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    return (255, 255, 255, 255)
