from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.radar.models.signal import SignalRow

# Manual merge map for overlapping opportunity themes
THEME_ALIASES: dict[str, str] = {
    "trailrunning": "trail_running",
    "trail running footwear": "trail_running",
    "trail running": "trail_running",
    "running": "trail_running",
    "klettersteig": "via_ferrata",
    "via ferrata starter kits": "via_ferrata",
    "vía ferrata": "via_ferrata",
    "bikepacking": "bikepacking",
    "skitour": "skitour",
    "alpha direct": "alpha_direct",
    "recycled down": "recycled_down",
    "ultralight sleeping bag": "ultralight_sleep",
    "merino / natural fiber base layers": "merino_base",
    "merino": "merino_base",
}


def normalize_theme(text: str) -> str:
    key = text.lower().strip()
    key = re.sub(r"[^a-z0-9\s/]", "", key)
    key = re.sub(r"\s+", " ", key)
    for alias, theme in THEME_ALIASES.items():
        if alias in key or key in alias:
            return theme
    return re.sub(r"\s+", "_", key)[:40]


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_theme(a), normalize_theme(b)).ratio()


def cluster_signals(signals: list[SignalRow], threshold: float = 0.55) -> list[dict]:
    """Group signals into opportunity themes (Overlap Guard)."""
    assigned: dict[int, str] = {}
    clusters: dict[str, list[SignalRow]] = {}

    for i, signal in enumerate(signals):
        theme = normalize_theme(signal.keyword or signal.signal_name)
        merged = False
        for existing_theme in list(clusters.keys()):
            if similarity(theme, existing_theme) >= threshold:
                clusters[existing_theme].append(signal)
                assigned[i] = existing_theme
                merged = True
                break
        if not merged:
            clusters[theme] = [signal]
            assigned[i] = theme

    output = []
    for theme, members in clusters.items():
        keywords = sorted({m.keyword for m in members})
        sources = sorted({m.source for m in members})
        types = sorted({m.signal_type for m in members})
        urls = [m.url for m in members if m.url]
        overlap_warning = len(keywords) > 1 or len({m.signal_name for m in members}) > 2
        output.append(
            {
                "theme_id": theme,
                "display_name": keywords[0] if keywords else theme.replace("_", " ").title(),
                "keywords": keywords,
                "signal_count": len(members),
                "sources": sources,
                "source_types": types,
                "evidence_urls": list(dict.fromkeys(urls))[:10],
                "overlap_warning": overlap_warning,
                "overlap_note": (
                    "Multiple related keywords detected — consolidate buying decision to avoid cannibalization."
                    if overlap_warning
                    else "Single coherent theme."
                ),
                "member_signals": [
                    {
                        "keyword": m.keyword,
                        "signal_name": m.signal_name,
                        "source": m.source,
                        "signal_type": m.signal_type,
                        "url": m.url,
                    }
                    for m in members[:15]
                ],
            }
        )

    output.sort(key=lambda c: c["signal_count"], reverse=True)
    return output


def merge_recommendation_themes(recommendations: list[dict]) -> list[dict]:
    """Collapse duplicate recommendation themes for combined_top display."""
    seen: dict[str, dict] = {}
    for rec in recommendations:
        theme = normalize_theme(rec.get("keyword") or rec.get("opportunity", ""))
        if theme not in seen or rec.get("signal_score", 0) > seen[theme].get("signal_score", 0):
            seen[theme] = rec
    merged = sorted(seen.values(), key=lambda r: r.get("signal_score", 0), reverse=True)
    for i, rec in enumerate(merged):
        rec["combined_rank"] = i + 1
    return merged
