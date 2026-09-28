"""Party planner API — POST /generate-party."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.party import PartyPlanRequest
from app.services import recommendation_service

router = APIRouter(tags=["party-planner"])


@router.post("/generate-party")
def generate_party(payload: PartyPlanRequest, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Generate an AI party/event plan within the given budget."""
    plan = recommendation_service.generate_party_plan(db, current_user, payload)
    return recommendation_service.plan_response(plan)
