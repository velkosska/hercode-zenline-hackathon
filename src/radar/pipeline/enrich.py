from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.radar.insight.bloom_detector import find_bloom_candidates, news_and_marketplace_signals
from src.radar.insight.corroborate import assess_cluster, group_signals_by_keyword
from src.radar.insight.market_capture import enrich_recommendation_commerce
from src.radar.insight.overlap_guard import cluster_signals, merge_recommendation_themes
from src.radar.models.signal import SignalRow
from src.radar.tools.competitor import (
    aggregate_coverage,
    competitor_signals_from_search,
    seed_signals_for_keyword,
)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
FINAL_DIR = DATA_DIR / "final"
CONFIG_PATH = ROOT / "config" / "scenario.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_signals_csv(path: Path) -> list[SignalRow]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        row = {k: ("" if pd.isna(v) else v) for k, v in r.items()}
        if "signal_score" in row:
            row["signal_score"] = float(row["signal_score"])
        rows.append(SignalRow(**row))
    return rows


def _append_signals(
    enriched: list[SignalRow],
    seen_urls: set[str],
    new_rows: list[SignalRow],
) -> None:
    for row in new_rows:
        if row.url and row.url not in seen_urls:
            enriched.append(row)
            seen_urls.add(row.url)


def enrich_signals(base_signals: list[SignalRow], config: dict) -> list[SignalRow]:
    domains = config.get("competitors", ["transa.ch", "ochsnersport.ch", "decathlon.ch"])
    search_terms = config.get("competitor_search_terms", {})
    live_keywords = set(config.get("enrich_live_keywords", []))
    enriched = list(base_signals)
    seen_urls = {s.url for s in enriched if s.url}

    keywords = set(s.keyword for s in base_signals)
    for kw in keywords:
        search_kw = search_terms.get(kw, kw)
        for seed in seed_signals_for_keyword(kw):
            _append_signals(enriched, seen_urls, [seed])
        for comp in competitor_signals_from_search(search_kw, domains):
            _append_signals(enriched, seen_urls, [comp])
        if kw in live_keywords:
            marketplace_domains = list(dict.fromkeys(domains + ["galaxus.ch"]))
            for live in news_and_marketplace_signals(search_kw, domains=marketplace_domains):
                _append_signals(enriched, seen_urls, [live])

    return enriched


def update_recommendations(
    rec_path: Path,
    signals: list[SignalRow],
    config: dict,
) -> dict:
    with open(rec_path, encoding="utf-8") as f:
        data = json.load(f)

    domains = config.get("competitors", [])
    search_terms = config.get("competitor_search_terms", {})
    groups = group_signals_by_keyword(signals)
    market = config.get("market_focus", "CH")

    for rec in data.get("recommendations", []):
        kw = rec.get("keyword", "")
        cluster_signals_list = groups.get(kw.lower(), [])
        if not cluster_signals_list:
            cluster_signals_list = [s for s in signals if kw.lower() in s.keyword.lower()]

        assessment = assess_cluster(cluster_signals_list) if cluster_signals_list else {}
        search_kw = search_terms.get(kw, kw)
        coverage, cov_urls = aggregate_coverage(search_kw, domains)

        existing_urls = list(rec.get("evidence_urls", []))
        all_urls = list(dict.fromkeys(existing_urls + assessment.get("evidence_urls", []) + cov_urls))
        rec["evidence_urls"] = [u for u in all_urls if u][:10]
        rec["coverage_status"] = coverage if coverage != "absent" else rec.get("coverage_status", "unknown")

        if assessment:
            rec["confidence"] = assessment.get("confidence", rec.get("confidence", "medium"))
            if assessment.get("corroboration_score", 0) >= 0.35:
                rec["evidence_summary"] = (
                    rec.get("evidence_summary", "")
                    + f" Corroboration score {assessment['corroboration_score']}; "
                    f"source types: {', '.join(assessment.get('source_types', []))}."
                ).strip()
        enrich_recommendation_commerce(rec, market=market)

    for rec in data.get("agent_synthesis", []):
        kw = rec.get("keyword", "")
        search_kw = search_terms.get(kw, kw.split("(")[0].strip())
        cluster_signals_list = [s for s in signals if search_kw.lower()[:8] in s.keyword.lower()]
        assessment = assess_cluster(cluster_signals_list) if cluster_signals_list else {}
        coverage, cov_urls = aggregate_coverage(search_kw, domains)
        rec["coverage_status"] = coverage
        rec["evidence_urls"] = list(
            dict.fromkeys(rec.get("evidence_urls", []) + cov_urls + assessment.get("evidence_urls", []))
        )[:10]
        if assessment:
            rec["confidence"] = assessment.get("confidence", rec.get("confidence", "medium"))
        enrich_recommendation_commerce(rec, market=market)

    combined = data.get("combined_top", [])
    if combined:
        data["combined_top"] = merge_recommendation_themes(combined)
        for item in data["combined_top"]:
            enrich_recommendation_commerce(item, market=market)

    clusters = cluster_signals(signals)
    data["clusters"] = clusters
    data["tool"] = "Zenline Scout — full pipeline"
    return data


def signals_to_csv(signals: list[SignalRow], path: Path) -> None:
    rows = [s.model_dump() for s in signals]
    pd.DataFrame(rows).to_csv(path, index=False)


def run_enrich(skip_process: bool = False) -> Path:
    load_dotenv(ROOT / ".env")
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()

    if not skip_process:
        subprocess.run([sys.executable, str(ROOT / "process_trends.py")], check=True, cwd=ROOT)

    base_path = DATA_DIR / "signals.csv"
    rec_path = DATA_DIR / "recommendations.json"
    base_signals = load_signals_csv(base_path)
    enriched = enrich_signals(base_signals, config)

    enriched_data = update_recommendations(rec_path, enriched, config)

    emerging_trends, discovery_rows = find_bloom_candidates(enriched, config, enriched_data)
    market = config.get("market_focus", "CH")
    for trend in emerging_trends:
        enrich_recommendation_commerce(trend, market=market)
    enriched_data["emerging_trends"] = emerging_trends
    _append_signals(enriched, {s.url for s in enriched if s.url}, discovery_rows)

    final_signals = FINAL_DIR / "signals.csv"
    signals_to_csv(enriched, final_signals)

    final_rec = FINAL_DIR / "recommendations.json"
    with open(final_rec, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, indent=2, ensure_ascii=False)

    clusters_path = FINAL_DIR / "clusters.json"
    with open(clusters_path, "w", encoding="utf-8") as f:
        json.dump(
            {"clusters": enriched_data.get("clusters", []), "generated_at": enriched_data.get("generated_at")},
            f,
            indent=2,
            ensure_ascii=False,
        )

    return FINAL_DIR


if __name__ == "__main__":
    out = run_enrich(skip_process="--skip-process" in sys.argv)
    print(f"Enriched outputs written to {out}")
