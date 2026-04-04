"""Hot Take template - bold text + reaction (Shorts)."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class HotTakeTemplate(BaseTemplate):
    """Bold, punchy hot take delivered straight to camera.

    Format: short-form vertical video (30-40s).
    Style: Direct statement, brief justification, mic-drop closer.
    """

    name = "hot_take"
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
            max_tokens=1024,
            system=(
                f"You are the content brain for a digital being named {being_name}.\n\n"
                f"Voice and personality guide:\n{voice_md}\n\n"
                "You generate punchy, bold hot take scripts for short-form vertical "
                "video. Each script should be 30-40 seconds when spoken aloud."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a hot take short-form video script.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- Open with a bold, attention-grabbing statement\n"
                        "- Give ONE compelling reason or example\n"
                        "- End with a mic-drop line or call to action\n"
                        "- 30-40 seconds when read aloud\n"
                        "- Write ONLY the spoken script, no stage directions\n\n"
                        "Also provide:\n"
                        "- A single background image description for the video\n"
                        "- A short caption (under 150 chars)\n"
                        "- 5 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SCRIPT:\n<the script>\n\n"
                        "IMAGE:\n<image description>\n\n"
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

        return ContentSpec(
            title=idea_title,
            script=sections.get("SCRIPT", "").strip(),
            duration_seconds=35,
            resolution="1080x1920",
            voice_prompt=f"Speak as {being_name}. Confident, bold delivery with emphasis on the opening statement.",
            image_prompts=[sections.get("IMAGE", "").strip()],
            video_prompt=f"Bold text overlay short-form video. Hot take style. Speaker: {being_name}.",
            caption=sections.get("CAPTION", "").strip(),
            hashtags=hashtags,
            platform_targets=["youtube_shorts", "tiktok", "instagram"],
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
