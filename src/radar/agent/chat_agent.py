from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.radar.insight.live_bloom import (
    CATEGORY_OPTIONS,
    build_charts,
    build_evidence,
    build_retailer_playbook,
    enrich_bloom_prediction,
    ensure_minimum_bloom_predictions,
)
from src.radar.insight.market_capture import estimate_market_capture
from src.radar.models.chat import ChatMode, ChatResponse
from src.radar.tools.llm import get_claude_api_key, get_claude_model
from src.radar.tools.tavily_search import search_discovery, search_marketplace, search_news, search_web

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "config" / "scenario.yaml"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _require_live_keys() -> None:
    if not get_claude_api_key():
        raise RuntimeError("CLAUDE_API_KEY is not set. Add it to .env in hercode-zenline-hackathon.")
    if not os.getenv("TAVILY_API_KEY", "").strip():
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to .env in hercode-zenline-hackathon.")


def live_search_available() -> bool:
    load_dotenv(ROOT / ".env")
    return bool(get_claude_api_key() and os.getenv("TAVILY_API_KEY", "").strip())


def _extract_keyword(message: str) -> str:
    msg = message.strip()
    for prefix in (
        "Category drill-down:",
        "Crosscheck my product idea:",
        "Crosscheck my idea:",
        "Estimate TAM and addressable revenue for",
    ):
        if msg.lower().startswith(prefix.lower()):
            msg = msg[len(prefix) :].strip()
    msg = re.sub(r"\s+in\s+(CH|DACH|US|Switzerland)\s*$", "", msg, flags=re.I)
    msg = re.sub(r"^—.*$", "", msg).strip()
    return msg[:80] if msg else message[:80]


def _parse_category_id(message: str) -> str | None:
    lower = message.lower()
    for cat in CATEGORY_OPTIONS:
        if cat["id"] in lower or cat["label"].lower() in lower:
            return cat["id"]
    return None


def _category_by_id(cat_id: str) -> dict[str, str] | None:
    for cat in CATEGORY_OPTIONS:
        if cat["id"] == cat_id:
            return cat
    return None


