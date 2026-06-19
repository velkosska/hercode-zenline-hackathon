from __future__ import annotations

import json
import os
import re
from typing import Any

from anthropic import Anthropic


def get_claude_api_key() -> str:
    """Read Claude API key from CLAUDE_API_KEY or ANTHROPIC_API_KEY."""
    return (
        os.getenv("CLAUDE_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
    )


def get_claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip() or "claude-sonnet-4-6"


def _parse_json_list(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, dict)]
        if isinstance(parsed, dict) and "trends" in parsed:
            trends = parsed["trends"]
            if isinstance(trends, list):
                return [p for p in trends if isinstance(p, dict)]
    except json.JSONDecodeError:
        pass
    return []


def synthesize_bloom_trends(
    discovery_snippets: list[dict[str, Any]],
    agent_rows: list[dict[str, Any]],
    seed_keywords: list[str],
    max_picks: int = 3,
) -> list[dict[str, Any]]:
    """
    Use Claude to propose net-new bloom trends from Tavily discovery + agent synthesis.
    Returns empty list if no API key or on failure.
    """
    api_key = get_claude_api_key()
    if not api_key:
        return []

    seed_list = ", ".join(seed_keywords)
    snippet_lines = []
    for hit in discovery_snippets[:12]:
        snippet_lines.append(
            f"- {hit.get('title', '')}: {hit.get('content', '')[:200]} ({hit.get('url', '')})"
        )
    agent_lines = []
    for row in agent_rows[:8]:
        agent_lines.append(
            f"- {row.get('keyword', '')}: {row.get('evidence_summary', row.get('opportunity', ''))[:180]}"
        )

    prompt = f"""Given these outdoor retail signals for Switzerland/DACH, propose up to {max_picks} trends likely to bloom in CH within 6–18 months.

Do NOT repeat these seed keywords already tracked: {seed_list}

Tavily discovery snippets:
{chr(10).join(snippet_lines) or '(none)'}

Agent synthesis rows (including dark horses):
{chr(10).join(agent_lines) or '(none)'}

Return ONLY a JSON array (no markdown). Each object must have:
- keyword (string)
- opportunity (string)
- bloom_rationale (string)
- timing_window (string, e.g. "12-18 months")
- recommended_action (string)
- confidence ("high" | "medium" | "low")

Only propose trends with evidence in the snippets or agent rows above."""

    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=get_claude_model(),
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        return _parse_json_list(text)[:max_picks]
    except Exception:
        return []
