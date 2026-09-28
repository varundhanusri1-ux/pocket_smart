"""Jewelry planner API — POST /generate-jewelry (multipart, optional image)."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.jewelry import JewelryPlanRequest, validate_image_upload
from app.services import recommendation_service

router = APIRouter(tags=["jewelry-planner"])


@router.post("/generate-jewelry")
async def generate_jewelry(
    total_budget: float = Form(..., gt=0),
    occasion: str = Form(..., min_length=2, max_length=60),
    style_preference: str | None = Form(None),
    jewelry_type: str | None = Form(None),
    outfit_description: str | None = Form(None),
    outfit_image: UploadFile | None = File(None, alias="outfit_image"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI jewelry plan; supports an optional outfit image."""
    try:
        payload = JewelryPlanRequest(
            total_budget=total_budget,
            occasion=occasion,
            style_preference=style_preference,
            jewelry_type=jewelry_type,
            outfit_description=outfit_description,
        )
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Please check the jewelry planner fields — budget and occasion are "
                   "required, and text fields must be within their length limits.",
        )

    image = validate_image_upload(outfit_image, settings)
    plan = recommendation_service.generate_jewelry_plan(db, current_user, payload, image=image)
    return recommendation_service.plan_response(plan)
