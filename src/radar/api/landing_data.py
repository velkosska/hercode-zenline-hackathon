"""Lightweight live data for ZenScout landing page."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.radar.tools.competitor import aggregate_coverage, check_competitor_coverage
from src.radar.tools.tavily_search import search_discovery, search_web

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "config" / "scenario.yaml"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _short_label(title: str, max_len: int = 32) -> str:
    t = re.sub(r"\s+", " ", title).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _series_from_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for i, hit in enumerate(hits[:8]):
        momentum = round(max(0.35, 0.92 - i * 0.07), 2)
        series.append(
            {
                "name": _short_label(hit.get("title") or f"Signal {i + 1}"),
                "momentum": momentum,
                "url": hit.get("url", ""),
            }
        )
    return series


def _fallback_series_from_signals(market: str) -> list[dict[str, Any]]:
    """Pipeline fallback when Tavily is unavailable or over quota."""
    for path in (ROOT / "data" / "final" / "signals.csv", ROOT / "data" / "signals.csv"):
        if not path.exists():
            continue
        best: dict[str, tuple[float, str]] = {}
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("market", "").upper() != market.upper():
                    continue
                kw = (row.get("keyword") or "").strip()
                if not kw:
                    continue
                try:
                    score = float(row.get("signal_score") or 0)
                except ValueError:
                    score = 0.0
                name = _short_label(row.get("signal_name") or kw)
                if score >= best.get(kw, (0, ""))[0]:
                    best[kw] = (score, name)
        if best:
            ranked = sorted(best.values(), key=lambda x: -x[0])[:8]
            return [
                {"name": name, "momentum": round(min(1.0, score), 2), "url": ""}
                for score, name in ranked
            ]
    return []


def fetch_live_trends(market: str = "CH") -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    config = _load_config()
    region = "Switzerland" if market.upper() == "CH" else market.upper()
    queries = config.get(
        "bloom_discovery_queries",
        ["emerging outdoor trends Switzerland 2026"],
    )

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in search_discovery(queries[:2], max_results=4):
        url = hit.get("url", "")
        if url and url not in seen:
            hits.append(hit)
            seen.add(url)

    for hit in search_web(
        f"outdoor retail trend momentum {region} 2026",
        max_results=5,
        topic="news",
        time_range="month",
    ):
        url = hit.get("url", "")
        if url and url not in seen:
            hits.append(hit)
            seen.add(url)

    if hits:
        series = _series_from_hits(hits)
        return {
            "market": market.upper(),
            "live": True,
            "data_source": "tavily",
            "notice": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "series": series,
            "source_count": len(hits),
        }

    fallback = _fallback_series_from_signals(market.upper())
    notice = (
        "Tavily web search is temporarily unavailable (quota or key). "
        "Showing Scout pipeline search momentum instead."
        if fallback
        else "Could not load trends. Check TAVILY_API_KEY in .env or run make all to refresh pipeline data."
    )

    return {
        "market": market.upper(),
        "live": bool(fallback),
        "data_source": "pipeline" if fallback else "none",
        "notice": notice,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "series": fallback,
        "source_count": len(fallback),
    }


def fetch_competitor_snapshot(market: str = "CH", keyword_limit: int = 4) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    config = _load_config()
    domains = config.get("competitors", ["transa.ch", "ochsnersport.ch", "decathlon.ch"])
    keywords = config.get("seed_keywords", [])[:keyword_limit]

    rows: list[dict[str, Any]] = []
    for kw in keywords:
        retailers: dict[str, Any] = {}
        for domain in domains:
            cov = check_competitor_coverage(domain, kw)
            retailers[domain.replace("www.", "")] = {
                "status": cov.status,
                "listings": cov.listing_count,
            }
        overall, urls = aggregate_coverage(kw, domains)
        rows.append(
            {
                "keyword": kw,
                "overall": overall,
                "retailers": retailers,
                "sample_urls": urls[:3],
            }
        )

    gaps = sum(1 for r in rows if r["overall"] in ("absent", "partially_covered"))

    return {
        "market": market.upper(),
        "live": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "retailer_domains": [d.replace("www.", "") for d in domains],
        "rows": rows,
        "gap_count": gaps,
    }
