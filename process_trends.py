#!/usr/bin/env python3
"""
Process trends_raw/ → structured Scout outputs.

Reads Google Trends exports (weekly time series + optional region breakdowns),
computes search velocity, YoY change, and CH vs US transfer gap, then writes:

  data/trends_metrics.csv   — one row per keyword (analyzer view)
  data/signals.csv          — hackathon signal contract rows
  data/recommendations.json — ranked opportunities from search signals

Usage:
    python process_trends.py
    python process_trends.py --raw-dir trends_raw --out-dir data
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import pandas as pd

RAW_DIR = Path("trends_raw")
OUT_DIR = Path("data")
OBSERVED_AT = date.today().isoformat()

# Human-readable opportunity metadata per scraped keyword
OPPORTUNITY_META: dict[str, dict] = {
    "Trailrunning": {
        "signal_name": "Trail running search momentum",
        "opportunity": "Expand trail running shoe wall and summer trail apparel",
        "action_core": "Merchandise dedicated trail running bay with gait-analysis service",
        "action_experimental": "Test-buy top 8 trail/gravel hybrid SKUs for SS26",
        "risks": "Seasonal spike may fade after summer; verify sell-through vs road running",
    },
    "bikepacking": {
        "signal_name": "Bikepacking interest",
        "opportunity": "Bikepacking bags, ultralight camping crossover, and gravel-adjacent kit",
        "action_core": "Create bikepacking starter capsule (pack, tent, sleep system) in bike corners",
        "action_experimental": "Pilot rental or test-buy in Zürich/Bern stores",
        "risks": "Niche audience; needs staff education to avoid confusion with touring",
    },
    "Klettersteig": {
        "signal_name": "Via ferrata (Klettersteig) seasonal demand",
        "opportunity": "Via ferrata harnesses, lanyards, helmets, and alpine access kit",
        "action_core": "Seasonal shop-in-shop May–September in alpine-adjacent stores",
        "action_experimental": "Bundle via ferrata starter sets with SAC partnership",
        "risks": "Highly seasonal; inventory timing critical",
    },
    "Skitour": {
        "signal_name": "Ski touring (Skitour) demand",
        "opportunity": "Ski touring boots, bindings, skins, and safety equipment",
        "action_core": "Plan AW26 buy based on Nov–Mar search curve; core in mountain regions",
        "action_experimental": "Monitor only until Q4 pre-season",
        "risks": "Off-season in June; signal is winter-forward",
    },
    "Alpha Direct": {
        "signal_name": "Alpha Direct insulation material curiosity",
        "opportunity": "Premium synthetic insulation (Alpha Direct) in ultralight mid-layers",
        "action_core": "Monitor — US-led niche material, sparse CH search volume",
        "action_experimental": "Test 3–5 Alpha Direct mid-layers if supplier access confirmed",
        "risks": "Very low CH search volume; trend may stay enthusiast-only",
    },
    "recycled down": {
        "signal_name": "Recycled down sustainability interest",
        "opportunity": "Recycled down jackets and sleeping bags for sustainability positioning",
        "action_core": "Tag and filter recycled-down SKUs; staff sustainability storytelling",
        "action_experimental": "Monitor — CH data is regional-only, insufficient time series",
        "risks": "Low search volume in CH; rely on assortment audit not search alone",
    },
    "ultralight sleeping bag": {
        "signal_name": "Ultralight sleeping bag demand",
        "opportunity": "Sub-kilo sleep systems for fast alpine and bikepacking customers",
        "action_core": "Curate ultralight sleep system bay linked to fast-hiking narrative",
        "action_experimental": "Monitor — CH export is regional breakdown only",
        "risks": "Sparse CH time series; corroborate with product sales if available",
    },
}


@dataclass
class TrendMetrics:
    keyword: str
    market: str
    format: str  # weekly | region
    data_points: int
    recent_12w_mean: float | None
    prior_12w_mean: float | None
    velocity_pct: float | None
    yoy_pct: float | None
    last_value: float | None
    peak_52w: float | None
    nonzero_weeks_52w: int | None
    top_regions: str | None
    source_file: str


@dataclass
class KeywordAnalysis:
    keyword: str
    ch: TrendMetrics | None
    us: TrendMetrics | None
    transfer_gap: float | None
    ch_momentum: float | None
    us_momentum: float | None
    signal_score: float
    confidence: str
    transferability: str
    coverage_status: str
    recommended_action: str
    range_tag: str  # core | premium | experimental | monitor
    first_observed_market: str
    notes: str


def parse_filename(path: Path) -> tuple[str, str] | None:
    """Parse keyword__GEO.csv naming convention."""
    stem = path.stem
    if stem.startswith("time_series"):
        return None
    if "__" not in stem:
        return None
    keyword, geo = stem.rsplit("__", 1)
    return keyword.replace("_", " "), geo.upper()


def _detect_format(df: pd.DataFrame) -> str:
    if df.empty:
        return "unknown"
    col0 = str(df.columns[0]).lower()
    if col0 == "week":
        return "weekly"
    if col0 == "region":
        return "region"
    if col0 == "time":
        return "monthly_multi"
    return "unknown"


def load_weekly_csv(path: Path) -> pd.DataFrame | None:
    """Load Google Trends weekly export → date, value."""
    try:
        raw = pd.read_csv(path, skiprows=1)
    except Exception:
        return None
    if _detect_format(raw) != "weekly":
        return None
    date_col = raw.columns[0]
    value_col = raw.columns[1]
    df = raw[[date_col, value_col]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"]).sort_values("date")
    return df


def load_region_csv(path: Path) -> list[tuple[str, float]]:
    try:
        raw = pd.read_csv(path, skiprows=1)
    except Exception:
        return []
    if _detect_format(raw) != "region":
        return []
    value_col = raw.columns[1]
    regions: list[tuple[str, float]] = []
    for _, row in raw.iterrows():
        name = str(row.iloc[0]).strip()
        val = pd.to_numeric(row.iloc[1], errors="coerce")
        if pd.notna(val) and val > 0:
            regions.append((name, float(val)))
    regions.sort(key=lambda x: x[1], reverse=True)
    return regions


def compute_weekly_metrics(keyword: str, market: str, path: Path, df: pd.DataFrame) -> TrendMetrics:
    values = df["value"]
    recent = values.tail(12)
    prior = values.iloc[-24:-12] if len(values) >= 24 else values.iloc[:12]
    yoy_cur = values.tail(12)
    yoy_prev = values.iloc[-64:-52] if len(values) >= 64 else pd.Series(dtype=float)

    recent_mean = float(recent.mean())
    prior_mean = float(prior.mean()) if len(prior) else 0.0
    yoy_cur_mean = float(yoy_cur.mean())
    yoy_prev_mean = float(yoy_prev.mean()) if len(yoy_prev) else 0.0

    velocity = ((recent_mean - prior_mean) / max(prior_mean, 1.0)) * 100 if len(prior) else None
    yoy = ((yoy_cur_mean - yoy_prev_mean) / max(yoy_prev_mean, 1.0)) * 100 if len(yoy_prev) else None

    tail_52 = values.tail(52)
    nonzero = int((tail_52 > 0).sum())

    return TrendMetrics(
        keyword=keyword,
        market=market,
        format="weekly",
        data_points=len(df),
        recent_12w_mean=round(recent_mean, 2),
        prior_12w_mean=round(prior_mean, 2),
        velocity_pct=round(velocity, 1) if velocity is not None else None,
        yoy_pct=round(yoy, 1) if yoy is not None else None,
        last_value=float(values.iloc[-1]) if len(values) else None,
        peak_52w=float(tail_52.max()) if len(tail_52) else None,
        nonzero_weeks_52w=nonzero,
        top_regions=None,
        source_file=str(path),
    )


def compute_region_metrics(keyword: str, market: str, path: Path, regions: list[tuple[str, float]]) -> TrendMetrics:
    top = ", ".join(f"{n} ({v:.0f})" for n, v in regions[:3])
    return TrendMetrics(
        keyword=keyword,
        market=market,
        format="region",
        data_points=len(regions),
        recent_12w_mean=None,
        prior_12w_mean=None,
        velocity_pct=None,
        yoy_pct=None,
        last_value=regions[0][1] if regions else None,
        peak_52w=None,
        nonzero_weeks_52w=None,
        top_regions=top or None,
        source_file=str(path),
    )


def load_metrics(path: Path) -> TrendMetrics | None:
    parsed = parse_filename(path)
    if not parsed:
        return None
    keyword, geo = parsed

    weekly = load_weekly_csv(path)
    if weekly is not None and len(weekly) > 0:
        return compute_weekly_metrics(keyword, geo, path, weekly)

    regions = load_region_csv(path)
    if regions:
        return compute_region_metrics(keyword, geo, path, regions)

    return None


def momentum_score(velocity: float | None) -> float:
    if velocity is None:
        return 0.0
    return max(0.0, min(1.0, (velocity + 20) / 80))  # -20%→0, +60%→1


def level_score(mean: float | None) -> float:
    if mean is None:
        return 0.0
    return max(0.0, min(1.0, mean / 100))


def confidence_label(ch: TrendMetrics | None, us: TrendMetrics | None) -> str:
    if ch and ch.format == "weekly" and (ch.nonzero_weeks_52w or 0) >= 30:
        if us and us.format == "weekly":
            return "high"
        return "medium"
    if ch and ch.format == "weekly" and (ch.nonzero_weeks_52w or 0) >= 15:
        return "medium"
    if ch and ch.format == "region":
        return "low"
    return "low"


def analyze_keyword(keyword: str, ch: TrendMetrics | None, us: TrendMetrics | None) -> KeywordAnalysis:
    meta = OPPORTUNITY_META.get(keyword, {})
    ch_vel = ch.velocity_pct if ch else None
    us_vel = us.velocity_pct if us else None
    transfer_gap = None
    if ch_vel is not None and us_vel is not None:
        transfer_gap = round(us_vel - ch_vel, 1)

    ch_mom = momentum_score(ch_vel)
    us_mom = momentum_score(us_vel)
    ch_lvl = level_score(ch.recent_12w_mean if ch else None)

    # Composite: CH momentum + level + transfer opportunity
    transfer_bonus = 0.0
    if transfer_gap is not None and transfer_gap > 10:
        transfer_bonus = min(0.25, transfer_gap / 120)
    elif ch_mom > us_mom and ch_mom > 0.5:
        transfer_bonus = 0.15  # local Swiss surge

    signal_score = round(
        min(1.0, 0.45 * ch_mom + 0.35 * ch_lvl + 0.20 * us_mom + transfer_bonus),
        3,
    )

    conf = confidence_label(ch, us)

    # Transferability narrative
    if ch and ch.format == "weekly" and (ch.recent_12w_mean or 0) >= 40:
        transferability = (
            f"Strong active CH search interest (12w avg {ch.recent_12w_mean:.0f}/100). "
            "Suitable for Swiss outdoor retailers this season."
        )
        coverage = "partially_covered"
        range_tag = "core"
    elif transfer_gap is not None and transfer_gap > 15:
        transferability = (
            f"US search momentum leads CH by {transfer_gap:.0f}pp — early transfer candidate "
            "if assortment gap confirmed at Transa/Ochsner."
        )
        coverage = "unknown"
        range_tag = "experimental"
    elif ch and ch.format == "region":
        transferability = (
            f"Low-volume CH signal; interest detected in {ch.top_regions or 'select cantons'}. "
            "Needs competitor assortment corroboration."
        )
        coverage = "unknown"
        range_tag = "monitor"
    else:
        transferability = "Moderate CH search signal; validate with competitor scans before buy."
        coverage = "unknown"
        range_tag = "experimental" if signal_score >= 0.45 else "monitor"

    first_market = "US" if us_mom > ch_mom + 0.15 else "CH"

    if range_tag == "core":
        action = meta.get("action_core", "Expand core assortment and in-store visibility")
    elif range_tag == "experimental":
        action = meta.get("action_experimental", "Pilot test-buy in 1–2 stores")
    else:
        action = meta.get("action_core", "Monitor and research further")

    notes_parts = []
    if ch:
        if ch.format == "weekly":
            notes_parts.append(
                f"CH 12w avg={ch.recent_12w_mean}, velocity={ch.velocity_pct}%, YoY={ch.yoy_pct}%"
            )
        else:
            notes_parts.append(f"CH regional signal: {ch.top_regions}")
    if us and us.format == "weekly":
        notes_parts.append(f"US 12w avg={us.recent_12w_mean}, velocity={us.velocity_pct}%")
    if transfer_gap is not None:
        notes_parts.append(f"US-CH velocity gap={transfer_gap}pp")
    notes_parts.append("Google Trends index 0–100; values <1 shown as 0 by Google.")

    return KeywordAnalysis(
        keyword=keyword,
        ch=ch,
        us=us,
        transfer_gap=transfer_gap,
        ch_momentum=round(ch_mom, 3),
        us_momentum=round(us_mom, 3),
        signal_score=signal_score,
        confidence=conf,
        transferability=transferability,
        coverage_status=coverage,
        recommended_action=action,
        range_tag=range_tag,
        first_observed_market=first_market,
        notes="; ".join(notes_parts),
    )


def metrics_to_signal_rows(m: TrendMetrics, analysis: KeywordAnalysis | None = None) -> list[dict]:
    meta = OPPORTUNITY_META.get(m.keyword, {})
    signal_name = meta.get("signal_name", f"{m.keyword} search trend")
    score = analysis.signal_score if analysis else level_score(m.recent_12w_mean)
    conf = analysis.confidence if analysis else "low"

    if m.format == "weekly":
        note = (
            f"12w mean={m.recent_12w_mean}, velocity={m.velocity_pct}%, "
            f"YoY={m.yoy_pct}%, peak_52w={m.peak_52w}"
        )
    else:
        note = f"Regional breakdown: {m.top_regions or 'sparse'}"

    trends_url = (
        f"https://trends.google.com/trends/explore?date=today%205-y&geo={m.market}&q="
        + m.keyword.replace(" ", "%20")
    )

    return [{
        "source": "Google Trends",
        "market": m.market,
        "keyword": m.keyword,
        "signal_name": signal_name,
        "signal_type": "search",
        "product_name": "",
        "brand": "",
        "price": "",
        "rank": "",
        "url": trends_url,
        "signal_score": score,
        "confidence": conf,
        "notes": note,
        "observed_at": OBSERVED_AT,
        "artifact_type": "csv",
        "artifact_uri": m.source_file,
        "created_by_tool": "process_trends.py",
    }]


def analysis_to_recommendation(rank: int, a: KeywordAnalysis) -> dict:
    meta = OPPORTUNITY_META.get(a.keyword, {})
    ch = a.ch
    us = a.us
    urls = []
    if ch:
        urls.append(
            f"https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q="
            + a.keyword.replace(" ", "%20")
        )
    if us:
        urls.append(
            f"https://trends.google.com/trends/explore?date=today%205-y&geo=US&q="
            + a.keyword.replace(" ", "%20")
        )

    evidence = []
    if ch and ch.format == "weekly":
        evidence.append(f"CH search 12w avg {ch.recent_12w_mean}/100, velocity {ch.velocity_pct}%")
    if us and us.format == "weekly":
        evidence.append(f"US search 12w avg {us.recent_12w_mean}/100, velocity {us.velocity_pct}%")
    if a.transfer_gap is not None:
        evidence.append(f"US-CH velocity gap {a.transfer_gap}pp")

    return {
        "rank": rank,
        "opportunity": meta.get("opportunity", a.keyword),
        "keyword": a.keyword,
        "first_observed_market": a.first_observed_market,
        "evidence_summary": ". ".join(evidence) + ".",
        "evidence_urls": urls,
        "transferability": a.transferability,
        "coverage_status": a.coverage_status,
        "recommended_action": a.recommended_action,
        "range_tag": a.range_tag,
        "confidence": a.confidence,
        "signal_score": a.signal_score,
        "risks": meta.get("risks", "Search-only signal; corroborate with competitor assortment."),
        "scout_module": "Scout",
    }


def _geo_from_time_series_path(path: Path) -> str:
    name = path.name.upper()
    if "_US_" in name or name.startswith("TIME_SERIES_US"):
        return "US"
    if "_CH_" in name or name.startswith("TIME_SERIES_CH"):
        return "CH"
    return "CH"


def _stage_to_confidence(stage: str) -> tuple[str, float]:
    s = stage.lower()
    if any(x in s for x in ("market proof", "strong & growing", "strong (maturing)", "strong")):
        return "high", 0.88
    if any(x in s for x in ("growing", "early adoption")):
        return "medium", 0.72
    if "weak to growing" in s:
        return "low", 0.55
    return "low", 0.45


def _agent_to_signal_type(agent: str) -> str:
    a = agent.lower()
    if "youtube" in a or "tiktok" in a:
        return "social"
    if "market" in a or "synthesis" in a:
        return "web"
    return "manual"


def load_swiss_outdoor_trends(path: Path) -> tuple[list[dict], list[dict]]:
    """Parse agent-curated swiss_outdoor_trends.csv → signals + synthesis recommendations."""
    try:
        df = pd.read_csv(path)
    except Exception:
        return [], []

    required = {"Agent", "Trend", "Signal_Stage", "Key_Evidence", "Product_Category",
                "Retail_Action", "Timing_Window"}
    if not required.issubset(set(df.columns)):
        return [], []

    signals: list[dict] = []
    synth_recs: list[dict] = []

    for _, row in df.iterrows():
        agent = str(row["Agent"]).strip()
        trend = str(row["Trend"]).strip()
        stage = str(row["Signal_Stage"]).strip()
        evidence = str(row["Key_Evidence"]).strip()
        category = str(row["Product_Category"]).strip()
        action = str(row["Retail_Action"]).strip()
        timing = str(row["Timing_Window"]).strip()

        conf, score = _stage_to_confidence(stage)
        is_synthesis = agent.lower().startswith("synthesis")
        keyword = trend.split("(")[0].strip()

        signal_row = {
            "source": agent if not is_synthesis else "Agent Synthesis",
            "market": "CH",
            "keyword": keyword,
            "signal_name": trend,
            "signal_type": _agent_to_signal_type(agent),
            "product_name": category,
            "brand": "",
            "price": "",
            "rank": "",
            "url": "",
            "signal_score": score,
            "confidence": conf,
            "notes": f"{stage}. {evidence[:200]}. Timing: {timing}. Action: {action[:120]}",
            "observed_at": OBSERVED_AT,
            "artifact_type": "csv",
            "artifact_uri": str(path),
            "created_by_tool": "process_trends.py",
        }
        signals.append(signal_row)

        if is_synthesis:
            rank_match = re.search(r"Rank\s*(\d+)", agent, re.I)
            dark = "dark horse" in agent.lower()
            synth_recs.append({
                "rank": int(rank_match.group(1)) if rank_match else len(synth_recs) + 1,
                "opportunity": trend,
                "keyword": keyword,
                "first_observed_market": "CH",
                "evidence_summary": evidence,
                "evidence_urls": [],
                "transferability": f"Swiss/DACH focused. Stage: {stage}. Window: {timing}.",
                "coverage_status": "unknown",
                "recommended_action": action,
                "range_tag": "core" if conf == "high" else "experimental" if conf == "medium" else "monitor",
                "confidence": conf,
                "signal_score": score,
                "risks": "Qualitative agent signal — corroborate with search trends and retailer assortment.",
                "scout_module": "Scout + Agent Synthesis",
                "synthesis_label": "Dark Horse" if dark else f"Rank {rank_match.group(1) if rank_match else '?'}",
            })

    synth_recs.sort(key=lambda r: r["rank"])
    return signals, synth_recs


def load_multi_keyword_monthly(path: Path) -> list[dict]:
    """Parse time_series_{GEO}_*.csv multi-keyword monthly exports."""
    try:
        df = pd.read_csv(path)
    except Exception:
        return []

    if "Time" not in df.columns:
        return []

    geo = _geo_from_time_series_path(path)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"]).sort_values("Time")
    if len(df) < 13:
        return []

    signals = []
    channel = "google search"
    if "news" in path.name:
        channel = "google news"
    elif "shopping" in path.name:
        channel = "google shopping"

    for col in df.columns:
        if col == "Time":
            continue
        series = pd.to_numeric(df[col], errors="coerce").fillna(0)
        recent = float(series.tail(3).mean())
        prior = float(series.iloc[-15:-12].mean()) if len(series) >= 15 else float(series.head(3).mean())
        velocity = ((recent - prior) / max(prior, 1)) * 100

        signals.append({
            "source": f"Google Trends ({channel})",
            "market": geo,
            "keyword": col,
            "signal_name": f"{col} {geo} search interest ({channel})",
            "signal_type": "search",
            "product_name": "",
            "brand": "",
            "price": "",
            "rank": "",
            "url": f"https://trends.google.com/trends/explore?date=today%205-y&geo={geo}&q={col.replace(' ', '%20')}",
            "signal_score": round(min(1.0, 0.5 * level_score(recent) + 0.5 * momentum_score(velocity)), 3),
            "confidence": "medium",
            "notes": f"Monthly {geo} index, 3m avg={recent:.0f}, velocity={velocity:.1f}% via {path.name}",
            "observed_at": OBSERVED_AT,
            "artifact_type": "csv",
            "artifact_uri": str(path),
            "created_by_tool": "process_trends.py",
        })
    return signals


def _build_combined_top(
    analyses: list[KeywordAnalysis],
    agent_synthesis: list[dict],
    limit: int = 8,
) -> list[dict]:
    """Merge trend-based and agent synthesis picks for demo ranking."""
    combined: list[dict] = []
    for a in analyses[:5]:
        combined.append({
            "source": "Google Trends",
            "opportunity": OPPORTUNITY_META.get(a.keyword, {}).get("opportunity", a.keyword),
            "keyword": a.keyword,
            "signal_score": a.signal_score,
            "confidence": a.confidence,
            "recommended_action": a.recommended_action,
        })
    for s in agent_synthesis:
        if s.get("synthesis_label", "").startswith("Rank"):
            combined.append({
                "source": "Agent Synthesis",
                "opportunity": s["opportunity"],
                "keyword": s["keyword"],
                "signal_score": s["signal_score"],
                "confidence": s["confidence"],
                "recommended_action": s["recommended_action"],
            })
    combined.sort(key=lambda x: x["signal_score"], reverse=True)
    for i, item in enumerate(combined[:limit]):
        item["combined_rank"] = i + 1
    return combined[:limit]


def run(raw_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    by_keyword: dict[str, dict[str, TrendMetrics]] = {}
    all_metrics: list[TrendMetrics] = []

    for path in sorted(raw_dir.glob("*.csv")):
        m = load_metrics(path)
        if m:
            by_keyword.setdefault(m.keyword, {})[m.market] = m
            all_metrics.append(m)

    analyses: list[KeywordAnalysis] = []
    for keyword in sorted(by_keyword.keys()):
        markets = by_keyword[keyword]
        analyses.append(analyze_keyword(keyword, markets.get("CH"), markets.get("US")))

    analyses.sort(key=lambda a: a.signal_score, reverse=True)

    agent_signals: list[dict] = []
    agent_synthesis: list[dict] = []

    # trends_metrics.csv
    metric_rows = []
    for m in all_metrics:
        row = asdict(m)
        metric_rows.append(row)
    pd.DataFrame(metric_rows).to_csv(out_dir / "trends_metrics.csv", index=False)

    # signals.csv
    signal_rows: list[dict] = []
    analysis_map = {a.keyword: a for a in analyses}
    for m in all_metrics:
        signal_rows.extend(metrics_to_signal_rows(m, analysis_map.get(m.keyword)))

    for path in sorted(raw_dir.glob("time_series_*.csv")):
        signal_rows.extend(load_multi_keyword_monthly(path))

    swiss_path = raw_dir / "swiss_outdoor_trends.csv"
    if swiss_path.exists():
        agent_signals, agent_synthesis = load_swiss_outdoor_trends(swiss_path)
        signal_rows.extend(agent_signals)

    signal_cols = [
        "source", "market", "keyword", "signal_name", "signal_type",
        "product_name", "brand", "price", "rank", "url", "signal_score",
        "confidence", "notes", "observed_at", "artifact_type", "artifact_uri",
        "created_by_tool",
    ]
    pd.DataFrame(signal_rows)[signal_cols].to_csv(out_dir / "signals.csv", index=False)

    # recommendations.json
    recommendations = {
        "generated_at": OBSERVED_AT,
        "tool": "Zenline Scout — process_trends.py",
        "methodology": {
            "signal_score": "0.45*CH_momentum + 0.35*CH_level + 0.20*US_momentum + transfer_bonus",
            "velocity": "12-week mean vs prior 12 weeks",
            "transfer_gap": "US velocity % minus CH velocity %",
            "confidence": "high if CH weekly with 30+ non-zero weeks in last 52",
        },
        "recommendations": [
            analysis_to_recommendation(i + 1, a) for i, a in enumerate(analyses)
        ],
        "agent_synthesis": agent_synthesis,
        "combined_top": _build_combined_top(analyses, agent_synthesis),
    }
    with open(out_dir / "recommendations.json", "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)

    # Summary markdown for business team
    lines = [
        "# Trends Analysis Summary",
        f"Generated: {OBSERVED_AT}",
        "",
        "## Top opportunities (search signals only)",
        "",
        "| Rank | Keyword | Score | Confidence | Range | CH 12w avg | Velocity |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, a in enumerate(analyses[:7]):
        ch_avg = a.ch.recent_12w_mean if a.ch and a.ch.format == "weekly" else "—"
        ch_vel = a.ch.velocity_pct if a.ch and a.ch.format == "weekly" else "—"
        lines.append(
            f"| {i+1} | {a.keyword} | {a.signal_score} | {a.confidence} | "
            f"{a.range_tag} | {ch_avg} | {ch_vel} |"
        )
    lines.extend([
        "",
        "## Agent synthesis (swiss_outdoor_trends.csv)",
        "",
    ])
    if agent_synthesis:
        lines.append("| Rank | Opportunity | Confidence | Action |")
        lines.append("| --- | --- | --- | --- |")
        for s in agent_synthesis:
            action = s["recommended_action"][:60] + "…" if len(s["recommended_action"]) > 60 else s["recommended_action"]
            lines.append(f"| {s['rank']} | {s['opportunity'][:50]} | {s['confidence']} | {action} |")
    else:
        lines.append("_No swiss_outdoor_trends.csv found._")
    lines.extend([
        "",
        "## Outputs",
        f"- `{out_dir / 'trends_metrics.csv'}` — raw metrics per keyword file",
        f"- `{out_dir / 'signals.csv'}` — hackathon signal contract ({len(signal_rows)} rows)",
        f"- `{out_dir / 'recommendations.json'}` — trends + agent_synthesis + combined_top",
        "",
        "**Next step:** corroborate top 3 with Transa/Ochsner URLs before final demo.",
    ])
    (out_dir / "trends_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Processed {len(all_metrics)} trend files → {len(analyses)} keywords")
    print(f"Agent signals: {len(agent_signals)} rows, synthesis ranks: {len(agent_synthesis)}")
    print(f"Wrote {out_dir / 'signals.csv'} ({len(signal_rows)} rows)")
    print(f"Wrote {out_dir / 'recommendations.json'} ({len(analyses)} trend + {len(agent_synthesis)} synthesis)")
    print("\nTop 5 by signal_score:")
    for a in analyses[:5]:
        ch_info = ""
        if a.ch and a.ch.format == "weekly":
            ch_info = f" CH avg={a.ch.recent_12w_mean} vel={a.ch.velocity_pct}%"
        print(f"  {a.signal_score:.3f}  {a.keyword} ({a.confidence}, {a.range_tag}){ch_info}")


def main():
    parser = argparse.ArgumentParser(description="Process Google Trends raw exports")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    run(args.raw_dir, args.out_dir)


if __name__ == "__main__":
    main()
