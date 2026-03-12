"""Vlog template — AI 'vlog' with selfies + narration."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class VlogTemplate(BaseTemplate):
    """AI vlog with multiple scene descriptions and narration.

    Format: short-form vertical video (45-60s).
    Style: Day-in-the-life or experience vlog with selfie-style shots
    across multiple scenes / locations.
    """

    name = "vlog"
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
                "You generate vlog-style scripts with multiple scenes. The being "
                "narrates their day or experience with selfie-style shots in different "
                "locations. Each script should be 45-60 seconds when spoken aloud."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a vlog-style narration script.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- 4-6 scenes, each with a different location/setting\n"
                        "- Natural, casual narration as if holding a phone\n"
                        "- Each scene is 1-3 sentences of narration\n"
                        "- Build a mini narrative arc across scenes\n"
                        "- 45-60 seconds total when read aloud\n"
                        "- Write ONLY the spoken narration, no stage directions\n\n"
                        "Also provide:\n"
                        "- A selfie-style image description for EACH scene\n"
                        "- A short caption (under 150 chars)\n"
                        "- 5 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "SCRIPT:\n<the full narration>\n\n"
                        "SCENES:\n<scene 1 image description>\n---\n"
                        "<scene 2 image description>\n---\n"
                        "<scene 3 image description>\n---\n"
                        "(continue for each scene)\n\n"
                        "CAPTION:\n<caption text>\n\n"
                        "HASHTAGS:\n<comma-separated hashtags>"
                    ),
                }
            ],
        )

        response_text = message.content[0].text
        sections = _parse_sections(response_text)

        scene_descriptions = [
            scene.strip()
            for scene in sections.get("SCENES", "").split("---")
            if scene.strip()
        ]

        hashtags = [
            tag.strip().lstrip("#")
            for tag in sections.get("HASHTAGS", "").split(",")
            if tag.strip()
        ]

        return ContentSpec(
            title=idea_title,
            script=sections.get("SCRIPT", "").strip(),
            duration_seconds=52,
            resolution="1080x1920",
            voice_prompt=(
                f"Speak as {being_name}. Casual, vlog-style delivery. "
                "Sounds like you're narrating into your phone camera."
            ),
            image_prompts=scene_descriptions,
            video_prompt=(
                f"Vlog-style selfie video across {len(scene_descriptions)} scenes. "
                f"Speaker: {being_name}. Handheld camera feel."
            ),
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
