"""Live dashboard payload for ZenScout — metrics, trends, opportunities."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.radar.api.landing_data import fetch_live_trends
from src.radar.insight.live_bloom import build_trajectory, explain_bloom_score
from src.radar.pipeline.enrich import FINAL_DIR, ROOT

CONFIG_PATH = ROOT / "config" / "scenario.yaml"
LINE_COLORS = ["#f97316", "#3b82f6", "#a855f7", "#22c55e"]

HOW_IT_WORKS = [
    {
        "step": "01",
        "title": "Scan the market",
        "body": "Pull live signals from retailers, media, and search demand across your region.",
    },
    {
        "step": "02",
        "title": "Spot the opportunity",
        "body": "Match weak signals to product gaps before competitors move.",
    },
    {
        "step": "03",
        "title": "Score the move",
        "body": "Blend evidence diversity, timing, and market size into a bloom score.",
    },
    {
        "step": "04",
        "title": "Act on the call",
        "body": "Get plain-English actions — buy now, test small, or keep watching.",
    },
]

CHAT_PROMPTS = [
    {
        "id": "category",
        "mode": "category",
        "title": "Dive into a category",
        "description": "Pick a category and get product-level stocking recommendations.",
        "prompt": "Category drill-down: Shoes — what styles and product features should we stock for Swiss outdoor retail?",
        "accent": "blue",
    },
    {
        "id": "crosscheck",
        "mode": "crosscheck",
        "title": "Cross-check my trend idea",
        "description": "Bring your hypothesis — we'll validate it against market data.",
        "prompt": "Crosscheck my product idea: ",
        "accent": "blue",
    },
    {
        "id": "roi",
        "mode": "roi",
        "title": "ROI & pricing analysis",
        "description": "See expected margin, price ladder and payback per opportunity.",
        "prompt": "Estimate TAM and addressable revenue for ",
        "accent": "orange",
    },
]


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _results_path() -> Path:
    final = FINAL_DIR / "recommendations.json"
    if final.exists():
        return final
    return ROOT / "data" / "recommendations.json"


def _load_results() -> dict[str, Any]:
    path = _results_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _signals_path() -> Path:
    for path in (FINAL_DIR / "signals.csv", ROOT / "data" / "signals.csv"):
        if path.exists():
            return path
    return FINAL_DIR / "signals.csv"


def _short_label(text: str, max_len: int = 36) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")[:32]


def _score_math_from_signal(score: float) -> dict[str, Any]:
    breakdown = {
        "early_stage": round(min(1.0, score * 0.65), 2),
        "source_diversity": round(min(1.0, 0.35 + score * 0.4), 2),
        "coverage_gap": round(min(1.0, 0.45 + (1 - score) * 0.25), 2),
        "recency": round(min(1.0, score * 0.75), 2),
    }
    computed = round(
        0.35 * breakdown["early_stage"]
        + 0.25 * breakdown["source_diversity"]
        + 0.25 * breakdown["coverage_gap"]
        + 0.15 * breakdown["recency"],
        3,
    )
    llm_score = round(score, 3)
    final = round(min(1.0, computed * 0.55 + llm_score * 0.45), 3)
    return explain_bloom_score(breakdown, computed, llm_score, final)


def _load_market_signals(market: str) -> list[dict[str, Any]]:
    path = _signals_path()
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("market", "").upper() != market.upper():
                continue
            try:
                score = float(row.get("signal_score") or 0)
            except ValueError:
                score = 0.0
            rows.append(
                {
                    "keyword": (row.get("keyword") or "").strip(),
                    "signal_name": (row.get("signal_name") or row.get("keyword") or "").strip(),
                    "signal_score": score,
                    "confidence": (row.get("confidence") or "medium").lower(),
                    "notes": row.get("notes") or "",
                    "url": row.get("url") or "",
                }
            )
    rows.sort(key=lambda r: -r["signal_score"])
    return rows


def _recommendation_lookup(results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for rec in results.get("recommendations") or []:
        kw = (rec.get("keyword") or "").strip().lower()
        if kw:
            lookup[kw] = rec
    return lookup


def _status_for_item(item: dict[str, Any]) -> str:
    action = (item.get("recommended_action") or "").lower()
    range_tag = (item.get("range_tag") or "").lower()
    score = float(item.get("bloom_score") or item.get("signal_score") or 0)
    confidence = (item.get("confidence") or "medium").lower()

    if "monitor" in action or range_tag == "monitor" or score < 0.48:
        return "keep_watching"
    if score >= 0.72 and confidence == "high":
        return "buy_now"
    if score >= 0.55 or range_tag == "experimental":
        return "worth_testing"
    return "keep_watching"


def _evidence_strength(confidence: str) -> str:
    c = confidence.lower()
    if c == "high":
        return "Strong evidence"
    if c == "medium":
        return "Moderate evidence"
    return "Emerging signal"


def _first_seen_label(item: dict[str, Any], rec_lookup: dict[str, dict[str, Any]]) -> str:
    kw = (item.get("keyword") or "").lower()
    rec = rec_lookup.get(kw.split("(")[0].strip())
    market = rec.get("first_observed_market") if rec else None
    transfer = (rec.get("transferability") or item.get("bloom_rationale") or "") if rec else ""

    if "US search momentum leads CH" in transfer:
        return "First seen in US · Early transfer"
    if "Italy" in transfer or "France" in transfer or "Klettersteig" in kw:
        return "First seen in Italy / France · Strong evidence"
    if market:
        region = "Switzerland" if market.upper() == "CH" else market
        return f"First seen in {region} · {_evidence_strength(item.get('confidence', 'medium'))}"
    return f"First seen in DACH · {_evidence_strength(item.get('confidence', 'medium'))}"


def _category_tag(item: dict[str, Any]) -> str:
    range_tag = (item.get("range_tag") or "").lower()
    keyword = (item.get("keyword") or "").lower()
    if range_tag == "experimental" or any(w in keyword for w in ("merino", "fiber", "material", "alpha")):
        return "material"
    return "product"


def _stocking_dates(timing_window: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", timing_window or "")
    if match:
        start_months = max(1, int(match.group(1)) // 2)
        peak_months = int(match.group(2))
    elif re.search(r"immediate|now|this season", timing_window or "", re.I):
        start_months, peak_months = 1, 6
    else:
        start_months, peak_months = 4, 12

    start = now + timedelta(days=start_months * 30)
    peak = now + timedelta(days=peak_months * 30)
    return start.strftime("%b %Y"), f"Peak around {peak.strftime('%b %Y')}"


def _build_opportunities(results: dict[str, Any], market: str) -> list[dict[str, Any]]:
    rec_lookup = _recommendation_lookup(results)
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    for src_key in ("emerging_trends", "combined_top"):
        for raw in results.get(src_key) or []:
            mc = raw.get("market_capture") or {}
            if mc.get("market") and mc.get("market").upper() != market.upper():
                continue
            keyword = (raw.get("keyword") or raw.get("opportunity") or "").strip()
            if not keyword:
                continue
            norm = keyword.lower()
            if norm in seen:
                continue
            seen.add(norm)

            score = float(raw.get("bloom_score") or raw.get("signal_score") or 0)
            status = _status_for_item(raw)
            timing = raw.get("timing_window") or "6–12 months"
            start_stock, peak_label = _stocking_dates(str(timing))
            evidence_urls = raw.get("evidence_urls") or rec_lookup.get(norm, {}).get("evidence_urls") or []
            addressable = float(mc.get("addressable_revenue_chf_m") or 0)

            items.append(
                {
                    "id": _slug(keyword),
                    "rank": raw.get("combined_rank") or len(items) + 1,
                    "keyword": keyword,
                    "title": _short_label(raw.get("opportunity") or keyword, 64),
                    "subtitle": _first_seen_label(raw, rec_lookup),
                    "category_tag": _category_tag(raw),
                    "status": status,
                    "status_label": {
                        "buy_now": "Buy now",
                        "worth_testing": "Worth testing",
                        "keep_watching": "Keep watching",
                    }[status],
                    "addressable_chf_m": round(addressable, 1),
                    "market_label": "a year in Switzerland",
                    "start_stocking": start_stock,
                    "peak_label": peak_label,
                    "source_count": len(evidence_urls) or max(1, int(score * 10)),
                    "recommended_action": raw.get("recommended_action") or "",
                    "chat_prompt": f"Tell me the full story behind {keyword} — evidence, timing, and what to stock.",
                }
            )

    items.sort(key=lambda x: (-x["addressable_chf_m"], x["rank"]))
    for i, item in enumerate(items, start=1):
        item["rank"] = i
    return items[:12]


def _build_metrics(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"buy_now": 0, "worth_testing": 0, "keep_watching": 0}
    total = 0.0
    for opp in opportunities:
        counts[opp["status"]] = counts.get(opp["status"], 0) + 1
        total += opp.get("addressable_chf_m") or 0
    return {
        "opportunities_found": len(opportunities),
        "ready_to_buy": counts.get("buy_now", 0),
        "worth_testing": counts.get("worth_testing", 0),
        "keep_watching": counts.get("keep_watching", 0),
        "total_market_chf_m": round(total, 1),
    }


def _build_trend_chart(market: str, live_notice: str | None) -> dict[str, Any]:
    signals = _load_market_signals(market)
    top = signals[:4]
    if not top:
        return {"series": [], "chart_points": [], "notice": live_notice}

    series_meta: list[dict[str, Any]] = []
    trajectories: dict[str, list[dict[str, Any]]] = {}

    for i, sig in enumerate(top):
        key = _slug(sig["keyword"])
        score = sig["signal_score"]
        traj = build_trajectory(score, sig.get("notes", ""))
        trajectories[key] = traj
        series_meta.append(
            {
                "key": key,
                "label": _short_label(sig["signal_name"] or sig["keyword"]),
                "keyword": sig["keyword"],
                "color": LINE_COLORS[i % len(LINE_COLORS)],
                "current_score": round(score * 100),
                "score_math": _score_math_from_signal(score),
            }
        )

    labels = [p["label"] for p in trajectories[series_meta[0]["key"]]]
    chart_points: list[dict[str, Any]] = []
    for label in labels:
        point: dict[str, Any] = {"label": label}
        for meta in series_meta:
            key = meta["key"]
            tp = next((t for t in trajectories[key] if t["label"] == label), None)
            point[key] = round((tp["demand_index"] if tp else 0) * 100)
        chart_points.append(point)

    return {
        "series": series_meta,
        "chart_points": chart_points,
        "notice": live_notice,
    }


def fetch_dashboard(market: str = "CH") -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    market = market.upper()
    config = _load_config()
    results = _load_results()
    generated_at = results.get("generated_at")

    live = fetch_live_trends(market)
    notice = live.get("notice")
    data_source = live.get("data_source", "none")

    opportunities = _build_opportunities(results, market)
    metrics = _build_metrics(opportunities)
    trend_chart = _build_trend_chart(market, notice)

    region_label = config.get("region_group") or "DACH"
    category = (config.get("category") or "outdoor").replace("_", " ")
    sector_label = "Outdoor Retail" if "outdoor" in category.lower() else category.title()

    return {
        "market": market,
        "region_label": region_label,
        "sector_label": sector_label,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scan_date": generated_at,
        "data_source": data_source,
        "live_search": live.get("live", False),
        "notice": notice,
        "how_it_works": HOW_IT_WORKS,
        "chat_prompts": CHAT_PROMPTS,
        "metrics": metrics,
        "opportunities": opportunities,
        "trend_chart": trend_chart,
        "filters": [
            {"id": "all", "label": "All opportunities", "count": metrics["opportunities_found"]},
            {"id": "buy_now", "label": "Buy now", "count": metrics["ready_to_buy"]},
            {"id": "worth_testing", "label": "Worth testing", "count": metrics["worth_testing"]},
            {"id": "keep_watching", "label": "Keep watching", "count": metrics["keep_watching"]},
        ],
    }
