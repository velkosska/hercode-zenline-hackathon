"""Full Zenline Scout pipeline orchestration."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.radar.pipeline.enrich import FINAL_DIR, ROOT, run_enrich

DATA_DIR = ROOT / "data"


def run_pipeline(skip_process: bool = False) -> dict:
    """Stage 1: process_trends → Stage 2: enrich + overlap + corroborate."""
    final_dir = run_enrich(skip_process=skip_process)

    for name in ("trends_metrics.csv", "trends_summary.md"):
        src = DATA_DIR / name
        if src.exists():
            shutil.copy(src, final_dir / name)

    return {
        "status": "ok",
        "output_dir": str(final_dir),
        "signals": str(final_dir / "signals.csv"),
        "recommendations": str(final_dir / "recommendations.json"),
        "clusters": str(final_dir / "clusters.json"),
    }


if __name__ == "__main__":
    result = run_pipeline()
    print(result)
