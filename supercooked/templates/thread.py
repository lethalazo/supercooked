"""Thread template - X thread format."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class ThreadTemplate(BaseTemplate):
    """X (Twitter) thread format.

    Format: 3-8 connected tweets forming a cohesive narrative.
    Style: Thought leadership, storytelling, or educational breakdown.
    """

    name = "thread"
    format_type = "thread"

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
                "You generate X (Twitter) threads. Each tweet must be under 280 "
                "characters. The thread should tell a cohesive story or build an "
                "argument across 3-8 connected tweets."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write an X thread.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- 5-7 tweets, each UNDER 280 characters\n"
                        "- First tweet is a hook that makes people want to read on\n"
                        "- Build a logical progression or narrative\n"
                        "- Include at least one tweet with a concrete example or data\n"
                        "- Last tweet should be a strong conclusion + CTA\n"
                        "- Number each tweet (1/, 2/, etc.)\n"
                        "- Each tweet should stand alone but connect to the thread\n\n"
                        "Also provide:\n"
                        "- A header image description for the first tweet\n"
                        "- 5 relevant hashtags (for the last tweet)\n\n"
                        "Format your response EXACTLY as:\n"
                        "THREAD:\n<all tweets, separated by blank lines>\n\n"
                        "IMAGE:\n<header image description>\n\n"
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

        thread_text = sections.get("THREAD", "").strip()

        return ContentSpec(
            title=idea_title,
            script=thread_text,
            duration_seconds=0,
            resolution="",
            voice_prompt="",
            image_prompts=[sections.get("IMAGE", "").strip()],
            video_prompt="",
            caption=thread_text,
            hashtags=hashtags,
            platform_targets=["x"],
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
