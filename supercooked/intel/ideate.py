"""Content idea generation via Claude API (Anthropic).

Uses the being's identity, memory, and voice to brainstorm
content ideas that fit the being's brand and strategy.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from supercooked.config import CLAUDE_MODEL, get_anthropic_client
from supercooked.identity.action_log import log_action
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.identity.memory import load_memory
from supercooked.identity.schemas import ContentIdea, IdeaStatus


IDEATION_SYSTEM_TEMPLATE = """You are the creative director for {name}, a digital being.

{voice_md}

CONTENT STRATEGY:
{strategy_info}

RECENT MEMORY/LEARNINGS:
{memory_summary}

Your job is to brainstorm content ideas that:
1. Fit {name}'s voice and personality perfectly
2. Are relevant to current trends and audience interests
3. Are feasible to produce (short-form video, images, tweets, threads)
4. Build on past successes and avoid repeated failures

Return your ideas as a JSON array with this exact format:
[
  {{
    "title": "Short catchy title",
    "concept": "2-3 sentence description of the content",
    "template": "video_short|image_post|tweet|thread|carousel",
    "tags": ["tag1", "tag2"],
    "content_types": ["image", "tweet"]
  }}
]

Valid content_types: image, video, post, selfie, tweet, thread, story, audio, music, thumbnail
- Choose types that match the content format (e.g. a video_short needs ["video", "thumbnail"], a tweet needs ["tweet"], an image_post needs ["image", "post"])
- Each idea should have at least one content_type

Return ONLY the JSON array. No other text.
"""


async def generate_ideas(
    slug: str,
    count: int = 5,
    focus: str | None = None,
) -> list[ContentIdea]:
    """Generate content ideas using Claude API.

    Loads the being's identity, memory, and voice to generate
    contextually relevant content ideas.

    Args:
        slug: Identity slug.
        count: Number of ideas to generate. Defaults to 5.
        focus: Optional focus area or topic to center ideas around.

    Returns:
        List of ContentIdea objects ready to be saved to the ideas file.

    Raises:
        RuntimeError: If the Anthropic API key is not configured or Claude returns invalid JSON.
    """
    identity = load_identity(slug)
    voice_md = get_voice_md(slug)
    memory = load_memory(slug)

    # Build strategy summary
    strategy = identity.content_strategy
    strategy_lines = []
    if strategy.posting_frequency.shorts:
        strategy_lines.append(f"Shorts frequency: {strategy.posting_frequency.shorts}")
    if strategy.posting_frequency.images:
        strategy_lines.append(f"Image frequency: {strategy.posting_frequency.images}")
    if strategy.posting_frequency.tweets:
        strategy_lines.append(f"Tweet frequency: {strategy.posting_frequency.tweets}")
    for series in strategy.series:
        strategy_lines.append(f"Series: {series.name} ({series.format}, {series.frequency})")
    strategy_info = "\n".join(strategy_lines) if strategy_lines else "No specific strategy set."

    # Build memory summary
    memory_lines = []
    for learning in memory.learnings[-20:]:
        memory_lines.append(
            f"- [{learning.category}] {learning.insight} (confidence: {learning.confidence})"
        )
    memory_summary = "\n".join(memory_lines) if memory_lines else "No learnings recorded yet."

    system_prompt = IDEATION_SYSTEM_TEMPLATE.format(
        name=identity.being.name,
        voice_md=voice_md,
        strategy_info=strategy_info,
        memory_summary=memory_summary,
    )

    user_prompt = f"Generate exactly {count} content ideas"
    if focus:
        user_prompt += f" focused on: {focus}"
    user_prompt += "."

    client = get_anthropic_client()
    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Parse JSON response
    try:
        ideas_data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON array from the response
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start == -1 or end == 0:
            raise RuntimeError(
                f"Claude returned non-JSON response for idea generation:\n{raw_text[:500]}"
            )
        try:
            ideas_data = json.loads(raw_text[start:end])
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Failed to parse ideas from Claude response:\n{raw_text[:500]}"
            )

    # Convert to ContentIdea objects
    ideas: list[ContentIdea] = []
    for item in ideas_data:
        idea = ContentIdea(
            id=uuid.uuid4().hex[:8],
            title=item.get("title", "Untitled"),
            concept=item.get("concept", ""),
            template=item.get("template", ""),
            status=IdeaStatus.BACKLOG,
            created=datetime.now(),
            tags=item.get("tags", []),
            content_types=item.get("content_types", []),
        )
        ideas.append(idea)

    log_action(
        slug,
        action="generate_ideas",
        platform="claude",
        details={
            "count": count,
            "focus": focus,
            "generated": len(ideas),
            "model": CLAUDE_MODEL,
        },
        result=f"Generated {len(ideas)} content ideas",
    )

    return ideas
