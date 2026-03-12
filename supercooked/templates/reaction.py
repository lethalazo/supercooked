"""Reaction template — PiP reaction to another video."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class ReactionTemplate(BaseTemplate):
    """Picture-in-picture reaction video.

    Format: short-form vertical video (30-60s).
    Style: Being reacts to source content with commentary overlaid.
    Includes a reference to the source video being reacted to.
    """

    name = "reaction"
    format_type = "short"

    async def generate_spec(
        self, slug: str, idea_title: str, idea_concept: str
    ) -> ContentSpec:
        identity = load_identity(slug)
        voice_md = get_voice_md(slug)
        being_name = identity.being.name

        client = get_anthropic_client()

        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=(
                f"You are the content brain for a digital being named {being_name}.\n\n"
                f"Voice and personality guide:\n{voice_md}\n\n"
                "You generate reaction commentary scripts for PiP (picture-in-picture) "
                "reaction videos. The being watches and reacts to source content. "
                "Each script should be 30-60 seconds when spoken aloud."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a reaction video commentary script.\n\n"
                        f"Title: {idea_title}\n"
                        f"Source content / concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- Brief intro setting up what you're about to watch\n"
                        "- 3-4 reaction beats (pause points with commentary)\n"
                        "- Each beat: describe the moment, then give your reaction\n"
                        "- End with an overall take or rating\n"
                        "- 30-60 seconds of spoken commentary\n"
                        "- Write ONLY the spoken script, no stage directions\n\n"
                        "Also provide:\n"
                        "- A description of the source video content being reacted to\n"
                        "- The being's facial expression / appearance during reactions\n"
                        "- A short caption (under 150 chars)\n"
                        "- 5 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SCRIPT:\n<the reaction commentary>\n\n"
                        "SOURCE:\n<description of source content>\n\n"
                        "APPEARANCE:\n<being's look during reactions>\n\n"
                        "CAPTION:\n<caption text>\n\n"
                        "HASHTAGS:\n<comma-separated hashtags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        hashtags = [
            tag.strip().lstrip("#")
            for tag in sections.get("HASHTAGS", "").split(",")
            if tag.strip()
        ]

        source_desc = sections.get("SOURCE", "").strip()
        appearance = sections.get("APPEARANCE", "").strip()

        return ContentSpec(
            title=idea_title,
            script=sections.get("SCRIPT", "").strip(),
            duration_seconds=45,
            resolution="1080x1920",
            voice_prompt=(
                f"Speak as {being_name}. Animated, expressive reactions. "
                "Shift between surprise, amusement, and thoughtful commentary."
            ),
            image_prompts=[
                f"PiP reaction cam of {being_name}: {appearance}",
                f"Source content: {source_desc}",
            ],
            video_prompt=(
                f"Picture-in-picture reaction video. Main: source content. "
                f"PiP overlay: {being_name} reacting. Source: {source_desc}"
            ),
            caption=sections.get("CAPTION", "").strip(),
            hashtags=hashtags,
            platform_targets=["youtube_shorts", "tiktok"],
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
