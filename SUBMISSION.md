# Submission

Complete this file in your fork before submitting.

## Team

- **Team name:** TrendFind(h)er
- **Team members:** Morena, Marija, Ashton, Maria
- **GitHub fork URL:** https://github.com/velkosska/hercode-zenline-hackathon
- **Demo URL, if any:**
  - **ZenScout (buyer UI + chat):** `http://localhost:3000` — run `make api` + `make web`
  - **Analyst dashboard (Streamlit):** `http://localhost:8501` — run `make dashboard`
  - **API docs:** `http://localhost:8000/docs`
- **Video walkthrough URL, if any:** https://drive.google.com/file/d/166KkY4JaXIFFvjRVlayRKw67X9om-wxh/view

## Summary

**ZenScout** (Zenline Scout) turns messy global trend signals into a short, ranked list of opportunities a category manager or buyer at a Swiss outdoor retailer can act on. Each opportunity is backed by sources, scored for reliability, reasoned for fit within Switzerland and DACH, and paired with a clear retail action.

The system has two layers:

1. **Offline pipeline** — ingests Google Trends, agent synthesis (YouTube, TikTok, market reports), and competitor coverage into normalized signals and ranked recommendations (`data/final/`).
2. **Live layer** — **Tavily** web search + **Claude** synthesis via `POST /chat`, producing bloom predictions, stocking advice, evidence, charts, and a retailer playbook. The **ZenScout** Next.js UI loads dashboard metrics and opportunity cards live from `GET /dashboard`.

We focused on **scoring and handoff**: taking normalized signals and converting them into decision-ready output a buyer can defend in a meeting. Pipeline signals use **signal score**, **confidence**, **transferability**, and **coverage gap**; live chat adds a **bloom score** blended from evidence rules (early stage, source diversity, coverage gap, recency) and AI read. Recommendations map to **Buy now**, **Worth testing**, or **Keep watching**.

The Streamlit dashboard maps to Zenline modules: **Scout**, **Evidence**, **Overlap Guard**, and **Range Architect**.

**Soundbite:** *Scout finds it early — including trends you didn't seed. Overlap Guard stops cannibalization. Range Architect tells the buyer what to do in Switzerland.*

## How To Run

```bash
cd hercode-zenline-hackathon
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy .env.example → .env and add TAVILY_API_KEY + CLAUDE_API_KEY for live chat
# Pipeline works offline using committed data/final/ when APIs are unavailable

make all              # process trends → enrich → data/final/
make api              # FastAPI at http://localhost:8000
make web-install && make web   # ZenScout at http://localhost:3000
make dashboard        # Streamlit analyst UI at http://localhost:8501
```

Single commands:

```bash
PYTHONPATH=. python process_trends.py
PYTHONPATH=. python -m src.radar.pipeline.run
streamlit run dashboard/app.py
uvicorn src.radar.api.main:app --reload --port 8000
```

If the web UI shows blank pages or 404s on static assets:

```bash
lsof -ti :3000 | xargs kill -9 2>/dev/null
cd zenscout && rm -rf .next && cd .. && make web
```

API:

- `GET /health` — status + live search availability
- `GET /dashboard?market=CH` — full dashboard payload
- `GET /live-trends?market=CH` — trend radar (Tavily or pipeline fallback)
- `GET /competitor-snapshot?market=CH` — retailer × keyword coverage
- `GET /signals` — enriched signals CSV as JSON
- `GET /results` — latest `recommendations.json`
- `POST /run` — rerun pipeline
- `POST /chat` — ZenScout live agent (Claude + Tavily); modes: `trends`, `crosscheck`, `roi`, `category`, `competitors`, `freeform`

## Inputs

