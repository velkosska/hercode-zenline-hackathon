from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.radar.pipeline.enrich import FINAL_DIR, ROOT

MIN_BLOOM_PREDICTIONS = 3

from src.radar.insight.bloom_detector import (
    _bloom_badge,
    _coverage_gap_score,
    _early_stage_bonus,
    _recency_score,
    _source_diversity_score,
    score_bloom,
)
from src.radar.models.signal import SignalRow
from src.radar.tools.competitor import aggregate_coverage

NEWS_DOMAINS = ("reuters", "apnews", "bbc", "ft.com", "retail", "ispo", "outdoor")
MARKETPLACE_DOMAINS = ("transa.ch", "ochsnersport.ch", "decathlon.ch", "galaxus.ch", "amazon", "ebay")
SOCIAL_MARKERS = ("tiktok", "youtube", "instagram", "reddit", "komoot")

CATEGORY_OPTIONS: list[dict[str, str]] = [
    {"id": "shoes", "label": "Shoes", "icon": "shoes", "search_hint": "footwear trail running lifestyle sneakers"},
    {"id": "coats", "label": "Coats & shells", "icon": "coats", "search_hint": "jackets outerwear gore-tex insulated shells"},
    {"id": "gear", "label": "Gear", "icon": "gear", "search_hint": "backpacks tents sleeping bags packs"},
    {"id": "accessories", "label": "Accessories", "icon": "accessories", "search_hint": "helmets gloves optics hydration via ferrata"},
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def classify_source_type(hit: dict[str, Any]) -> str:
    url = (hit.get("url") or "").lower()
    title = (hit.get("title") or "").lower()
    content = (hit.get("content") or "").lower()
    host = urlparse(url).netloc.replace("www.", "") if url else ""

    if any(d in host for d in MARKETPLACE_DOMAINS):
        return "marketplace"
    if hit.get("discovery_query"):
        return "discovery"
    if any(m in url or m in content for m in SOCIAL_MARKERS):
        return "social"
    if any(n in host or n in title for n in NEWS_DOMAINS) or "news" in host:
        return "news"
    if any(w in content for w in ("forecast", "report", "industry", "trade", "retailer")):
        return "trade"
    return "web"


def build_evidence(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        url = hit.get("url", "")
        if not url:
            continue
        snippet = (hit.get("content") or "")[:320]
        source_type = classify_source_type(hit)
        relevance = 0.55
        if source_type in ("marketplace", "social"):
            relevance = 0.72
        elif source_type == "news":
            relevance = 0.65
        evidence.append(
            {
                "id": i,
                "title": (hit.get("title") or "Source")[:140],
                "url": url,
                "snippet": snippet,
                "source_type": source_type,
                "relevance": relevance,
                "domain": urlparse(url).netloc.replace("www.", ""),
            }
        )
    return evidence


def _hits_to_signals(keyword: str, hits: list[dict[str, Any]], market: str) -> list[SignalRow]:
    rows: list[SignalRow] = []
    kw_norm = _normalize(keyword)
    for hit in hits:
        text = f"{hit.get('title', '')} {hit.get('content', '')}".lower()
        if kw_norm and kw_norm not in _normalize(text) and len(kw_norm.split()) > 1:
            if not any(part in text for part in kw_norm.split() if len(part) > 4):
                continue
        source_type = classify_source_type(hit)
        signal_type = "marketplace" if source_type == "marketplace" else "web"
        rows.append(
            SignalRow(
                source=hit.get("url", "")[:40],
                market=market,
                keyword=keyword,
                signal_name=(hit.get("title") or keyword)[:120],
                signal_type=signal_type,
                url=hit.get("url", ""),
                signal_score=0.5,
                confidence="medium",
                notes=(hit.get("content") or "")[:200],
                observed_at="2026-06-19",
                artifact_type="web",
                artifact_uri=hit.get("url", ""),
                created_by_tool=f"tavily_{source_type}",
            )
        )
    return rows[:8]


def explain_bloom_score(
    breakdown: dict[str, Any],
    computed_score: float,
    llm_score: float,
    final_score: float,
) -> dict[str, Any]:
    early = float(breakdown.get("early_stage", 0))
    diversity = float(breakdown.get("source_diversity", 0))
    coverage = float(breakdown.get("coverage_gap", 0))
    recency = float(breakdown.get("recency", 0))
    recomputed = round(
        0.35 * early + 0.25 * diversity + 0.25 * coverage + 0.15 * recency,
        3,
    )
    return {
        "formula": "bloom_score = 0.55 × computed + 0.45 × AI_signal",
        "computed_formula": (
            "computed = 0.35×early_stage + 0.25×source_diversity "
            "+ 0.25×coverage_gap + 0.15×recency"
        ),
        "weights": {
            "early_stage": 0.35,
            "source_diversity": 0.25,
            "coverage_gap": 0.25,
            "recency": 0.15,
        },
        "components": {
            "early_stage": early,
            "source_diversity": diversity,
            "coverage_gap": coverage,
            "recency": recency,
        },
        "computed_score": computed_score,
        "recomputed_check": recomputed,
        "llm_score": round(llm_score, 3),
        "blend_weights": {"computed": 0.55, "llm": 0.45},
        "final_score": final_score,
        "plain_english": (
            f"Scout blends a rule-based score ({computed_score:.2f}) from live evidence diversity, "
            f"assortment gaps, and how early the signal is, with Claude's read ({llm_score:.2f}). "
            f"Final bloom score = {final_score:.2f}."
        ),
    }


def build_trajectory(bloom_score: float, stage_text: str = "") -> list[dict[str, Any]]:
    """Project demand index from weak signal today to predicted bloom."""
    early = _early_stage_bonus(stage_text)
    now = round(max(0.15, min(0.45, bloom_score * 0.35 + early * 0.1)), 2)
    return [
        {"label": "Now", "demand_index": now, "phase": "weak signal"},
        {"label": "+6 mo", "demand_index": round(min(0.85, now + bloom_score * 0.35), 2), "phase": "building"},
        {"label": "+12 mo", "demand_index": round(min(0.95, bloom_score * 0.9), 2), "phase": "bloom"},
        {"label": "+18 mo", "demand_index": round(min(1.0, bloom_score * 1.05), 2), "phase": "mainstream"},
    ]


def enrich_bloom_prediction(
    raw: dict[str, Any],
    hits: list[dict[str, Any]],
    market: str,
    domains: list[str],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    keyword = str(raw.get("keyword") or "Trend")
    stage_text = " ".join(
        filter(
            None,
            [
                raw.get("weak_signal_note", ""),
                raw.get("bloom_rationale", ""),
                raw.get("opportunity", ""),
            ],
        )
    )
    coverage, cov_urls = aggregate_coverage(keyword.split("(")[0].strip(), domains)
    cluster = _hits_to_signals(keyword, hits, market)
    computed_score = score_bloom(keyword, cluster, coverage, stage_text)
    llm_score = float(raw.get("bloom_score") or 0)
    bloom_score = round(min(1.0, computed_score * 0.55 + llm_score * 0.45), 3)
    types = {s.signal_type for s in cluster}
    breakdown = {
        "early_stage": round(_early_stage_bonus(stage_text), 2),
        "source_diversity": round(_source_diversity_score(types), 2),
        "coverage_gap": round(_coverage_gap_score(coverage), 2),
        "recency": round(_recency_score(cluster), 2),
        "source_count": len(cluster),
        "computed_score": computed_score,
        "llm_score": round(llm_score, 3),
    }
    score_math = explain_bloom_score(breakdown, computed_score, llm_score, bloom_score)

    evidence_ids = raw.get("evidence_ids") or raw.get("evidence_indices") or []
    if not evidence_ids:
        kw_parts = [p for p in _normalize(keyword).split() if len(p) > 3]
        for ev in evidence:
            text = _normalize(f"{ev.get('title', '')} {ev.get('snippet', '')}")
            if any(p in text for p in kw_parts):
                evidence_ids.append(ev["id"])

    linked_urls = list(
        dict.fromkeys(
            [evidence[i]["url"] for i in evidence_ids if isinstance(i, int) and 0 <= i < len(evidence)]
            + cov_urls
        )
    )[:8]

    trajectory = raw.get("trajectory")
    if not isinstance(trajectory, list) or len(trajectory) < 3:
        trajectory = build_trajectory(bloom_score, stage_text)

    return {
        "keyword": keyword,
        "bloom_score": bloom_score,
        "bloom_stage": raw.get("bloom_stage") or ("early" if bloom_score >= 0.55 else "watch"),
        "bloom_badge": raw.get("bloom_badge") or _bloom_badge(bloom_score, stage_text),
        "timing_window": raw.get("timing_window") or "12–18 months",
        "opportunity": raw.get("opportunity") or keyword,
        "bloom_rationale": raw.get("bloom_rationale") or raw.get("opportunity", ""),
        "weak_signal_note": raw.get("weak_signal_note")
        or "Weak corroboration today — projected from adjacent demand and coverage gaps.",
        "recommended_action": raw.get("recommended_action") or "Pilot 2–3 SKUs and monitor sell-through.",
        "confidence": raw.get("confidence") or ("medium" if bloom_score >= 0.5 else "low"),
        "coverage_status": raw.get("coverage_status") or coverage,
        "trajectory": trajectory,
        "evidence_ids": evidence_ids[:6],
        "evidence_urls": linked_urls,
        "signal_breakdown": breakdown,
        "score_math": score_math,
    }


def _pipeline_bloom_seeds(market: str, limit: int = 6) -> list[dict[str, Any]]:
    """Fallback bloom rows from Scout pipeline when live synthesis returns too few."""
    for path in (FINAL_DIR / "recommendations.json", ROOT / "data" / "recommendations.json"):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        seeds: list[dict[str, Any]] = []
        for src_key in ("emerging_trends", "combined_top"):
            for row in data.get(src_key) or []:
                mc = row.get("market_capture") or {}
                if mc.get("market") and str(mc["market"]).upper() != market.upper():
                    continue
                seeds.append(row)
        seeds.sort(
            key=lambda r: float(r.get("bloom_score") or r.get("signal_score") or 0),
            reverse=True,
        )
        if seeds:
            return seeds[:limit]
    return []


def ensure_minimum_bloom_predictions(
    predictions: list[dict[str, Any]],
    *,
    min_count: int = MIN_BLOOM_PREDICTIONS,
    hits: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    market: str,
    domains: list[str],
    product_stocking: list[dict[str, Any]] | None = None,
    recommendations: list[dict[str, Any]] | None = None,
    keyword: str = "",
    category_label: str | None = None,
) -> list[dict[str, Any]]:
    """Guarantee at least `min_count` enriched bloom predictions for every chat response."""
    out = list(predictions)
    seen = {_normalize(p.get("keyword", "")) for p in out if p.get("keyword")}

    def add_raw(raw: dict[str, Any]) -> None:
        if len(out) >= min_count:
            return
        kw = str(raw.get("keyword") or raw.get("opportunity") or raw.get("style") or "").strip()
        if not kw:
            return
        norm = _normalize(kw)
        if not norm or norm in seen:
            return
        seen.add(norm)
        out.append(enrich_bloom_prediction(raw, hits, market, domains, evidence))

    for i, row in enumerate(product_stocking or []):
        style = str(row.get("style") or "").strip()
        if not style:
            continue
        add_raw(
            {
                "keyword": style,
                "opportunity": style,
                "bloom_score": max(0.52, 0.72 - i * 0.06),
                "bloom_stage": "early",
                "bloom_badge": "Category bloom",
                "timing_window": row.get("timing") or "6–12 months",
                "bloom_rationale": row.get("rationale")
                or f"Live category signals support stocking {style} in {category_label or 'this category'}.",
                "weak_signal_note": "Synthesized from category drill-down and marketplace listings.",
                "recommended_action": f"Pilot {style} with 2–3 hero SKUs.",
                "confidence": "medium" if row.get("priority") != "high" else "high",
                "coverage_status": "partially_covered",
                "evidence_ids": row.get("evidence_ids") or [],
            }
        )

    for i, rec in enumerate(recommendations or []):
        add_raw(
            {
                "keyword": rec.get("keyword") or rec.get("opportunity") or keyword,
                "opportunity": rec.get("opportunity") or rec.get("keyword") or keyword,
                "bloom_score": float(rec.get("signal_score") or rec.get("bloom_score") or max(0.5, 0.68 - i * 0.05)),
                "bloom_stage": "early",
                "timing_window": rec.get("timing_window") or "6–12 months",
                "bloom_rationale": rec.get("recommended_action") or rec.get("opportunity") or "Live recommendation.",
                "weak_signal_note": "Derived from corroborated live search snippets.",
                "recommended_action": rec.get("recommended_action") or "Monitor and test buy.",
                "confidence": rec.get("confidence") or "medium",
                "coverage_status": rec.get("coverage_status") or "unknown",
                "evidence_ids": rec.get("evidence_ids") or [],
            }
        )

    for i, ev in enumerate(evidence):
        title = str(ev.get("title") or "").strip()
        if len(title) < 12:
            continue
        add_raw(
            {
                "keyword": title[:72],
                "opportunity": title[:100],
                "bloom_score": max(0.48, 0.62 - i * 0.04),
                "bloom_stage": "watch",
                "bloom_badge": "Weak signal",
                "timing_window": "12–18 months",
                "bloom_rationale": (ev.get("snippet") or title)[:140],
                "weak_signal_note": f"Single-source {ev.get('source_type', 'web')} signal — watch for corroboration.",
                "recommended_action": "Track weekly; expand if second source confirms.",
                "confidence": "low",
                "coverage_status": "unknown",
                "evidence_ids": [ev["id"]],
            }
        )

    if keyword:
        add_raw(
            {
                "keyword": keyword,
                "opportunity": keyword,
                "bloom_score": 0.58,
                "bloom_stage": "watch",
                "timing_window": "6–12 months",
                "bloom_rationale": f"User focus: {keyword} — projected from adjacent live demand.",
                "weak_signal_note": "Anchor prediction from the query topic.",
                "recommended_action": "Validate with a small buy or A/B floor placement.",
                "confidence": "medium",
                "coverage_status": "unknown",
                "evidence_ids": [ev["id"] for ev in evidence[:2]],
            }
        )

    for i, seed in enumerate(_pipeline_bloom_seeds(market)):
        add_raw(
            {
                "keyword": seed.get("keyword") or seed.get("opportunity") or f"Pipeline trend {i + 1}",
                "opportunity": seed.get("opportunity") or seed.get("keyword") or "",
                "bloom_score": float(seed.get("bloom_score") or seed.get("signal_score") or 0.55),
                "bloom_stage": seed.get("bloom_stage") or "early",
                "bloom_badge": seed.get("bloom_badge") or "Pipeline signal",
                "timing_window": seed.get("timing_window") or "6–12 months",
                "bloom_rationale": seed.get("bloom_rationale")
                or seed.get("recommended_action")
                or "Scout pipeline corroboration.",
                "weak_signal_note": "Backfilled from Scout pipeline when live synthesis returned fewer than 3 picks.",
                "recommended_action": seed.get("recommended_action") or "Review assortment gap.",
                "confidence": seed.get("confidence") or "medium",
                "coverage_status": seed.get("coverage_status") or "unknown",
                "evidence_ids": [],
            }
        )

    out.sort(key=lambda p: p.get("bloom_score", 0), reverse=True)
    return out[: max(min_count, len(out))]


def build_charts(
    predictions: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    market_capture: dict[str, Any] | None,
) -> dict[str, Any]:
    bloom_ranking = [
        {
            "name": p["keyword"][:28],
            "score": p["bloom_score"],
            "stage": p.get("bloom_stage", "watch"),
        }
        for p in predictions[:5]
    ]

    trajectories = [
        {"keyword": p["keyword"][:24], "points": p.get("trajectory", [])}
        for p in predictions[:3]
    ]

    mix: dict[str, int] = {}
    for ev in evidence:
        t = ev.get("source_type", "web")
        mix[t] = mix.get(t, 0) + 1
    source_mix = [{"type": k, "count": v} for k, v in sorted(mix.items(), key=lambda x: -x[1])]

    capture_funnel: list[dict[str, Any]] = []
    if market_capture:
        capture_funnel = [
            {"label": "Market TAM", "value": market_capture.get("tam_total_chf_m", 0)},
            {"label": "Category TAM", "value": market_capture.get("category_tam_chf_m", 0)},
            {"label": "Addressable", "value": market_capture.get("addressable_revenue_chf_m", 0)},
        ]

    return {
        "bloom_ranking": bloom_ranking,
        "trajectories": trajectories,
        "source_mix": source_mix,
        "capture_funnel": capture_funnel,
    }


def build_retailer_playbook(
    predictions: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    playbook: list[dict[str, Any]] = []
    priority = 1

    top_action = parsed.get("recommended_action")
    if top_action:
        playbook.append(
            {
                "priority": priority,
                "action": str(top_action),
                "horizon": "Now",
                "rationale": "Lead move synthesized from live signals",
            }
        )
        priority += 1

    for pred in predictions[:3]:
        playbook.append(
            {
                "priority": priority,
                "action": pred.get("recommended_action", "Monitor"),
                "horizon": pred.get("timing_window", "12–18 months"),
                "rationale": pred.get("bloom_rationale", pred.get("opportunity", ""))[:200],
                "keyword": pred.get("keyword"),
            }
        )
        priority += 1

    for rec in recommendations[:2]:
        if rec.get("recommended_action"):
            playbook.append(
                {
                    "priority": priority,
                    "action": rec["recommended_action"],
                    "horizon": "Season planning",
                    "rationale": rec.get("opportunity", rec.get("keyword", ""))[:200],
                    "keyword": rec.get("keyword"),
                }
            )
            priority += 1

    return playbook[:6]
