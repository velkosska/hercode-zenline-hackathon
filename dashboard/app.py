"""Zenline Scout — Streamlit dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.radar.insight.market_capture import assortment_for_keyword, recapture_for_market

ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "data" / "final"
DATA_DIR = ROOT / "data"


def data_dir() -> Path:
    if (FINAL_DIR / "recommendations.json").exists():
        return FINAL_DIR
    return DATA_DIR


@st.cache_data
def load_recommendations() -> dict:
    path = data_dir() / "recommendations.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_signals() -> pd.DataFrame:
    path = data_dir() / "signals.csv"
    return pd.read_csv(path)


@st.cache_data
def load_clusters() -> list:
    path = data_dir() / "clusters.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("clusters", [])
    rec = load_recommendations()
    return rec.get("clusters", [])


def confidence_color(conf: str) -> str:
    return {"high": "green", "medium": "orange", "low": "red"}.get(conf, "gray")


def zenline_bucket(signal_type: str, source: str) -> str:
    st = str(signal_type).lower()
    src = str(source).lower()
    if st == "search" or "trends.google" in src:
        return "Search trends"
    if st in ("competitor", "marketplace") or any(
        d in src for d in ("transa", "ochsner", "decathlon", "galaxus", "marketplace")
    ):
        return "Competitor / marketplace"
    if st in ("web", "social") or "tavily" in src or "youtube" in src or "tiktok" in src:
        return "Social / web press"
    return "Retailer behavior (N/A)"


def render_assortment_items(items: list, keyword: str = "") -> None:
    if not items and keyword:
        bundle = assortment_for_keyword(keyword)
        items = bundle.get("assortment_items", [])
    if not items:
        return
    st.markdown("**Stock these SKUs (Range Architect):**")
    for row in items:
        pri = row.get("priority", "core")
        st.markdown(f"- **{row.get('category', '—')}** ({pri}) — {row.get('examples', '')}")


def render_market_capture(capture: dict) -> None:
    if not capture:
        return
    st.markdown("**Market capture (TAM heuristic):**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Market TAM", f"CHF {capture.get('tam_total_chf_m', 0):.0f}M")
    c2.metric("Category TAM", f"CHF {capture.get('category_tam_chf_m', 0):.1f}M")
    c3.metric("Capture rate", f"{capture.get('estimated_capture_rate_pct', 0):.1f}%")
    c4.metric("Addressable", f"CHF {capture.get('addressable_revenue_chf_m', 0):.1f}M")
    st.caption(capture.get("methodology_note", ""))


def main():
    st.set_page_config(page_title="Zenline Scout", page_icon="🔭", layout="wide")
    st.title("Zenline Scout")
    st.caption("Early-signal module for Swiss outdoor assortment intelligence — Scout · Overlap Guard · Range Architect")

    rec_data = load_recommendations()
    signals_df = load_signals()
    clusters = load_clusters()
    using_final = data_dir() == FINAL_DIR

    st.sidebar.markdown(f"**Data source:** `{'data/final/' if using_final else 'data/'}`")
    st.sidebar.markdown(f"Signals: {len(signals_df)} rows")
    bloom_picks = rec_data.get("emerging_trends", [])
    st.sidebar.metric("Bloom picks", len(bloom_picks))
    selected_market = st.sidebar.selectbox(
        "Market for TAM / capture",
        ["CH", "DACH", "US"],
        index=0,
        help="Select market to see total addressable market and estimated capture (from Marija brainstorm).",
    )

    tab_scout, tab_evidence, tab_overlap, tab_range = st.tabs(
        ["Scout", "Evidence", "Overlap Guard", "Range Architect"]
    )

    with tab_scout:
        st.subheader("Ranked opportunities")
        combined = rec_data.get("combined_top") or rec_data.get("recommendations", [])[:8]
        for item in combined[:8]:
            item = recapture_for_market(item, selected_market)
            rank = item.get("combined_rank") or item.get("rank", "?")
            conf = item.get("confidence", "medium")
            st.markdown(f"### #{rank} — {item.get('opportunity', item.get('keyword', ''))}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{item.get('signal_score', 0):.2f}")
            c2.markdown(f"**Confidence:** :{confidence_color(conf)}[{conf.upper()}]")
            c3.markdown(f"**Source:** {item.get('source', 'Scout')}")
            st.markdown(f"**Action:** {item.get('recommended_action', '—')}")
            render_assortment_items(item.get("assortment_items", []), item.get("keyword", ""))
            render_market_capture(item.get("market_capture", {}))
            urls = item.get("evidence_urls", [])
            if urls:
                st.markdown("**Evidence:**")
                for u in urls[:5]:
                    st.markdown(f"- [{u}]({u})")
            st.divider()

        st.subheader("Scout Bloom — trends we think will take off")
        emerging = rec_data.get("emerging_trends", [])
        if not emerging:
            st.info("Run the pipeline with Tavily + Claude keys to populate `emerging_trends`.")
        for item in emerging:
            item = recapture_for_market(item, selected_market)
            badge = item.get("bloom_badge", "Watch")
            st.markdown(f"### {item.get('keyword', '—')} — :orange[{badge}]")
            c1, c2, c3 = st.columns(3)
            c1.metric("Bloom score", f"{item.get('bloom_score', 0):.2f}")
            c2.markdown(f"**Timing:** {item.get('timing_window', '—')}")
            c3.markdown(f"**Coverage:** {item.get('coverage_status', 'unknown')}")
            st.markdown(f"**Opportunity:** {item.get('opportunity', '—')}")
            st.markdown(f"**Action:** {item.get('recommended_action', '—')}")
            render_assortment_items(item.get("assortment_items", []), item.get("keyword", ""))
            render_market_capture(item.get("market_capture", {}))
            if item.get("bloom_rationale"):
                st.caption(item["bloom_rationale"])
            st.caption(f"Discovered by: {item.get('discovered_by', 'Scout Bloom')}")
            for u in item.get("evidence_urls", [])[:5]:
                st.markdown(f"- [{u}]({u})")
            st.divider()

    with tab_evidence:
        st.subheader("Evidence trail")
        keywords = sorted(signals_df["keyword"].dropna().unique())
        selected = st.selectbox("Filter by keyword", ["All"] + list(keywords))
        filtered = signals_df if selected == "All" else signals_df[signals_df["keyword"] == selected]
        filtered = filtered.copy()
        filtered["zenline_bucket"] = filtered.apply(
            lambda r: zenline_bucket(r.get("signal_type", ""), r.get("source", "")),
            axis=1,
        )
        bucket_order = [
            "Search trends",
            "Competitor / marketplace",
            "Social / web press",
            "Retailer behavior (N/A)",
        ]
        for bucket in bucket_order:
            bucket_df = filtered[filtered["zenline_bucket"] == bucket]
            if bucket_df.empty:
                continue
            st.markdown(f"#### {bucket} ({len(bucket_df)})")
            st.dataframe(
                bucket_df[
                    ["source", "market", "signal_type", "signal_name", "url", "confidence", "signal_score", "notes"]
                ],
                use_container_width=True,
                hide_index=True,
            )
            for _, row in bucket_df.head(5).iterrows():
                if pd.notna(row.get("url")) and str(row["url"]).startswith("http"):
                    st.markdown(
                        f"- [{row['source']} / {row['signal_type']}]({row['url']}) — {str(row['notes'])[:120]}"
                    )
            st.divider()

    with tab_overlap:
        st.subheader("Overlap Guard — merged themes")
        if not clusters:
            st.info("Run `make pipeline` to generate clusters.json")
        for cluster in clusters:
            warn = cluster.get("overlap_warning", False)
            icon = "⚠️" if warn else "✓"
            st.markdown(f"#### {icon} {cluster.get('display_name', cluster.get('theme_id'))}")
            st.markdown(cluster.get("overlap_note", ""))
            st.markdown(f"Keywords: {', '.join(cluster.get('keywords', []))}")
            st.markdown(f"Sources: {', '.join(cluster.get('sources', [])[:6])}")
            st.markdown(f"Types: {', '.join(cluster.get('source_types', []))}")
            for u in cluster.get("evidence_urls", [])[:5]:
                st.markdown(f"- [{u}]({u})")
            st.divider()

    with tab_range:
        st.subheader("Range Architect — assortment actions")
        st.caption(f"Market: **{selected_market}** — TAM and capture estimates update with sidebar selector.")
        recs = rec_data.get("recommendations", []) + rec_data.get("agent_synthesis", [])
        tags = {"core": [], "premium": [], "experimental": [], "monitor": []}
        for r in recs:
            tag = r.get("range_tag", "experimental")
            if tag in tags:
                tags[tag].append(recapture_for_market(r, selected_market))
        cols = st.columns(4)
        for col, (tag, items) in zip(cols, tags.items()):
            with col:
                st.markdown(f"**{tag.upper()}**")
                for r in items[:4]:
                    cap = r.get("market_capture", {})
                    addr = cap.get("addressable_revenue_chf_m", 0)
                    st.markdown(f"- **{r.get('opportunity', r.get('keyword'))[:40]}**")
                    st.caption(f"{r.get('recommended_action', '')[:60]}")
                    if addr:
                        st.caption(f"Addressable ~CHF {addr:.1f}M ({selected_market})")
        st.divider()
        st.markdown("#### Example: Via ferrata starter kit SKUs")
        kletter = next((r for r in recs if "klettersteig" in r.get("keyword", "").lower()), None)
        if kletter:
            render_assortment_items(kletter.get("assortment_items", []), kletter.get("keyword", ""))
            render_market_capture(kletter.get("market_capture", {}))

    st.sidebar.markdown("---")
    st.sidebar.code("make process\nmake pipeline\nmake dashboard", language="bash")


if __name__ == "__main__":
    main()