- **Market:** Switzerland (primary decision market); **US** for transfer comparison and velocity-gap scoring; UI also supports **DACH** context
- **Category:** Outdoor apparel & gear — footwear, alpine access (via ferrata / Klettersteig), trail running, bikepacking, ski touring, materials, lifestyle crossover. Chat drill-down: **Shoes, Coats & shells, Gear, Accessories**
- **Seed keywords** (`config/scenario.yaml`): Trailrunning, bikepacking, Klettersteig, Skitour, Alpha Direct, recycled down, ultralight sleeping bag
- **Sources:**
  - **Google Trends** — weekly CSVs per keyword × market (`trends_raw/`)
  - **Google Trends time series** — CH/US search, news, shopping
  - **Agent synthesis** — YouTube, TikTok, market reports, cross-agent synthesis (`trends_raw/swiss_outdoor_trends.csv`)
  - **Competitor assortment** — Transa, Ochsner Sport, Decathlon (site search + coverage checks)
  - **Live web research** — Tavily web, news, marketplace, discovery (chat + enrichment)
  - **User prompts** — trends, cross-check, ROI, category drill-down, freeform chat
- **Languages:** English for UI and synthesis; **German/English keyword variants** in search (e.g. Klettersteig / via ferrata, trail running schuhe, ultraleicht schlafsack)
- **External files, APIs, or datasets:**
  - **Files:** `trends_raw/`, `config/scenario.yaml`, pipeline output `data/final/`
  - **APIs:** Tavily (`TAVILY_API_KEY`), Anthropic Claude (`CLAUDE_API_KEY`, default `claude-sonnet-4-6`)

## Outputs

- **Dashboard or UI:**
  - **ZenScout (Next.js, `:3000`)** — live dashboard: metrics row, multi-line “What’s blooming” chart, filterable opportunity cards, embedded chat co-pilot; chat results show bloom predictions (≥3), stocking, charts, evidence, retailer playbook
  - **Analyst dashboard (Streamlit, `:8501`)** — Scout, Evidence, Overlap Guard, Range Architect tabs
- **Report:** `data/final/trends_summary.md` — ranked search-signal table + agent synthesis summary
- **Structured data:**
  - `data/final/signals.csv` — enriched signal rows (source, market, keyword, score, confidence, URLs)
  - `data/final/recommendations.json` — ranked recommendations, `combined_top`, `emerging_trends` (Scout Bloom), market capture (TAM / addressable CHF), assortment items
  - `data/final/clusters.json` — Overlap Guard theme clusters
  - `data/final/trends_metrics.csv` — raw per-keyword metrics
  - **Live chat JSON** (`POST /chat`) — `bloom_predictions`, `product_stocking`, `evidence`, `charts`, `retailer_playbook`, `market_capture`, `demand_driver`
- **API endpoint:** FastAPI (`src/radar/api/main.py`, `:8000`) — see How To Run for full route list
- **Screenshots or visuals:** *(add before jury presentation — ZenScout dashboard, chat bloom predictions, opportunity cards)*

## Ranked Opportunities

| Rank | Opportunity | Evidence | Confidence |
| --- | --- | --- | --- |
| 1 | Trail running shoe wall + summer trail apparel | CH search 12w avg 58/100, velocity +112%; agent synthesis Rank 1; Transa/Ochsner trail categories | high |
| 2 | Via ferrata / Klettersteig starter kits | CH velocity +346%; Transa Klettersteig category; corroborated search + competitor | high |
| 3 | Merino / natural fiber base layers | Agent synthesis Rank 3; YouTube + market report signals in cluster | medium |
| 4 | Bikepacking starter capsule | CH avg 61/100; Transa bikepacking category; US–CH aligned momentum | high |
| 5 | Ski touring (monitor only) | US-led signal; CH velocity negative — monitor until Q4 pre-season | high (signal), low (action) |
| 6 | Quiet Outdoors aesthetic (post-gorpcore) | Agent synthesis lifestyle trend — pilot merchandising, watch 6 months | low |

**Scout Bloom (surfaced beyond seed keywords):** Packrafting, Ultralight Backpacking, Quiet Outdoors — see `emerging_trends` in `recommendations.json`.

**Recommendation mapping:** Buy now / Worth testing / Keep watching (derived from bloom score, confidence, coverage gap, and recommended action text).

## Evidence Trail

