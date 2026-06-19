from __future__ import annotations

import re
from typing import Any

from src.radar.models.signal import SignalRow
from src.radar.tools.competitor import aggregate_coverage
from src.radar.tools.llm import synthesize_bloom_trends
from src.radar.tools.tavily_search import search_discovery, search_marketplace, search_news

EARLY_STAGE_PATTERNS = (
    "weak",
    "early adoption",
    "dark horse",
    "weak signal",
    "weak to growing",
    "12–18",
    "12-18",
)
GROWING_PATTERNS = ("growing", "6–12", "6-12")
STRONG_PATTERNS = ("strong", "market proof", "immediate")


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _keyword_matches_seed(keyword: str, seed_keywords: list[str]) -> bool:
    kw = _normalize(keyword)
    for seed in seed_keywords:
        seed_norm = _normalize(seed)
        if seed_norm in kw or kw in seed_norm:
            return True
        if kw.split() and seed_norm.split():
            if kw.split()[0] == seed_norm.split()[0] and len(kw.split()[0]) > 4:
                return True
    return False


def _early_stage_bonus(text: str) -> float:
    lower = text.lower()
    if any(p in lower for p in EARLY_STAGE_PATTERNS):
        return 1.0
    if any(p in lower for p in GROWING_PATTERNS):
        return 0.5
    if any(p in lower for p in STRONG_PATTERNS):
        return 0.2
    return 0.6


def _coverage_gap_score(status: str) -> float:
    return {
        "absent": 1.0,
        "partially_covered": 0.7,
        "unknown": 0.5,
        "not_relevant": 0.3,
        "covered": 0.2,
    }.get(status, 0.5)


def _source_diversity_score(types: set[str]) -> float:
    mapped = set()
    for t in types:
        if t in ("search",):
            mapped.add("search")
        elif t in ("competitor", "marketplace"):
            mapped.add("marketplace")
        elif t in ("web", "social"):
            mapped.add("social")
        else:
            mapped.add(t)
    return min(1.0, len(mapped) / 3)


def _recency_score(signals: list[SignalRow]) -> float:
    tools = {s.created_by_tool for s in signals}
    if "tavily_discovery" in tools or "tavily_news" in tools:
        return 1.0
    if "tavily_marketplace" in tools:
        return 0.7
    return 0.3


def _bloom_badge(score: float, stage_text: str) -> str:
    lower = stage_text.lower()
    if "dark horse" in lower or score >= 0.75:
        return "Dark horse"
    if score >= 0.55 or "early" in lower or "weak" in lower:
        return "Early bloom"
    return "Watch"


def news_and_marketplace_signals(
    keyword: str,
    market: str = "CH",
    domains: list[str] | None = None,
) -> list[SignalRow]:
    """Tavily news + marketplace hits for live keyword enrichment."""
    rows: list[SignalRow] = []
    observed = "2026-06-19"

    for hit in search_news(keyword, market=market, max_results=3):
        url = hit.get("url", "")
        if not url:
            continue
        rows.append(
            SignalRow(
                source="tavily_news",
                market=market,
                keyword=keyword,
                signal_name=(hit.get("title") or f"News: {keyword}")[:120],
                signal_type="web",
                url=url,
                signal_score=0.55,
                confidence="medium",
                notes=(hit.get("content") or "")[:200],
                observed_at=observed,
                artifact_type="web",
                artifact_uri=url,
                created_by_tool="tavily_news",
            )
        )

    for hit in search_marketplace(keyword, domains=domains, max_results=3):
        url = hit.get("url", "")
        if not url:
            continue
        domain = url.split("/")[2].replace("www.", "") if url.startswith("http") else "marketplace"
        rows.append(
            SignalRow(
                source=domain,
                market=market,
                keyword=keyword,
                signal_name=(hit.get("title") or f"Marketplace: {keyword}")[:120],
                signal_type="marketplace",
                url=url,
                signal_score=0.6,
                confidence="medium",
                notes=(hit.get("content") or "")[:200],
                observed_at=observed,
                artifact_type="web",
                artifact_uri=url,
                created_by_tool="tavily_marketplace",
            )
        )

    return rows


