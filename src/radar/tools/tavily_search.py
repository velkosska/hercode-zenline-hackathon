from __future__ import annotations

import os
from typing import Any

import httpx

TAVILY_URL = "https://api.tavily.com/search"

MARKETPLACE_DOMAINS = ["galaxus.ch", "decathlon.ch", "ochsnersport.ch", "transa.ch"]


def search_web(
    query: str,
    max_results: int = 5,
    *,
    topic: str | None = None,
    time_range: str | None = None,
    include_domains: list[str] | None = None,
    search_depth: str = "basic",
) -> list[dict[str, Any]]:
    """Tavily web search. Returns empty list if no API key."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": False,
    }
    if topic:
        payload["topic"] = topic
    if time_range:
        payload["time_range"] = time_range
    if include_domains:
        payload["include_domains"] = include_domains

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


def search_news(keyword: str, market: str = "CH", max_results: int = 5) -> list[dict[str, Any]]:
    """Trade press / news corroboration for a keyword."""
    query = f"{keyword} outdoor trend {market} Switzerland"
    return search_web(query, max_results=max_results, topic="news", time_range="month")


def search_marketplace(
    keyword: str,
    domains: list[str] | None = None,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Marketplace / e-com listing presence via domain-restricted search."""
    domain_list = domains or MARKETPLACE_DOMAINS
    query = f"{keyword} outdoor gear"
    return search_web(
        query,
        max_results=max_results,
        include_domains=domain_list,
    )


def search_discovery(queries: list[str], max_results: int = 5) -> list[dict[str, Any]]:
    """Broad discovery queries for Scout Bloom — recent news hits."""
    hits: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for query in queries:
        for result in search_web(
            query,
            max_results=max_results,
            topic="news",
            time_range="month",
        ):
            url = result.get("url", "")
            if url and url not in seen_urls:
                hits.append({**result, "discovery_query": query})
                seen_urls.add(url)
    return hits
