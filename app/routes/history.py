"""History page — GET /history. Private per user."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models import User
from app.models.history import get_user_plans
from app.routes.pages import templates, _ctx

router = APIRouter(tags=["history"])

PLANNER_LABELS = {"home": "Home Interior", "party": "Party", "jewelry": "Jewelry"}


@router.get("/history")
def history_page(request: Request, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    if user is None:
        # API clients get a JSON 401; browsers get a login redirect.
        if "application/json" in request.headers.get("accept", ""):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You need to be logged in to access this.",
            )
        return RedirectResponse(url="/login", status_code=302)

    plans = get_user_plans(db, user.id, limit=100)
    entries = [{
        "id": p.id,
        "planner_type": p.planner_type,
        "planner_label": PLANNER_LABELS.get(p.planner_type, p.planner_type.title()),
        "title": p.title,
        "budget": p.budget,
        "input_summary": p.input_summary or {},
        "source": p.source,
        "ai_generated": p.ai_generated,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "item_count": len((p.result or {}).get("recommendations", [])),
    } for p in plans]

    if "application/json" in request.headers.get("accept", ""):
        return {"plans": entries, "total": len(entries)}

    # HTML entries keep datetime objects for template formatting.
    for entry, plan in zip(entries, plans):
        entry["created_at"] = plan.created_at
    return templates.TemplateResponse(request, "history.html", _ctx(
        request, user, entries=entries, planner_labels=PLANNER_LABELS,
    ))
