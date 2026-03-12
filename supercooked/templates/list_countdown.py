"""List Countdown template — 'Top N things...' (Shorts)."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class ListCountdownTemplate(BaseTemplate):
    """Numbered countdown list delivered as a short-form video.

    Format: short-form vertical video (40-45s).
    Style: Energetic countdown from N to 1, with brief commentary on each item.
    """

    name = "list_countdown"
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
                "You generate numbered countdown list scripts for short-form vertical "
                "video. Each script should be 40-45 seconds when spoken aloud."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a countdown list short-form video script.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- Start with a hook line to keep viewers watching\n"
                        "- List 5 items counting down from 5 to 1\n"
                        "- Each item gets 1-2 sentences of punchy commentary\n"
                        "- Number 1 should be the most surprising or impactful\n"
                        "- End with a quick outro or call to action\n"
                        "- 40-45 seconds total when read aloud\n"
                        "- Write ONLY the spoken script, no stage directions\n\n"
                        "Also provide:\n"
                        "- 5 image descriptions (one per list item) for background visuals\n"
                        "- A short caption (under 150 chars)\n"
                        "- 5 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SCRIPT:\n<the script>\n\n"
                        "IMAGES:\n<image 1 description>\n<image 2 description>\n"
                        "<image 3 description>\n<image 4 description>\n<image 5 description>\n\n"
                        "CAPTION:\n<caption text>\n\n"
                        "HASHTAGS:\n<comma-separated hashtags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        image_prompts = [
            line.strip()
            for line in sections.get("IMAGES", "").splitlines()
            if line.strip()
        ]

        hashtags = [
            tag.strip().lstrip("#")
            for tag in sections.get("HASHTAGS", "").split(",")
            if tag.strip()
        ]

        return ContentSpec(
            title=idea_title,
            script=sections.get("SCRIPT", "").strip(),
            duration_seconds=42,
            resolution="1080x1920",
            voice_prompt=f"Speak as {being_name}. Upbeat, energetic delivery. Emphasize each number.",
            image_prompts=image_prompts,
            video_prompt=f"Countdown list video with numbered text overlays. Speaker: {being_name}.",
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
