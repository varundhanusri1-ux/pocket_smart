"""RecommendationPlan model — one row per generated plan; doubles as history."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import utcnow

PLANNER_TYPES = ("home", "party", "jewelry")
PLAN_SOURCES = ("gemini", "fallback")


class RecommendationPlan(Base):
    __tablename__ = "recommendation_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    planner_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    # "gemini" = AI-generated, "fallback" = demo data shown during AI unavailability
    source: Mapped[str] = mapped_column(String(20), default="gemini", nullable=False)
    ai_generated: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)

    user = relationship("User", backref="plans")

    def __repr__(self) -> str:
        return f"<RecommendationPlan id={self.id} type={self.planner_type} user_id={self.user_id}>"