def _infer_demand_driver_from_hits(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "mixed"
    text = " ".join((h.get("content") or "") + " " + (h.get("title") or "") for h in hits).lower()
    trade_markers = ("forecast", "report", "ispo", "industry", "retailer survey", "press release")
    consumer_markers = ("review", "buy", "sell out", "sold out", "tiktok", "youtube", "search trend", "marketplace")
    trade = sum(1 for m in trade_markers if m in text)
    consumer = sum(1 for m in consumer_markers if m in text)
    if consumer >= 2 and trade <= consumer:
        return "consumer_pull"
    if trade >= 2 and consumer == 0:
        return "trade_push"
    if consumer >= 1 and trade >= 1:
        return "mixed"
    return "consumer_pull" if consumer else "mixed"


def _run_tavily(
    mode: ChatMode,
    message: str,
    keyword: str,
    market: str,
    config: dict,
    *,
    category_id: str | None = None,
    trend_context: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    steps: list[str] = []
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(results: list[dict[str, Any]]) -> None:
        for h in results:
            url = h.get("url", "")
            if url and url not in seen:
                seen.add(url)
                hits.append(h)

    region = "Switzerland" if market == "CH" else market
    trends_hint = ", ".join(trend_context[:4]) if trend_context else keyword

    if mode == "category":
        cat = _category_by_id(category_id or "") or CATEGORY_OPTIONS[0]
        hint = cat["search_hint"]
        add(search_marketplace(f"{hint} {region}", max_results=5))
        add(search_web(f"{hint} trending features styles {region} 2026 2027", max_results=4))
        add(search_web(f"site:transa.ch {cat['label']}", max_results=3))
        add(search_web(f"{trends_hint} {cat['label']} product features retail", max_results=3))
        add(search_news(f"{cat['label']} outdoor retail {region}", market=market, max_results=2))
        steps.append(f"Tavily category drill-down: {cat['label']} ({len(hits)} sources)")

    elif mode == "trends":
        base_queries = config.get(
            "bloom_discovery_queries",
            ["emerging outdoor trends Switzerland 2026"],
        )
        add(search_discovery(base_queries[:3]))
        add(search_web(f"{keyword} outdoor trend {region} 2026", max_results=4))
        add(search_web(message[:120], max_results=3))
        steps.append(f"Tavily trend discovery ({len(hits)} sources)")

    elif mode == "competitors":
        for domain in config.get("competitors", ["transa.ch", "ochsnersport.ch", "decathlon.ch"]):
            add(search_web(f"site:{domain} {keyword} outdoor", max_results=2))
        add(search_web(f"{keyword} assortment gap Swiss outdoor retail {region}", max_results=3))
        add(search_marketplace(keyword, max_results=3))
        steps.append(f"Tavily competitor analysis ({len(hits)} sources)")

    elif mode == "crosscheck":
        add(search_news(keyword, market=market, max_results=4))
        add(search_marketplace(keyword, max_results=4))
        add(search_web(f"site:transa.ch {keyword}", max_results=3))
        add(search_web(f"site:ochsnersport.ch {keyword}", max_results=2))
        add(search_web(f"{keyword} consumer demand {region}", max_results=3))
        steps.append(f"Tavily crosscheck ({len(hits)} sources)")

    elif mode == "roi":
        add(search_marketplace(keyword, max_results=4))
        add(search_web(f"{keyword} market size outdoor retail {region}", max_results=3))
        add(search_news(keyword, market=market, max_results=2))
        steps.append(f"Tavily ROI research ({len(hits)} sources)")

    else:
        add(search_web(message, max_results=5))
        add(search_news(keyword, market=market, max_results=3))
        add(search_marketplace(keyword, max_results=3))
        steps.append(f"Tavily web search ({len(hits)} sources)")

    return hits[:15], steps


def _parse_claude_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError("Claude did not return valid JSON.")
    raw = match.group()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Claude returned malformed JSON: {e}") from e


def _claude_synthesize(
    mode: ChatMode,
    message: str,
    keyword: str,
    market: str,
    hits: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    *,
    category_id: str | None = None,
    trend_context: list[str] | None = None,
) -> dict[str, Any]:
    api_key = get_claude_api_key()
    indexed_snippets = "\n".join(
        f"[{ev['id']}] [{ev.get('title', 'Source')}] ({ev.get('source_type', 'web')}) "
        f"{ev.get('snippet', '')[:180]} — {ev.get('url', '')}"
        for ev in evidence[:15]
    )
    if not indexed_snippets:
        raise RuntimeError("Tavily returned no results. Try a different query or check your API key.")

    if not indexed_snippets:
        raise RuntimeError("Tavily returned no results. Try a different query or check your API key.")

    if mode == "category":
        cat = _category_by_id(category_id or _parse_category_id(message) or "") or CATEGORY_OPTIONS[0]
        trends_line = ", ".join(trend_context[:5]) if trend_context else keyword
        system = (
            "You are ZenScout assortment lead for Swiss outdoor retail. "
            "Given bloom trends already spotted, recommend specific product styles and features to stock "
            "in the chosen category. Use ONLY provided snippets. Cite evidence_ids."
        )
        user_prompt = f"""Category: {cat['label']} ({cat['id']})
Market: {market}
Prior bloom trends: {trends_line}
User: {message}

Snippets (evidence_ids 0..N-1):
{indexed_snippets}

Return ONLY compact JSON. Max 4 product_stocking rows. You MUST include exactly 3 bloom_predictions for this category.
{{
  "reply": "2-3 sentences: what to stock in {cat['label']} and why now",
  "demand_driver": "consumer_pull",
  "product_stocking": [
    {{
      "style": "e.g. lightweight trail runner",
      "features": ["feature1", "feature2", "feature3"],
      "example_products": "brands or SKU types from snippets",
      "priority": "high",
      "timing": "SS2027",
      "rationale": "short why",
      "evidence_ids": [0, 1]
    }}
  ],
  "bloom_predictions": [
    {{
      "keyword": "specific product trend in {cat['label']}",
      "opportunity": "what will bloom",
      "bloom_score": 0.72,
      "bloom_stage": "early",
      "bloom_badge": "Early bloom",
      "timing_window": "6-12 months",
      "bloom_rationale": "short inference chain",
      "weak_signal_note": "what is weak today",
      "recommended_action": "retailer move",
      "confidence": "medium",
      "coverage_status": "partially_covered",
      "evidence_ids": [0, 2]
    }}
  ],
  "recommendations": [],
  "top_keyword": "{cat['label']}",
  "recommended_action": "lead stocking move",
  "risks": "short note"
}}"""
    else:
        system = (
            "You are ZenScout, a predictive assortment intelligence agent for Swiss outdoor retail. "
            "Your job is to LEAD the category manager: infer what will BLOOM from weak or partial signals, "
            "not just summarize search results. Use ONLY the provided live web snippets — do not invent URLs. "
            "Weak signals (single marketplace listing, niche social mention, early trade press) are valid inputs "
            "for bloom prediction when you explain the inference chain. "
            "Classify demand_driver: consumer_pull if multiple independent consumer signals; "
            "trade_push if only industry/editorial; mixed otherwise."
        )
        user_prompt = f"""Mode: {mode}
Market: {market}
User question: {message}
Focus keyword: {keyword}

Live web snippets (index these as evidence_ids 0..N-1):
{indexed_snippets}

Return ONLY compact valid JSON (no markdown). Keep strings under 140 chars.
You MUST return exactly 3 bloom_predictions (never fewer). Max 2 recommendations.
{{
  "reply": "lead with top bloom prediction",
  "demand_driver": "consumer_pull",
  "bloom_predictions": [
    {{
      "keyword": "string",
      "opportunity": "string",
      "bloom_score": 0.72,
      "bloom_stage": "early",
      "bloom_badge": "Early bloom",
      "timing_window": "6-12 months",
      "bloom_rationale": "short inference chain",
      "weak_signal_note": "what is weak today",
      "recommended_action": "retailer move",
      "confidence": "medium",
      "coverage_status": "partially_covered",
      "evidence_ids": [0, 2]
    }}
  ],
  "recommendations": [
    {{
      "keyword": "string",
      "opportunity": "string",
      "recommended_action": "string",
      "signal_score": 0.65,
      "confidence": "medium",
      "coverage_status": "unknown",
      "evidence_ids": [1]
    }}
  ],
  "top_keyword": "string",
  "recommended_action": "lead action this week",
  "risks": "short risk note"
}}

Predict what will BLOOM from weak signals. Cite evidence_ids only."""

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=get_claude_model(),
        max_tokens=2500,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    parsed = _parse_claude_json(text)
    if not parsed.get("reply"):
        raise RuntimeError("Claude returned empty reply.")
    return parsed


def _parse_json_list_field(val: Any) -> list[dict]:
    if isinstance(val, list):
        return [x for x in val if isinstance(x, dict)]
    return []


def run_chat(
    message: str,
    mode: ChatMode = "freeform",
    market: str = "CH",
    trend_context: list[str] | None = None,
) -> ChatResponse:
    load_dotenv(ROOT / ".env")
    _require_live_keys()
    config = _load_config()
    market = market.upper()
    keyword = _extract_keyword(message)
    steps: list[str] = []
    trend_context = [t for t in (trend_context or []) if t][:6]
    category_id: str | None = None
    selected_category: str | None = None

    if mode == "freeform":
        lower = message.lower()
        if lower.startswith("category drill-down:"):
            mode = "category"
        elif any(w in lower for w in ("competitor", "competitors", "transa", "ochsner", "assortment gap")):
            mode = "competitors"
        elif any(w in lower for w in ("tam", "roi", "revenue", "pricing", "capture", "market size")):
            mode = "roi"
        elif any(w in lower for w in ("crosscheck", "my idea", "validate", "next hit")):
            mode = "crosscheck"
        elif any(w in lower for w in ("trend", "bloom", "emerging", "next year")):
            mode = "trends"

    if mode == "category":
        category_id = _parse_category_id(message)
        cat = _category_by_id(category_id or "") if category_id else None
        selected_category = cat["id"] if cat else category_id

    tavily_hits, tavily_steps = _run_tavily(
        mode,
        message,
        keyword,
        market,
        config,
        category_id=category_id,
        trend_context=trend_context,
    )
    steps.extend(tavily_steps)

    evidence = build_evidence(tavily_hits)
    parsed = _claude_synthesize(
        mode,
        message,
        keyword,
        market,
        tavily_hits,
        evidence,
        category_id=category_id,
        trend_context=trend_context,
    )
    steps.append(
        "Claude category stocking synthesis" if mode == "category" else "Claude bloom prediction synthesis"
    )

    domains = config.get("competitors", [])
    product_stocking = _parse_json_list_field(parsed.get("product_stocking"))
    for row in product_stocking:
        ids = row.get("evidence_ids") or []
        row["evidence_urls"] = [
            evidence[i]["url"] for i in ids if isinstance(i, int) and 0 <= i < len(evidence)
        ]

    raw_predictions = _parse_json_list_field(parsed.get("bloom_predictions"))
    if not raw_predictions:
        raw_predictions = _parse_json_list_field(parsed.get("emerging_trends"))

    bloom_predictions = [
        enrich_bloom_prediction(raw, tavily_hits, market, domains, evidence)
        for raw in raw_predictions[:5]
    ]
    bloom_predictions.sort(key=lambda p: p["bloom_score"], reverse=True)

    recommendations = _parse_json_list_field(parsed.get("recommendations"))

    cat_label = None
    if mode == "category":
        cat = _category_by_id(category_id or _parse_category_id(message) or "")
        cat_label = cat["label"] if cat else None

    bloom_predictions = ensure_minimum_bloom_predictions(
        bloom_predictions,
        hits=tavily_hits,
        evidence=evidence,
        market=market,
        domains=domains,
        product_stocking=product_stocking,
        recommendations=recommendations,
        keyword=keyword,
        category_label=cat_label,
    )
    for rec in recommendations:
        ids = rec.get("evidence_ids") or []
        rec["evidence_urls"] = [
            evidence[i]["url"] for i in ids if isinstance(i, int) and 0 <= i < len(evidence)
        ]

    emerging = _parse_json_list_field(parsed.get("emerging_trends"))
    if not emerging and bloom_predictions:
        emerging = [
            {
                "keyword": p["keyword"],
                "opportunity": p["opportunity"],
                "bloom_score": p["bloom_score"],
                "timing_window": p["timing_window"],
                "recommended_action": p["recommended_action"],
                "coverage_status": p["coverage_status"],
                "bloom_badge": p["bloom_badge"],
            }
            for p in bloom_predictions
        ]

    top_kw = str(parsed.get("top_keyword") or keyword)
    coverage = "unknown"
    if recommendations:
        coverage = recommendations[0].get("coverage_status", "unknown")
    market_capture = estimate_market_capture(
        top_kw,
        market,
        float(recommendations[0].get("signal_score", 0.6)) if recommendations else 0.6,
        str(coverage),
    )

    evidence_urls = list(
        dict.fromkeys(
            [ev["url"] for ev in evidence if ev.get("url")]
            + [u for p in bloom_predictions for u in p.get("evidence_urls", [])]
        )
    )[:15]
    demand_driver = parsed.get("demand_driver") or _infer_demand_driver_from_hits(tavily_hits)
    if demand_driver not in ("consumer_pull", "trade_push", "mixed"):
        demand_driver = _infer_demand_driver_from_hits(tavily_hits)

    charts = build_charts(bloom_predictions, evidence, market_capture)
    playbook = _parse_json_list_field(parsed.get("retailer_playbook"))
    if not playbook:
        playbook = build_retailer_playbook(bloom_predictions, recommendations, parsed)
    else:
        for i, item in enumerate(playbook):
            item["priority"] = i + 1

    show_category_prompt = mode == "trends" and len(bloom_predictions) > 0 and not product_stocking

    return ChatResponse(
        reply=str(parsed.get("reply", "")),
        mode=mode,
        recommendations=recommendations,
        emerging_trends=emerging,
        bloom_predictions=bloom_predictions,
        product_stocking=product_stocking,
        evidence=evidence,
        charts=charts,
        retailer_playbook=playbook,
        market_capture=market_capture,
        evidence_urls=evidence_urls,
        demand_driver=demand_driver,
        score_explanation={
            "plain_english": parsed.get("reply"),
            "recommended_action": parsed.get("recommended_action"),
            "risks": parsed.get("risks"),
            "source_count": len(tavily_hits),
            "prediction_count": len(bloom_predictions),
            "live_only": True,
            "bloom_score_math": bloom_predictions[0].get("score_math") if bloom_predictions else None,
        },
        steps=steps,
        used_live_search=True,
        show_category_prompt=show_category_prompt,
        category_options=CATEGORY_OPTIONS if show_category_prompt else [],
        selected_category=selected_category,
    )
