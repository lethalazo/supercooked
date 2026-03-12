"""Content strategy recommendations via Claude API (Anthropic).

Analyzes a being's performance history, memory, and current trends
to recommend content strategy adjustments.
"""

from __future__ import annotations

import json
from typing import Any

from supercooked.config import CLAUDE_MODEL, get_anthropic_client
from supercooked.identity.action_log import log_action
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.identity.memory import load_memory
from supercooked.identity.state import _load_strategy_log
from supercooked.intel.analytics import get_platform_stats, get_top_content


STRATEGY_SYSTEM_TEMPLATE = """You are a content strategy advisor for {name}, a digital being.

IDENTITY:
{identity_summary}

VOICE:
{voice_md}

CURRENT STRATEGY:
{strategy_history}

PERFORMANCE DATA:
{performance_summary}

MEMORY/LEARNINGS:
{memory_summary}

Analyze the data and provide actionable strategy recommendations.
Return your analysis as JSON with this exact format:
{{
  "overall_assessment": "1-2 sentence summary of current performance",
  "recommendations": [
    {{
      "area": "content|posting_schedule|engagement|platform|growth",
      "recommendation": "Specific actionable recommendation",
      "reasoning": "Why this would help",
      "priority": "high|medium|low"
    }}
  ],
  "content_themes_to_explore": ["theme1", "theme2"],
  "content_themes_to_avoid": ["theme1"],
  "optimal_posting_times": {{
    "platform_name": "suggested schedule description"
  }}
}}

Return ONLY the JSON. No other text.
"""


async def recommend_strategy(
    slug: str,
) -> dict[str, Any]:
    """Generate content strategy recommendations using Claude API.

    Analyzes the being's performance history, memory, strategy log,
    and identity to provide data-driven recommendations.

    Args:
        slug: Identity slug.

    Returns:
        Dict containing strategy recommendations with keys:
            overall_assessment, recommendations, content_themes_to_explore,
            content_themes_to_avoid, optimal_posting_times.

    Raises:
        RuntimeError: If the Anthropic API key is not configured or Claude
                      returns invalid JSON.
    """
    identity = load_identity(slug)
    voice_md = get_voice_md(slug)
    memory = load_memory(slug)

    # Build identity summary
    identity_summary_lines = [
        f"Name: {identity.being.name}",
        f"Tagline: {identity.being.tagline}",
        f"Archetype: {identity.persona.archetype}",
        f"Tone: {identity.persona.tone}",
    ]
    identity_summary = "\n".join(identity_summary_lines)

    # Build performance summary
    top_content = get_top_content(slug, limit=10, sort_by="views")
    platform_stats = get_platform_stats(slug)

    perf_lines = ["## Top Content:"]
    for content in top_content:
        perf_lines.append(
            f"- {content.title} ({content.platform}): "
            f"{content.views} views, {content.likes} likes, "
            f"{content.engagement_rate:.2%} engagement"
        )

    perf_lines.append("\n## Platform Stats:")
    for ps in platform_stats:
        perf_lines.append(
            f"- {ps.platform}: {ps.followers} followers, "
            f"{ps.total_views} total views, "
            f"{ps.engagement_rate:.2%} avg engagement"
        )

    performance_summary = "\n".join(perf_lines) if top_content or platform_stats else "No performance data yet."

    # Build memory summary
    memory_lines = []
    for learning in memory.learnings[-30:]:
        memory_lines.append(
            f"- [{learning.category}] {learning.insight} (confidence: {learning.confidence})"
        )
    memory_summary = "\n".join(memory_lines) if memory_lines else "No learnings yet."

    # Build strategy history
    strategy_log = _load_strategy_log(slug)
    strategy_lines = []
    for decision in strategy_log.decisions[-10:]:
        strategy_lines.append(
            f"- {decision.decision} (reason: {decision.reasoning})"
        )
        if decision.outcome:
            strategy_lines.append(f"  Outcome: {decision.outcome}")
    strategy_history = "\n".join(strategy_lines) if strategy_lines else "No previous strategy decisions."

    system_prompt = STRATEGY_SYSTEM_TEMPLATE.format(
        name=identity.being.name,
        identity_summary=identity_summary,
        voice_md=voice_md,
        strategy_history=strategy_history,
        performance_summary=performance_summary,
        memory_summary=memory_summary,
    )

    client = get_anthropic_client()
    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": "Analyze my content performance and provide strategy recommendations.",
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Parse JSON response
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start == -1 or end == 0:
            raise RuntimeError(
                f"Claude returned non-JSON response for strategy:\n{raw_text[:500]}"
            )
        try:
            result = json.loads(raw_text[start:end])
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Failed to parse strategy from Claude response:\n{raw_text[:500]}"
            )

    log_action(
        slug,
        action="recommend_strategy",
        platform="claude",
        details={
            "model": CLAUDE_MODEL,
            "recommendation_count": len(result.get("recommendations", [])),
        },
        result=f"Generated strategy with {len(result.get('recommendations', []))} recommendations",
    )

    return result
