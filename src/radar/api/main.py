"""FastAPI for Zenline Scout."""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.radar.agent.chat_agent import live_search_available, run_chat
from src.radar.api.dashboard_data import fetch_dashboard
from src.radar.api.landing_data import fetch_competitor_snapshot, fetch_live_trends
from src.radar.models.chat import ChatRequest, ChatResponse
from src.radar.pipeline.enrich import FINAL_DIR, ROOT
from src.radar.pipeline.run import run_pipeline

load_dotenv(ROOT / ".env")

app = FastAPI(title="Zenline Scout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _results_path() -> Path:
    final = FINAL_DIR / "recommendations.json"
    if final.exists():
        return final
    fallback = ROOT / "data" / "recommendations.json"
    return fallback


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "zenline-scout",
        "live_search_available": live_search_available(),
    }


@app.get("/dashboard")
def dashboard(market: str = "CH"):
    try:
        return fetch_dashboard(market.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/live-trends")
def live_trends(market: str = "CH"):
    try:
        return fetch_live_trends(market.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/competitor-snapshot")
def competitor_snapshot(market: str = "CH"):
    try:
        return fetch_competitor_snapshot(market.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/results")
def get_results():
    path = _results_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="No results yet. POST /run first.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/run")
def run_scout(skip_process: bool = False):
    try:
        result = run_pipeline(skip_process=skip_process)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/signals")
def get_signals():
    path = FINAL_DIR / "signals.csv"
    if not path.exists():
        path = ROOT / "data" / "signals.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="signals.csv not found")
    import pandas as pd

    df = pd.read_csv(path)
    return df.to_dict(orient="records")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return run_chat(
            request.message,
            request.mode,
            request.market.upper(),
            request.trend_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