def discovery_signals_from_tavily(
    queries: list[str],
    market: str = "CH",
) -> list[SignalRow]:
    """Broad Tavily discovery hits for Scout Bloom."""
    rows: list[SignalRow] = []
    observed = "2026-06-19"
    for hit in search_discovery(queries):
        url = hit.get("url", "")
        if not url:
            continue
        query = hit.get("discovery_query", queries[0] if queries else "discovery")
        rows.append(
            SignalRow(
                source="tavily_discovery",
                market=market,
                keyword=query[:80],
                signal_name=(hit.get("title") or "Discovery hit")[:120],
                signal_type="web",
                url=url,
                signal_score=0.5,
                confidence="medium",
                notes=(hit.get("content") or "")[:200],
                observed_at=observed,
                artifact_type="web",
                artifact_uri=url,
                created_by_tool="tavily_discovery",
            )
        )
    return rows


def score_bloom(
    keyword: str,
    signals: list[SignalRow],
    coverage_status: str,
    stage_text: str = "",
) -> float:
    types = {s.signal_type for s in signals}
    score = (
        0.35 * _early_stage_bonus(stage_text)
        + 0.25 * _source_diversity_score(types)
        + 0.25 * _coverage_gap_score(coverage_status)
        + 0.15 * _recency_score(signals)
    )
    return round(min(1.0, score), 3)


def _signals_for_keyword(keyword: str, signals: list[SignalRow]) -> list[SignalRow]:
    kw = _normalize(keyword)
    matched = [s for s in signals if kw in _normalize(s.keyword) or _normalize(s.keyword) in kw]
    if matched:
        return matched
    tokens = [t for t in kw.split() if len(t) > 3]
    if not tokens:
        return []
    return [s for s in signals if any(t in _normalize(s.keyword) for t in tokens)]


def _rule_based_candidates(
    recommendations: dict,
    seed_keywords: list[str],
    signals: list[SignalRow],
    domains: list[str],
) -> list[dict[str, Any]]:
    picks: list[dict[str, Any]] = []
    for row in recommendations.get("agent_synthesis", []):
        kw = row.get("keyword", "")
        if not kw or _keyword_matches_seed(kw, seed_keywords):
            continue

        cluster_signals = _signals_for_keyword(kw, signals)
        types = {s.signal_type for s in cluster_signals}
        if len(types) < 2 and len(cluster_signals) < 2:
            continue

        coverage, cov_urls = aggregate_coverage(kw.split("(")[0].strip(), domains)
        stage_text = " ".join(
            filter(
                None,
                [
                    row.get("evidence_summary", ""),
                    row.get("transferability", ""),
                    row.get("synthesis_label", ""),
                ],
            )
        )
        bloom_score = score_bloom(kw, cluster_signals, coverage, stage_text)
        urls = list(dict.fromkeys(row.get("evidence_urls", []) + cov_urls + [s.url for s in cluster_signals if s.url]))[:10]

        picks.append(
            {
                "keyword": kw,
                "opportunity": row.get("opportunity", kw),
                "bloom_score": bloom_score,
                "bloom_stage": "early" if _early_stage_bonus(stage_text) >= 0.5 else "watch",
                "timing_window": _extract_timing(row.get("transferability", ""), stage_text),
                "coverage_status": coverage,
                "recommended_action": row.get("recommended_action", "Pilot assortment — monitor corroboration"),
                "evidence_urls": urls,
                "confidence": row.get("confidence", "medium"),
                "range_tag": row.get("range_tag", "experimental"),
                "source": "Scout Bloom",
                "discovered_by": "agent_synthesis",
                "bloom_badge": _bloom_badge(bloom_score, stage_text),
                "bloom_rationale": row.get("evidence_summary", "")[:240],
            }
        )
    return picks


