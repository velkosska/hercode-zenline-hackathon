from __future__ import annotations

from collections import defaultdict

from src.radar.models.signal import Confidence, SignalRow


def _unique_domains(urls: list[str]) -> int:
    domains = set()
    for url in urls:
        if not url or not url.startswith("http"):
            continue
        try:
            host = url.split("/")[2].replace("www.", "")
            domains.add(host)
        except IndexError:
            continue
    return len(domains)


def corroboration_score(signals: list[SignalRow]) -> float:
    if not signals:
        return 0.0
    sources = len({s.source for s in signals})
    types = len({s.signal_type for s in signals})
    markets = len({s.market for s in signals})
    urls = [s.url for s in signals if s.url]
    domains = _unique_domains(urls)
    url_count = len(set(urls))

    score = (
        0.30 * min(1.0, sources / 3)
        + 0.30 * min(1.0, types / 3)
        + 0.20 * min(1.0, markets / 2)
        + 0.20 * min(1.0, domains / max(url_count, 1))
    )
    return round(score, 3)


def gate_confidence(signals: list[SignalRow], base: Confidence = "medium") -> Confidence:
    urls = [s.url for s in signals if s.url and s.url.startswith("http")]
    types = {s.signal_type for s in signals}
    unique_domains = _unique_domains(urls)
    has_marketplace = "marketplace" in types
    has_search_or_competitor = bool(types & {"search", "competitor"})
    marketplace_boost = has_marketplace and has_search_or_competitor and len(types) >= 2

    if len(set(urls)) >= 3 and len(types) >= 2 and unique_domains >= 2:
        return "high"
    if marketplace_boost and len(set(urls)) >= 2:
        return "high"
    if len(set(urls)) >= 2 and len(types) >= 2:
        return "medium"
    if len(set(urls)) >= 2:
        return base if base != "high" else "medium"
    return "low"


def group_signals_by_keyword(signals: list[SignalRow]) -> dict[str, list[SignalRow]]:
    groups: dict[str, list[SignalRow]] = defaultdict(list)
    for s in signals:
        key = s.keyword.strip().lower()
        groups[key].append(s)
    return dict(groups)


def assess_cluster(signals: list[SignalRow]) -> dict:
    score = corroboration_score(signals)
    conf = gate_confidence(signals)
    urls = list({s.url for s in signals if s.url})
    types = list({s.signal_type for s in signals})
    return {
        "corroboration_score": score,
        "confidence": conf,
        "evidence_urls": urls,
        "source_types": types,
        "signal_count": len(signals),
    }
