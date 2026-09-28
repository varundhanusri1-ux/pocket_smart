"""Home Interior planner API — POST /generate-home."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.home import HomePlanRequest
from app.services import recommendation_service

router = APIRouter(tags=["home-planner"])


@router.post("/generate-home")
def generate_home(payload: HomePlanRequest, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Generate an AI home interior plan within the given budget."""
    plan = recommendation_service.generate_home_plan(db, current_user, payload)
    return recommendation_service.plan_response(plan)
