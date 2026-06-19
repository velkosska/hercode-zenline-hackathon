# Submission

Complete this file in your fork before submitting.

## Team

- Team name: *(update before final submission)*
- Team members: *(update before final submission)*
- GitHub fork URL: *(update before final submission)*
- Demo URL, if any:
  - **ZenScout (chat):** `http://localhost:3000` — `make api` + `make web`
  - **Analyst dashboard:** `http://localhost:8501` — `make dashboard`
  - **API docs:** `http://localhost:8000/docs`
- Video walkthrough URL, if any: *(optional)*

## Summary

**Zenline Scout** is a reusable assortment-intelligence pipeline for Swiss outdoor retail. **ZenScout** is the public Next.js chat front-end: three intents (latest trends, crosscheck idea, ROI) plus a ChatGPT-style prompt box, backed by a combined **Claude + Tavily** agent via `POST /chat`.

The pipeline detects opportunities from Google Trends, agent synthesis, and competitor signals; enriches via Tavily; surfaces **Scout Bloom** picks; and clusters themes via **Overlap Guard**.

The Streamlit dashboard maps to Zenline modules: **Scout**, **Evidence**, **Overlap Guard**, and **Range Architect**.

## How To Run

```bash
cd hercode-zenline-hackathon
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: copy .env.example → .env and add TAVILY_API_KEY + CLAUDE_API_KEY for live competitor search and Scout Bloom
# Pipeline works offline using committed data/final/ snapshot + seed URLs

make all              # process trends → enrich → data/final/
make api              # FastAPI at http://localhost:8000
make web-install && make web   # ZenScout at http://localhost:3000
make dashboard        # Streamlit analyst UI
```

Single commands:

```bash
PYTHONPATH=. python process_trends.py
PYTHONPATH=. python -m src.radar.pipeline.run
streamlit run dashboard/app.py
uvicorn src.radar.api.main:app --reload --port 8000
```

API:

- `GET /health` — status
- `GET /results` — latest `recommendations.json`
- `GET /signals` — enriched signals CSV as JSON
- `POST /chat` — ZenScout live agent (Claude + Tavily); modes: `trends`, `crosscheck`, `roi`, `freeform`

## Inputs

- **Market:** Switzerland (primary), US (transfer comparison)
- **Category:** Outdoor retail — footwear, alpine access, bikepacking, materials, lifestyle
- **Seed keywords:** Configured in `config/scenario.yaml` (Trailrunning, Klettersteig, bikepacking, Skitour, Alpha Direct, etc.)
- **Sources:**
  - Google Trends weekly CSVs (`trends_raw/`)
  - US/CH time series (search, news, shopping)
  - `swiss_outdoor_trends.csv` (YouTube, TikTok, market reports, agent synthesis)
  - Competitor site search (Tavily `site:transa.ch`, `site:ochsnersport.ch`, `site:decathlon.ch`) with seed URL fallbacks
  - Tavily news + marketplace enrichment for top live keywords (Trailrunning, Klettersteig, bikepacking)
  - Tavily discovery queries + Claude synthesis for **Scout Bloom** (`emerging_trends`)
- **Languages:** DE/EN keyword variants (e.g. Klettersteig / via ferrata)
- **External APIs:** Tavily (optional), Claude/Anthropic (optional for Bloom synthesis)

## Outputs

- **Dashboard:** `dashboard/app.py` — 4-tab Streamlit UI
- **Report:** `data/final/trends_summary.md`
- **Structured data:**
  - `data/final/signals.csv` — 79+ enriched signal rows
  - `data/final/recommendations.json` — ranked opportunities + `combined_top` + `emerging_trends` (Scout Bloom)
  - `data/final/clusters.json` — Overlap Guard theme clusters
  - `data/final/trends_metrics.csv`
- **API:** FastAPI (`src/radar/api/main.py`)
- **Screenshots:** *(add before jury presentation)*

## Ranked Opportunities

| Rank | Opportunity | Evidence | Confidence |
| --- | --- | --- | --- |
| 1 | Trail running shoe wall + summer trail apparel | CH search avg 58/100, velocity +112%; agent synthesis Rank 1; Transa trail category | high |
| 2 | Via ferrata / Klettersteig starter kits | CH velocity +346%; Transa Klettersteig category; corroborated search + competitor | high |
| 3 | Merino / natural fiber base layers | Agent synthesis Rank 2; YouTube + market report signals in cluster | medium |
| 4 | Bikepacking starter capsule | CH avg 61/100; Transa bikepacking category; US-CH aligned momentum | high |
| 5 | Ski touring (monitor only) | US-led signal; CH velocity negative — monitor until Q4 pre-season | high (trends), low (action) |
| 6 | Quiet Outdoors aesthetic | Agent synthesis lifestyle trend — pilot merchandising, watch 6 months | low |

**Scout Bloom (not in seed keywords):** Packrafting, Ultralight Backpacking, Quiet Outdoors — surfaced via agent synthesis + Tavily discovery; see `emerging_trends` in recommendations.json.

## Evidence Trail

- Google Trends CH/US: [Trailrunning](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=Trailrunning), [Klettersteig](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=Klettersteig), [bikepacking](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=bikepacking)
- Competitor: [Transa trail running](https://www.transa.ch/de/b/trailrunning/), [Transa Klettersteig](https://www.transa.ch/de/b/klettersteig/), [Transa bikepacking](https://www.transa.ch/de/b/bikepacking/)
- Agent synthesis + social: `trends_raw/swiss_outdoor_trends.csv`
- Overlap Guard clusters: `data/final/clusters.json`

## Reusability

Change `config/scenario.yaml` (keywords, competitors, markets) and re-run `make all`. The same pipeline applies to any retailer or category:

1. **Stage 1:** `process_trends.py` — normalize raw CSVs → signals + recommendations
2. **Stage 2:** competitor enrichment + corroboration gate
3. **Stage 3:** Overlap Guard clustering
4. **Stage 4:** dashboard + API consume `data/final/`

No hard-coded Swiss logic beyond default config; US comparison and transfer-gap scoring are parameterized.

## Known Limitations

- Many agent-synthesis rows lack direct URLs; enrichment adds competitor seeds but not full social permalinks
- Tavily rate limits during live demo — committed `data/final/` snapshot ensures offline jury demo
- Ski touring shows US transfer gap but negative CH velocity — flagged as monitor-only
- Embedding-based clustering uses keyword aliases + fuzzy groups; Claude optional for future enrichment

## Architecture Notes

```
trends_raw/ → process_trends.py → data/signals.csv + recommendations.json
                                        ↓
                    competitor enrich (Tavily + seeds) + corroborate gate
                                        ↓
                         overlap_guard.py → clusters.json
                                        ↓
                              data/final/ → Streamlit + FastAPI
```

Key modules:

- `src/radar/tools/tavily_search.py` — web, news, marketplace, discovery search
- `src/radar/tools/llm.py` — Claude bloom synthesis
- `src/radar/insight/bloom_detector.py` — Scout Bloom scoring + `emerging_trends`
- `src/radar/tools/competitor.py` — CH retailer coverage
- `src/radar/insight/corroborate.py` — evidence quality gate
- `src/radar/insight/overlap_guard.py` — theme clustering
- `src/radar/pipeline/run.py` — orchestration
- `dashboard/app.py` — Scout / Evidence / Overlap Guard / Range Architect tabs

Soundbite: *Scout finds it early — including trends you didn't seed. Overlap Guard stops cannibalization. Range Architect tells the buyer what to do in Switzerland.*
