from __future__ import annotations

from dataclasses import dataclass

from src.radar.models.signal import SignalRow
from src.radar.tools.tavily_search import search_site

# Curated fallback URLs — demo-safe when Tavily unavailable
SEED_URLS: dict[str, list[dict[str, str]]] = {
    "trailrunning": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/b/trailrunning/",
            "notes": "Transa trail running category",
        },
        {
            "source": "swisspo",
            "url": "https://swisspo.ch/de/erfolgreicher-winter-und-chancen-im-sommer-sportartikel-branche-beweist-stabilitaet-und-anpassungsfaehigkeit/",
            "notes": "Swiss retailers expect hiking + running shoes this summer",
        },
    ],
    "trail running footwear": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/b/trailrunning/",
            "notes": "Trail running assortment at Transa",
        },
    ],
    "bikepacking": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/b/bikepacking/",
            "notes": "Transa bikepacking category",
        },
    ],
    "klettersteig": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/b/klettersteig/",
            "notes": "Via ferrata / Klettersteig at Transa",
        },
    ],
    "skitour": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/b/skitour/",
            "notes": "Ski touring at Transa",
        },
    ],
    "via ferrata starter kits": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/p/salomon-gravel-skin-4-set-357211-002/",
            "notes": "Example alpine accessory listing; verify via ferrata kit bay separately",
        },
    ],
    "merino": [
        {
            "source": "transa.ch",
            "url": "https://www.transa.ch/de/blog/nachhaltigkeit/pfas-faq/",
            "notes": "Transa sustainability / material positioning",
        },
    ],
}


@dataclass
class CoverageResult:
    status: str
    listing_count: int
    sample_urls: list[str]


def _normalize_key(text: str) -> str:
    return text.lower().strip().replace("_", " ")


def check_competitor_coverage(domain: str, keyword: str) -> CoverageResult:
    results = search_site(domain, keyword, max_results=5)
    urls = [r.get("url", "") for r in results if r.get("url")]
    count = len(urls)
    if count >= 5:
        status = "covered"
    elif count >= 1:
        status = "partially_covered"
    else:
        status = "absent"
    return CoverageResult(status=status, listing_count=count, sample_urls=urls[:3])


def aggregate_coverage(keyword: str, domains: list[str]) -> tuple[str, list[str]]:
    all_urls: list[str] = []
    statuses: list[str] = []
    for domain in domains:
        cov = check_competitor_coverage(domain, keyword)
        statuses.append(cov.status)
        all_urls.extend(cov.sample_urls)

    if not statuses or all(s == "absent" for s in statuses):
        combined = "absent" if not all_urls else "partially_covered"
    elif all(s == "covered" for s in statuses):
        combined = "covered"
    else:
        combined = "partially_covered"

    return combined, list(dict.fromkeys(all_urls))


def seed_signals_for_keyword(keyword: str, market: str = "CH") -> list[SignalRow]:
    key = _normalize_key(keyword)
    rows: list[SignalRow] = []
    for seed_key, entries in SEED_URLS.items():
        if seed_key not in key and key not in seed_key:
            continue
        for entry in entries:
            rows.append(
                SignalRow(
                    source=entry["source"],
                    market=market,
                    keyword=keyword,
                    signal_name=f"CH competitor / trade signal: {keyword}",
                    signal_type="competitor",
                    url=entry["url"],
                    signal_score=0.7,
                    confidence="medium",
                    notes=entry["notes"],
                    observed_at="2026-06-19",
                    artifact_type="web",
                    artifact_uri=entry["url"],
                    created_by_tool="competitor_seed",
                )
            )
    return rows


def competitor_signals_from_search(
    keyword: str,
    domains: list[str],
    market: str = "CH",
) -> list[SignalRow]:
    rows: list[SignalRow] = []
    for domain in domains:
        results = search_site(domain, keyword, max_results=2)
        for r in results:
            url = r.get("url", "")
            if not url:
                continue
            rows.append(
                SignalRow(
                    source=domain,
                    market=market,
                    keyword=keyword,
                    signal_name=r.get("title", f"{keyword} on {domain}")[:120],
                    signal_type="competitor",
                    url=url,
                    signal_score=0.65,
                    confidence="medium",
                    notes=(r.get("content", "") or "")[:200],
                    observed_at="2026-06-19",
                    artifact_type="web",
                    artifact_uri=url,
                    created_by_tool="tavily_competitor",
                )
            )
    return rows
