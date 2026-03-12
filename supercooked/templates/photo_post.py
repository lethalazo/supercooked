"""Photo Post template — single image + caption (IG/X)."""

from __future__ import annotations

from supercooked.config import get_anthropic_client, CLAUDE_MODEL
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.templates.base import BaseTemplate, ContentSpec


class PhotoPostTemplate(BaseTemplate):
    """Single image post with caption.

    Format: square image (1080x1080) with accompanying caption.
    Style: Polished single photo post for Instagram or X feed.
    """

    name = "photo_post"
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
            max_tokens=1024,
            system=(
                f"You are the content brain for a digital being named {being_name}.\n\n"
                f"Voice and personality guide:\n{voice_md}\n\n"
                "You generate single image posts for Instagram and X. Each post "
                "needs a compelling image and an engaging caption."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create a photo post.\n\n"
                        f"Title: {idea_title}\n"
                        f"Concept: {idea_concept}\n\n"
                        "Requirements:\n"
                        "- A detailed image prompt for a striking square (1:1) photo\n"
                        "- An engaging caption (50-200 words)\n"
                        "- Caption should feel authentic and personal\n"
                        "- Include a question or CTA to drive engagement\n\n"
                        "Also provide:\n"
                        "- 10 relevant hashtags\n\n"
                        "Format your response EXACTLY as:\n"
                        "IMAGE:\n<detailed image description for generation>\n\n"
                        "CAPTION:\n<the post caption>\n\n"
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
            script="",
            duration_seconds=0,
            resolution="1080x1080",
            voice_prompt="",
            image_prompts=[sections.get("IMAGE", "").strip()],
            video_prompt="",
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
