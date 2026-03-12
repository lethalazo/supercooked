"""Longform template — YouTube long-form video (5-20 min)."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class LongformTemplate(BaseTemplate):
    """YouTube long-form video with full scripted segments.

    Format: horizontal video (1920x1080), 5-20 minutes.
    Style: Fully scripted video with intro, multiple segments,
    and outro. Includes B-roll descriptions for each segment.
    """

    name = "longform"
    format_type = "longform"

    async def generate_spec(
        self, slug: str, idea_title: str, idea_concept: str
    ) -> ContentSpec:
        identity = load_identity(slug)
        voice_md = get_voice_md(slug)
        being_name = identity.being.name

        client = get_anthropic_client()

        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=(
                f"You are the content brain for a digital being named {being_name}.\n\n"
                f"Voice and personality guide:\n{voice_md}\n\n"
                "You generate full scripts for long-form YouTube videos (5-20 minutes). "
                "Each script has a structured format with intro, multiple content "
                "segments, and an outro. Include B-roll and visual descriptions."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a full YouTube video script.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- Target length: 8-12 minutes when read aloud\n"
                        "- INTRO (30-60s): Hook, introduce yourself, preview the topic\n"
                        "- 4-6 SEGMENTS: Each with a clear heading and 1-2 minutes of script\n"
                        "- OUTRO (30s): Recap key points, CTA (like/subscribe/comment)\n"
                        "- Write the FULL spoken script (not bullet points)\n"
                        "- Include natural transitions between segments\n\n"
                        "Also provide:\n"
                        "- A thumbnail image description\n"
                        "- A B-roll / visual description for each segment\n"
                        "- A YouTube description (150-300 words)\n"
                        "- 10 relevant tags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SCRIPT:\n<the full video script with segment headers>\n\n"
                        "THUMBNAIL:\n<thumbnail image description>\n\n"
                        "VISUALS:\n<segment 1 visual>\n---\n"
                        "<segment 2 visual>\n---\n"
                        "(continue for each segment)\n\n"
                        "DESCRIPTION:\n<youtube description>\n\n"
                        "TAGS:\n<comma-separated tags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        # Parse visual descriptions per segment
        visuals = [
            v.strip()
            for v in sections.get("VISUALS", "").split("---")
            if v.strip()
        ]

        # Thumbnail + segment visuals
        thumbnail = sections.get("THUMBNAIL", "").strip()
        image_prompts = [thumbnail] + visuals if thumbnail else visuals

        tags = [
            tag.strip().lstrip("#")
            for tag in sections.get("TAGS", "").split(",")
            if tag.strip()
        ]

        description = sections.get("DESCRIPTION", "").strip()

        return ContentSpec(
            title=idea_title,
            script=sections.get("SCRIPT", "").strip(),
            duration_seconds=600,  # 10 minutes target
            resolution="1920x1080",
            voice_prompt=(
                f"Speak as {being_name}. YouTube presenter style. Clear, "
                "engaging delivery with natural pacing and emphasis on key points."
            ),
            image_prompts=image_prompts,
            video_prompt=(
                f"Long-form YouTube video. Presenter: {being_name}. "
                f"Mix of talking head and B-roll across {len(visuals)} segments."
            ),
            caption=description,
            hashtags=tags,
            platform_targets=["youtube"],
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
