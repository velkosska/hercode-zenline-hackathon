"""FastAPI for Zenline Scout."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.radar.pipeline.enrich import FINAL_DIR, ROOT
from src.radar.pipeline.run import run_pipeline

app = FastAPI(title="Zenline Scout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return {"status": "ok", "service": "zenline-scout"}


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
