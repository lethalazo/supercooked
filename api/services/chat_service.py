"""Claude API chat in being's persona."""

from __future__ import annotations

from supercooked.config import CLAUDE_MODEL, get_anthropic_client
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.identity.state import create_session, end_session


class ChatService:
    def __init__(self, slug: str):
        self.slug = slug
        self.session_id: str | None = None
        self.messages: list[dict] = []
        self.system_prompt: str = ""

    async def initialize(self):
        """Load being's identity and create a session."""
        identity = load_identity(self.slug)
        voice_md = get_voice_md(self.slug)

        self.system_prompt = (
            f"You are {identity.being.name}. {identity.being.tagline}\n\n"
            f"PERSONALITY AND VOICE GUIDE:\n{voice_md}\n\n"
            f"Stay in character at all times. You ARE this being. "
            f"Respond as {identity.being.name} would - with the tone, perspective, "
            f"and voice traits defined above. Never break character."
        )

        self.session_id = create_session(self.slug)
        self.messages = []

    async def respond(self, user_message: str) -> str:
        """Generate a response as the being using Claude Opus 6."""
        client = get_anthropic_client()

        self.messages.append({"role": "user", "content": user_message})

        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.messages,
        )

        assistant_message = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    async def end_session(self):
        """End the chat session and save summary."""
        if self.session_id:
            actions = [m["content"][:100] for m in self.messages if m["role"] == "user"]
            end_session(
                self.slug,
                self.session_id,
                summary=f"Chat session with {len(self.messages)} messages",
                actions_taken=actions,
            )
