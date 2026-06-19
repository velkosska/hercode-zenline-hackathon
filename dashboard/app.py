"""Zenline Scout — Streamlit dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

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

    tab_scout, tab_evidence, tab_overlap, tab_range = st.tabs(
        ["Scout", "Evidence", "Overlap Guard", "Range Architect"]
    )

    with tab_scout:
        st.subheader("Ranked opportunities")
        combined = rec_data.get("combined_top") or rec_data.get("recommendations", [])[:8]
        for item in combined[:8]:
            rank = item.get("combined_rank") or item.get("rank", "?")
            conf = item.get("confidence", "medium")
            st.markdown(f"### #{rank} — {item.get('opportunity', item.get('keyword', ''))}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{item.get('signal_score', 0):.2f}")
            c2.markdown(f"**Confidence:** :{confidence_color(conf)}[{conf.upper()}]")
            c3.markdown(f"**Source:** {item.get('source', 'Scout')}")
            st.markdown(f"**Action:** {item.get('recommended_action', '—')}")
            urls = item.get("evidence_urls", [])
            if urls:
                st.markdown("**Evidence:**")
                for u in urls[:5]:
                    st.markdown(f"- [{u}]({u})")
            st.divider()

    with tab_evidence:
        st.subheader("Evidence trail")
        keywords = sorted(signals_df["keyword"].dropna().unique())
        selected = st.selectbox("Filter by keyword", ["All"] + list(keywords))
        filtered = signals_df if selected == "All" else signals_df[signals_df["keyword"] == selected]
        st.dataframe(
            filtered[["source", "market", "signal_type", "signal_name", "url", "confidence", "signal_score", "notes"]],
            use_container_width=True,
            hide_index=True,
        )
        for _, row in filtered.head(10).iterrows():
            if pd.notna(row.get("url")) and str(row["url"]).startswith("http"):
                st.markdown(f"- [{row['source']} / {row['signal_type']}]({row['url']}) — {row['notes'][:120]}")

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
        recs = rec_data.get("recommendations", []) + rec_data.get("agent_synthesis", [])
        tags = {"core": [], "premium": [], "experimental": [], "monitor": []}
        for r in recs:
            tag = r.get("range_tag", "experimental")
            if tag in tags:
                tags[tag].append(r)
        cols = st.columns(4)
        for col, (tag, items) in zip(cols, tags.items()):
            with col:
                st.markdown(f"**{tag.upper()}**")
                for r in items[:4]:
                    st.markdown(f"- **{r.get('opportunity', r.get('keyword'))[:40]}**")
                    st.caption(r.get("recommended_action", "")[:80])

    st.sidebar.markdown("---")
    st.sidebar.code("make process\nmake pipeline\nmake dashboard", language="bash")


if __name__ == "__main__":
    main()