- **Primary research:** Conversation with Global Category Management at **Intersport** — used to confirm the buyer problem and react to Scout’s top recommendations (business validation, not an automated data feed)
- **Google Trends CH/US:** [Trailrunning](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=Trailrunning), [Klettersteig](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=Klettersteig), [bikepacking](https://trends.google.com/trends/explore?date=today%205-y&geo=CH&q=bikepacking)
- **Competitor assortment:** [Transa trail running](https://www.transa.ch/de/b/trailrunning/), [Transa Klettersteig](https://www.transa.ch/de/b/klettersteig/), [Transa bikepacking](https://www.transa.ch/de/b/bikepacking/), Ochsner Sport trail categories
- **Agent synthesis + social:** `trends_raw/swiss_outdoor_trends.csv` (YouTube, TikTok, market reports, Komoot-adjacent signals)
- **Overlap Guard clusters:** `data/final/clusters.json`
- **Live chat evidence:** Tavily-sourced URLs attached per prediction in `POST /chat` responses

## Reusability

The engine is category- and market-agnostic. Swap **`config/scenario.yaml`** (seed keywords, competitors, source markets, discovery queries) and re-run `make all`. The same flow applies to another retailer, category, or industry:

1. **Stage 1:** `process_trends.py` — normalize raw CSVs → signals + recommendations
2. **Stage 2:** Competitor enrichment + corroboration gate
3. **Stage 3:** Overlap Guard clustering
4. **Stage 4:** FastAPI + ZenScout UI + Streamlit consume `data/final/`; live chat adds on-demand Tavily + Claude layer

No hard-coded Swiss logic beyond default config; US comparison and transfer-gap scoring are parameterized.

## Known Limitations

- **Tavily quota** can block live web search during demo — committed `data/final/` snapshot and pipeline fallback on `/dashboard` and `/live-trends` ensure offline jury demo
- Many agent-synthesis rows lack direct social permalinks; enrichment adds competitor seed URLs but not full TikTok/YouTube links for every row
- **Transferability** is a reasoned heuristic (US–CH velocity gap + text assessment), not a fitted predictive model
- **Validation** includes Intersport conversation and worked examples; precision and lead time are not backtested against historical POS at scale
- Ski touring shows US transfer potential but negative CH velocity — flagged as monitor-only
- Clustering uses keyword aliases + fuzzy groups; not full embedding pipeline in production form

**Next steps:** Backtest lead time vs. historical POS, add one always-on live source with deduplication, tighten transferability with retailer-specific POS where available.

## Architecture Notes

```
trends_raw/ + swiss_outdoor_trends.csv
        ↓
process_trends.py → signals.csv, recommendations.json
        ↓
enrich (competitor + corroborate) + overlap_guard → data/final/
        ↓
FastAPI (:8000) ←→ ZenScout Next.js (:3000)
        ↑
Live chat: Tavily search → Claude synthesis → bloom predictions (≥3)
```

**Four stages (conceptual → implementation):**

1. **Collection** — Google Trends CSVs, agent synthesis CSV, competitor scans, live Tavily search (web/news/marketplace/discovery)
2. **Normalize & deduplicate** — signal rows with URL, market, date, source type; corroboration gate
3. **Score** — pipeline `signal_score` + confidence + transferability + coverage; live **bloom score** = 0.55×computed + 0.45×AI (computed from early stage, source diversity, coverage gap, recency)
4. **Handoff** — ranked opportunities with Buy now / Worth testing / Keep watching, market capture (CHF TAM), stocking dates, chat playbook, and category drill-down

**Key modules:**

- `src/radar/tools/tavily_search.py` — web, news, marketplace, discovery search
- `src/radar/agent/chat_agent.py` — live chat orchestration
- `src/radar/insight/live_bloom.py` — bloom scoring, charts, min-3 predictions
- `src/radar/insight/bloom_detector.py` — Scout Bloom + `emerging_trends`
- `src/radar/tools/competitor.py` — CH retailer coverage
- `src/radar/insight/corroborate.py` — evidence quality gate
- `src/radar/insight/overlap_guard.py` — theme clustering
- `src/radar/api/dashboard_data.py` — live dashboard API
- `src/radar/pipeline/run.py` — pipeline orchestration
- `zenscout/` — Next.js buyer UI
- `dashboard/app.py` — Streamlit analyst UI
