"""Livestream template - Twitch stream blueprint."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class LivestreamTemplate(BaseTemplate):
    """Twitch livestream blueprint.

    Format: livestream plan with talking points, segments, and chat guidelines.
    Style: Interactive stream with audience participation and structured segments.
    """

    name = "livestream"
    format_type = "livestream"

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
                "You generate Twitch livestream blueprints. Each stream plan includes "
                "structured segments, talking points, audience interaction prompts, "
                "and chat response guidelines."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create a livestream plan.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- Stream duration: 60-90 minutes\n"
                        "- 4-6 segments with clear transitions\n"
                        "- Each segment: topic, talking points, audience interaction\n"
                        "- Opening bit to welcome viewers and set the vibe\n"
                        "- At least 2 chat interaction moments (polls, Q&A, etc.)\n"
                        "- Closing segment with recap and raid/host plan\n\n"
                        "Also provide:\n"
                        "- Stream title (under 100 chars)\n"
                        "- Category/game suggestion\n"
                        "- 3 chat response guidelines (how to handle common chat messages)\n"
                        "- A thumbnail image description\n"
                        "- 5 relevant tags\n\n"
                        "Format your response EXACTLY as:\n"
                        "STREAM_TITLE:\n<stream title>\n\n"
                        "CATEGORY:\n<category or game>\n\n"
                        "SEGMENTS:\n<full segment breakdown>\n\n"
                        "CHAT_GUIDELINES:\n<3 chat response guidelines>\n\n"
                        "THUMBNAIL:\n<thumbnail image description>\n\n"
                        "TAGS:\n<comma-separated tags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        tags = [
            tag.strip().lstrip("#")
            for tag in sections.get("TAGS", "").split(",")
            if tag.strip()
        ]

        stream_title = sections.get("STREAM_TITLE", idea_title).strip()
        segments = sections.get("SEGMENTS", "").strip()
        chat_guidelines = sections.get("CHAT_GUIDELINES", "").strip()
        category = sections.get("CATEGORY", "").strip()

        # Combine segments and chat guidelines into the script
        full_script = (
            f"CATEGORY: {category}\n\n"
            f"SEGMENTS:\n{segments}\n\n"
            f"CHAT RESPONSE GUIDELINES:\n{chat_guidelines}"
        )

        return ContentSpec(
            title=stream_title,
            script=full_script,
            duration_seconds=5400,  # 90 minutes
            resolution="1920x1080",
            voice_prompt=(
                f"Speak as {being_name}. Energetic streamer persona. "
                "Interactive, reacts to chat, keeps the energy up."
            ),
            image_prompts=[sections.get("THUMBNAIL", "").strip()],
            video_prompt=f"Twitch livestream. Streamer: {being_name}. Category: {category}.",
            caption=stream_title,
            hashtags=tags,
            platform_targets=["twitch"],
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
