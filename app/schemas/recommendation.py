"""Shared recommendation output schemas (validated Gemini/fallback plan data)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PlannerType = Literal["home", "party", "jewelry"]


class AllocationItem(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: float = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    note: str | None = Field(default=None, max_length=300)


class RecommendationItem(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    estimated_price: float = Field(ge=0)
    quantity: int = Field(default=1, ge=1, le=999)
    total_price: float = Field(ge=0)
    platform: str = Field(min_length=1, max_length=60)
    reason: str | None = Field(default=None, max_length=500)
    link: str | None = Field(default=None, max_length=500)
    budget_status: str | None = Field(default=None, max_length=40)
    source: Literal["ai", "fallback"] = "ai"

    @field_validator("link")
    @classmethod
    def link_must_be_http(cls, v: str | None) -> str | None:
        # Only allow real, well-formed web links — never fabricated deep links.
        if v and not (v.startswith("http://") or v.startswith("https://")):
            return None
        return v


class PlanResult(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    budget: float = Field(ge=0)
    currency: str = "INR"
    allocation: list[AllocationItem] = []
    recommendations: list[RecommendationItem] = []
    tips: list[str] = Field(default_factory=list, max_length=15)
    total_estimated_cost: float = 0
    remaining_budget: float = 0
    utilization_percent: float = 0

    def model_post_init(self, __context) -> None:
        # Recompute derived figures so the UI never divides by zero or shows drift.
        items_total = round(sum(r.total_price for r in self.recommendations), 2)
        self.total_estimated_cost = items_total or round(sum(a.amount for a in self.allocation), 2)
        self.remaining_budget = round(self.budget - self.total_estimated_cost, 2)
        self.utilization_percent = (
            round(self.total_estimated_cost / self.budget * 100, 1) if self.budget > 0 else 0.0
        )
        for r in self.recommendations:
            if not r.budget_status:
                r.budget_status = (
                    "within-budget" if items_total <= self.budget else "over-budget"
                )


class PlanResponse(BaseModel):
    plan_id: int
    planner_type: PlannerType
    title: str
    input_summary: dict = {}
    source: Literal["gemini", "fallback"]
    ai_generated: bool
    created_at: datetime | None = None
    result: PlanResult


class PlanDetailResponse(PlanResponse):
    """Recommendation details, optionally including the raw input summary."""
