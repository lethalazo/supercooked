"""Carousel template - multi-image post (IG carousel)."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class CarouselTemplate(BaseTemplate):
    """Multi-image carousel post for Instagram.

    Format: 4-10 square images (1080x1080) with unified caption.
    Style: Educational breakdown, storytelling, or listicle across slides.
    """

    name = "carousel"
    format_type = "image"

    async def generate_spec(
        self, slug: str, idea_title: str, idea_concept: str
    ) -> ContentSpec:
        identity = load_identity(slug)
        voice_md = get_voice_md(slug)
        being_name = identity.being.name

        client = get_anthropic_client()

        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=(
                f"You are the content brain for a digital being named {being_name}.\n\n"
                f"Voice and personality guide:\n{voice_md}\n\n"
                "You generate Instagram carousel posts. Each carousel has 5-8 slides "
                "that tell a story or teach something. Each slide needs a distinct image "
                "and text overlay."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create an Instagram carousel post.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- 6 slides, each with a unique image and text overlay\n"
                        "- Slide 1: eye-catching cover with the title\n"
                        "- Slides 2-5: each makes one key point with supporting visual\n"
                        "- Slide 6: summary/CTA slide\n"
                        "- Each slide's text overlay should be 5-15 words\n"
                        "- All images should be square (1:1) composition\n\n"
                        "Also provide:\n"
                        "- An overall caption for the post (50-200 words)\n"
                        "- 15 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SLIDES:\n"
                        "1. [overlay text] | [image description]\n"
                        "2. [overlay text] | [image description]\n"
                        "3. [overlay text] | [image description]\n"
                        "4. [overlay text] | [image description]\n"
                        "5. [overlay text] | [image description]\n"
                        "6. [overlay text] | [image description]\n\n"
                        "CAPTION:\n<the post caption>\n\n"
                        "HASHTAGS:\n<comma-separated hashtags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        # Parse slide image descriptions from the SLIDES section
        image_prompts: list[str] = []
        slide_text_parts: list[str] = []
        for line in sections.get("SLIDES", "").splitlines():
            line = line.strip()
            if not line:
                continue
            # Expected format: "N. [overlay] | [image desc]"
            if "|" in line:
                parts = line.split("|", 1)
                overlay = parts[0].strip().lstrip("0123456789.").strip()
                image_desc = parts[1].strip()
                slide_text_parts.append(overlay)
                image_prompts.append(image_desc)
            elif line:
                image_prompts.append(line)

        hashtags = [
            tag.strip().lstrip("#")
            for tag in sections.get("HASHTAGS", "").split(",")
            if tag.strip()
        ]

        # Combine slide overlay texts into the script field
        slides_script = "\n".join(
            f"Slide {i + 1}: {text}" for i, text in enumerate(slide_text_parts)
        )

        return ContentSpec(
            title=idea_title,
            script=slides_script,
            duration_seconds=0,
            resolution="1080x1080",
            voice_prompt="",
            image_prompts=image_prompts,
            video_prompt="",
            caption=sections.get("CAPTION", "").strip(),
            hashtags=hashtags,
            platform_targets=["instagram"],
        )


def _parse_sections(text: str) -> dict[str, str]:
    """Parse a response into named sections."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1].upper() == stripped[:-1] and len(stripped) > 1:
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = stripped[:-1]
            current_lines = []
        else:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
