from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChatMode = Literal["trends", "crosscheck", "roi", "freeform", "category", "competitors"]
DemandDriver = Literal["consumer_pull", "trade_push", "mixed"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: ChatMode = "freeform"
    market: str = "CH"
    trend_context: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    mode: ChatMode
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    emerging_trends: list[dict[str, Any]] = Field(default_factory=list)
    bloom_predictions: list[dict[str, Any]] = Field(default_factory=list)
    product_stocking: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    charts: dict[str, Any] = Field(default_factory=dict)
    retailer_playbook: list[dict[str, Any]] = Field(default_factory=list)
    market_capture: dict[str, Any] | None = None
    evidence_urls: list[str] = Field(default_factory=list)
    demand_driver: DemandDriver | None = None
    score_explanation: dict[str, Any] | None = None
    steps: list[str] = Field(default_factory=list)
    used_live_search: bool = False
    show_category_prompt: bool = False
    category_options: list[dict[str, Any]] = Field(default_factory=list)
    selected_category: str | None = None
