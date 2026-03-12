"""Reply generation via Claude API (Anthropic).

Uses the identity's VOICE.md as a system prompt to generate
in-character replies to audience comments across platforms.
"""

from __future__ import annotations

from supercooked.config import CLAUDE_MODEL, get_anthropic_client
from supercooked.identity.action_log import log_action
from supercooked.identity.manager import get_voice_md, load_identity


REPLY_SYSTEM_TEMPLATE = """You are {name}, a digital being. You are replying to a comment on {platform}.

{voice_md}

RULES:
- Stay completely in character as {name}.
- Match the platform's tone and conventions ({platform}).
- Keep replies concise and engaging.
- Never break character or reveal you are an AI.
- If the comment is hostile or inappropriate, respond with grace or humor, staying in character.
"""


async def generate_reply(
    slug: str,
    comment_text: str,
    platform: str,
    context: str = "",
    max_tokens: int = 280,
) -> str:
    """Generate an in-character reply to a comment using Claude API.

    Loads the being's VOICE.md and identity to construct a system prompt,
    then uses Claude to generate a reply that matches the being's personality.

    Args:
        slug: Identity slug.
        comment_text: The comment text to reply to.
        platform: Platform where the comment was made (e.g. "x", "youtube", "instagram").
        context: Optional additional context (e.g. the original post text).
        max_tokens: Maximum tokens in the reply. Defaults to 280 (tweet-length).

    Returns:
        The generated reply text.

    Raises:
        RuntimeError: If the Anthropic API key is not configured.
    """
    identity = load_identity(slug)
    voice_md = get_voice_md(slug)

    system_prompt = REPLY_SYSTEM_TEMPLATE.format(
        name=identity.being.name,
        platform=platform,
        voice_md=voice_md,
    )

    user_message = f"Reply to this comment on {platform}:\n\n\"{comment_text}\""
    if context:
        user_message = f"Context (the original post): {context}\n\n{user_message}"

    client = get_anthropic_client()
    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    reply_text = response.content[0].text

    log_action(
        slug,
        action="generate_reply",
        platform=platform,
        details={
            "comment": comment_text[:200],
            "reply": reply_text[:200],
            "model": CLAUDE_MODEL,
        },
        result=f"Generated reply ({len(reply_text)} chars)",
    )

    return reply_text
