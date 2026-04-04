"""Story template - IG/X story format."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class StoryTemplate(BaseTemplate):
    """Instagram / X story format.

    Format: vertical image with overlay text (1080x1920).
    Style: Single striking image with a short text overlay and optional poll/question.
    """

    name = "story"
    format_type = "story"

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
                "You generate Instagram/X story content. Stories are vertical images "
                "with short overlay text. They should feel spontaneous and personal."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create an IG/X story.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- A short overlay text (max 30 words) - what appears ON the story\n"
                        "- The text should feel casual, in-the-moment\n"
                        "- Include a question or poll prompt if it fits naturally\n"
                        "- Keep it shareable and engaging\n\n"
                        "Also provide:\n"
                        "- A detailed background image description (vertical 9:16)\n"
                        "- A swipe-up caption or CTA if appropriate\n"
                        "- 3 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "OVERLAY:\n<the overlay text>\n\n"
                        "IMAGE:\n<background image description>\n\n"
                        "CAPTION:\n<swipe-up caption or CTA>\n\n"
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

        overlay_text = sections.get("OVERLAY", "").strip()

        return ContentSpec(
            title=idea_title,
            script=overlay_text,
            duration_seconds=5,
            resolution="1080x1920",
            voice_prompt="",
            image_prompts=[sections.get("IMAGE", "").strip()],
            video_prompt=f"Story format: vertical image with text overlay. Speaker: {being_name}.",
            caption=sections.get("CAPTION", "").strip(),
            hashtags=hashtags,
            platform_targets=["instagram", "x"],
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
