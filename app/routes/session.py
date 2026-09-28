"""Session routes: /session-info and /session-data."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AUTH_COOKIE_NAME, get_current_user
from app.core.security import token_expiry_iso
from app.models import User
from app.models.history import get_plan_stats
from app.schemas.auth import SessionData, SessionInfo, UserOut

router = APIRouter(prefix="", tags=["session"])


def _current_token(request: Request) -> str | None:
    token = getattr(request.state, "auth_token", None)
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/session-info", response_model=SessionInfo)
def session_info(request: Request, user: User = Depends(get_current_user)) -> SessionInfo:
    """Metadata about the current session: identity, login status, token lifetime."""
    token = _current_token(request)
    return SessionInfo(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        issued_at=user.created_at.isoformat() if user.created_at else None,
        expires_at=token_expiry_iso(token) if token else None,
    )


@router.get("/session-data", response_model=SessionData)
def session_data(request: Request, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> SessionData:
    """Detailed session-specific data used for personalization and tracking."""
    token = _current_token(request)
    return SessionData(
        user=UserOut.model_validate(user),
        plan_stats=get_plan_stats(db, user.id),
        login_expires_at=token_expiry_iso(token) if token else None,
    )
