from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
BUNDLES_PATH = ROOT / "config" / "assortment_bundles.yaml"

MARKET_TAM_CHF_M = {
    "CH": 220.0,
    "DACH": 620.0,
    "US": 1100.0,
}

CATEGORY_TAM_SHARE = {
    "trailrunning": 0.18,
    "trail running": 0.18,
    "klettersteig": 0.05,
    "via ferrata": 0.05,
    "bikepacking": 0.08,
    "skitour": 0.12,
    "packrafting": 0.01,
    "merino": 0.04,
    "ultralight": 0.06,
    "alpha direct": 0.02,
    "recycled down": 0.03,
    "quiet outdoors": 0.07,
    "default": 0.04,
}

CAPTURE_BY_COVERAGE = {
    "absent": 0.14,
    "partially_covered": 0.09,
    "unknown": 0.07,
    "covered": 0.04,
    "not_relevant": 0.02,
}


def load_assortment_bundles() -> dict[str, Any]:
    if not BUNDLES_PATH.exists():
        return {}
    with open(BUNDLES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _category_share(keyword: str) -> float:
    key = keyword.lower()
    for pattern, share in CATEGORY_TAM_SHARE.items():
        if pattern in key or key in pattern:
            return share
    return CATEGORY_TAM_SHARE["default"]


def _match_bundle_key(keyword: str, bundles: dict) -> str | None:
    key = keyword.lower()
    for bundle_key in bundles:
        bk = bundle_key.lower()
        if bk in key or key in bk:
            return bundle_key
        if key.split() and bk.split() and key.split()[0] == bk.split()[0] and len(key.split()[0]) > 4:
            return bundle_key
    return None


def assortment_for_keyword(keyword: str) -> dict[str, Any]:
    bundles = load_assortment_bundles()
    match = _match_bundle_key(keyword, bundles)
    if match:
        return bundles[match]
    return {"assortment_items": [], "opportunity_label": keyword}


def estimate_market_capture(
    keyword: str,
    market: str,
    signal_score: float,
    coverage_status: str,
) -> dict[str, Any]:
    market = market.upper()
    tam_total = MARKET_TAM_CHF_M.get(market, MARKET_TAM_CHF_M["CH"])
    category_share = _category_share(keyword)
    category_tam = round(tam_total * category_share, 1)
    base_capture = CAPTURE_BY_COVERAGE.get(coverage_status, 0.07)
    capture_rate = round(min(0.20, base_capture * (0.7 + 0.3 * signal_score)), 3)
    addressable = round(category_tam * capture_rate, 1)
    return {
        "market": market,
        "tam_total_chf_m": tam_total,
        "category_tam_chf_m": category_tam,
        "category_share_pct": round(category_share * 100, 1),
        "estimated_capture_rate_pct": round(capture_rate * 100, 1),
        "addressable_revenue_chf_m": addressable,
        "methodology_note": (
            "Heuristic from Swiss outdoor market report; category share from signal; "
            "capture rate scales with coverage gap. Production Zenline merges POS/margin."
        ),
    }


def enrich_recommendation_commerce(rec: dict, market: str = "CH") -> dict:
    keyword = rec.get("keyword", "")
    bundle = assortment_for_keyword(keyword)
    if bundle.get("assortment_items"):
        rec["assortment_items"] = bundle["assortment_items"]
    rec["market_capture"] = estimate_market_capture(
        keyword,
        market,
        float(rec.get("signal_score", 0.5)),
        rec.get("coverage_status", "unknown"),
    )
    return rec


def recapture_for_market(rec: dict, market: str) -> dict:
    """Recompute market_capture when user selects a different market in dashboard."""
    out = dict(rec)
    out["market_capture"] = estimate_market_capture(
        rec.get("keyword", ""),
        market,
        float(rec.get("signal_score", 0.5)),
        rec.get("coverage_status", "unknown"),
    )
    return out
