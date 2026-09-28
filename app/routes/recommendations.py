"""Recommendation details API — GET /recommendations-details."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.models.history import get_latest_user_plan, get_user_plan
from app.services import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations-details")
def recommendations_details(
    plan_id: int | None = Query(default=None, ge=1, description="Specific plan id; defaults to the latest"),
    planner_type: str | None = Query(default=None, pattern="^(home|party|jewelry)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full details of one of the current user's recommendation plans.

    Only the owner can read a plan — other users' ids resolve to 404.
    """
    if plan_id:
        plan = get_user_plan(db, current_user.id, plan_id)
        if plan is None:
            raise HTTPException(
                status_code=404,
                detail="That recommendation plan doesn't exist in your history.",
            )
    else:
        plan = get_latest_user_plan(db, current_user.id, planner_type)
        if plan is None:
            raise HTTPException(
                status_code=404,
                detail="You haven't generated any recommendations yet.",
            )
    return recommendation_service.plan_response(plan)
