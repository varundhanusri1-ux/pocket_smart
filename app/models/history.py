"""History data-access helpers. History = persisted RecommendationPlan rows.

Every query is scoped to a user id so user data isolation is enforced at the
data-access layer, not just in routes.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.recommendation import PLANNER_TYPES, RecommendationPlan


def get_user_plans(db: Session, user_id: int, planner_type: str | None = None,
                   limit: int = 100) -> list[RecommendationPlan]:
    stmt = select(RecommendationPlan).where(RecommendationPlan.user_id == user_id)
    if planner_type:
        if planner_type not in PLANNER_TYPES:
            raise ValueError(f"Unknown planner type: {planner_type}")
        stmt = stmt.where(RecommendationPlan.planner_type == planner_type)
    stmt = stmt.order_by(RecommendationPlan.created_at.desc()).limit(min(limit, 200))
    return list(db.scalars(stmt))


def get_user_plan(db: Session, user_id: int, plan_id: int) -> RecommendationPlan | None:
    """Fetch one plan owned by the user; returns None when not owned."""
    stmt = select(RecommendationPlan).where(
        RecommendationPlan.id == plan_id, RecommendationPlan.user_id == user_id
    )
    return db.scalars(stmt).first()


def get_latest_user_plan(db: Session, user_id: int, planner_type: str | None = None) -> RecommendationPlan | None:
    stmt = select(RecommendationPlan).where(RecommendationPlan.user_id == user_id)
    if planner_type:
        stmt = stmt.where(RecommendationPlan.planner_type == planner_type)
    stmt = stmt.order_by(RecommendationPlan.created_at.desc()).limit(1)
    return db.scalars(stmt).first()


def get_plan_stats(db: Session, user_id: int) -> dict:
    """Aggregated counts/budgets per planner type for dashboard insights."""
    rows = db.execute(
        select(
            RecommendationPlan.planner_type,
            func.count(RecommendationPlan.id),
            func.sum(RecommendationPlan.budget),
        )
        .where(RecommendationPlan.user_id == user_id)
        .group_by(RecommendationPlan.planner_type)
    ).all()
    by_type = {t: {"count": 0, "total_budget": 0.0} for t in PLANNER_TYPES}
    for planner_type, count, total in rows:
        by_type[planner_type] = {"count": int(count), "total_budget": float(total or 0.0)}
    total_count = sum(v["count"] for v in by_type.values())
    return {"total_plans": total_count, "by_type": by_type}