def _extract_timing(transferability: str, stage_text: str) -> str:
    combined = f"{transferability} {stage_text}"
    for pattern in ("12–18 months", "12-18 months", "6–12 months", "6-12 months", "Immediate"):
        if pattern.lower() in combined.lower():
            return pattern.replace("–", "-")
    if "weak" in combined.lower():
        return "12-18 months"
    return "6-12 months"


def _claude_candidates(
    discovery_signals: list[SignalRow],
    recommendations: dict,
    seed_keywords: list[str],
    domains: list[str],
    signals: list[SignalRow],
    max_picks: int,
) -> list[dict[str, Any]]:
    snippets = [
        {"title": s.signal_name, "content": s.notes, "url": s.url}
        for s in discovery_signals
    ]
    agent_rows = recommendations.get("agent_synthesis", [])
    claude_picks = synthesize_bloom_trends(
        snippets,
        agent_rows,
        seed_keywords,
        max_picks=max_picks,
    )

    picks: list[dict[str, Any]] = []
    for pick in claude_picks:
        kw = pick.get("keyword", "")
        if not kw or _keyword_matches_seed(kw, seed_keywords):
            continue

        cluster_signals = _signals_for_keyword(kw, signals + discovery_signals)
        coverage, cov_urls = aggregate_coverage(kw, domains)
        stage_text = pick.get("bloom_rationale", "")
        bloom_score = score_bloom(kw, cluster_signals, coverage, stage_text)
        urls = list(
            dict.fromkeys(
                [s.url for s in cluster_signals if s.url]
                + cov_urls
            )
        )[:10]

        picks.append(
            {
                "keyword": kw,
                "opportunity": pick.get("opportunity", kw),
                "bloom_score": bloom_score,
                "bloom_stage": "early",
                "timing_window": pick.get("timing_window", "12-18 months"),
                "coverage_status": coverage,
                "recommended_action": pick.get("recommended_action", "Pilot 2-3 SKUs"),
                "evidence_urls": urls,
                "confidence": pick.get("confidence", "medium"),
                "range_tag": "experimental",
                "source": "Scout Bloom",
                "discovered_by": "tavily_discovery+claude",
                "bloom_badge": _bloom_badge(bloom_score, stage_text),
                "bloom_rationale": pick.get("bloom_rationale", ""),
            }
        )
    return picks


def find_bloom_candidates(
    signals: list[SignalRow],
    config: dict,
    recommendations: dict,
) -> tuple[list[dict[str, Any]], list[SignalRow]]:
    """
    Rule-based picks from agent_synthesis outside seed keywords + Claude picks from Tavily discovery.
    Returns (emerging_trends, discovery_signal_rows).
    """
    seed_keywords = config.get("seed_keywords", [])
    domains = config.get("competitors", [])
    queries = config.get(
        "bloom_discovery_queries",
        [
            "emerging outdoor trends Switzerland 2026",
            "rising DACH outdoor product categories",
            "new outdoor gear social media trend 2026",
        ],
    )
    max_picks = int(config.get("max_bloom_picks", 5))

    discovery_rows = discovery_signals_from_tavily(queries)
    all_signals = signals + discovery_rows

    rule_picks = _rule_based_candidates(recommendations, seed_keywords, all_signals, domains)
    claude_picks = _claude_candidates(
        discovery_rows,
        recommendations,
        seed_keywords,
        domains,
        all_signals,
        max_picks=3,
    )

    merged: dict[str, dict[str, Any]] = {}
    for pick in rule_picks + claude_picks:
        key = _normalize(pick["keyword"])
        existing = merged.get(key)
        if existing is None or pick["bloom_score"] > existing["bloom_score"]:
            merged[key] = pick

    ranked = sorted(merged.values(), key=lambda p: p["bloom_score"], reverse=True)
    return ranked[:max_picks], discovery_rows
