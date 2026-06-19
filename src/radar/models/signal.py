from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]
CoverageStatus = Literal["covered", "partially_covered", "absent", "unknown", "not_relevant"]
RangeTag = Literal["core", "premium", "experimental", "monitor"]


class SignalRow(BaseModel):
    source: str
    market: str
    keyword: str
    signal_name: str
    signal_type: str
    product_name: str = ""
    brand: str = ""
    price: str = ""
    rank: str = ""
    url: str = ""
    signal_score: float = Field(ge=0, le=1)
    confidence: Confidence = "medium"
    notes: str = ""
    observed_at: str = ""
    artifact_type: str = "csv"
    artifact_uri: str = ""
    created_by_tool: str = "zenline_scout"


class RecommendationRow(BaseModel):
    rank: int
    opportunity: str
    keyword: str = ""
    first_observed_market: str = "CH"
    evidence_summary: str = ""
    evidence_urls: list[str] = Field(default_factory=list)
    transferability: str = ""
    coverage_status: CoverageStatus = "unknown"
    recommended_action: str = ""
    range_tag: RangeTag = "experimental"
    confidence: Confidence = "medium"
    signal_score: float = Field(ge=0, le=1, default=0.5)
    risks: str = ""
    scout_module: str = "Scout"
