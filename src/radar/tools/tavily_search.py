from __future__ import annotations

import os
from typing import Any

import httpx

TAVILY_URL = "https://api.tavily.com/search"


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Tavily web search. Returns empty list if no API key."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
    except Exception:
        return []


def search_site(domain: str, keyword: str, max_results: int = 3) -> list[dict[str, Any]]:
    return search_web(f"site:{domain} {keyword}", max_results=max_results)
