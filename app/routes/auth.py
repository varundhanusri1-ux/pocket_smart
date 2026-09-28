"""Authentication routes: register, login (JSON), OAuth2 token, logout."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import clear_auth_cookie, set_auth_cookie
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="", tags=["auth"])


def _issue_token(user: User, request: Request, response: Response) -> TokenResponse:
    token, expires_at = create_access_token(user.id)
    set_auth_cookie(response, token, secure=request.url.scheme == "https")
    return TokenResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response,
             db: Session = Depends(get_db)):
    """Create a new account and start an authenticated session."""
    email = payload.email.lower().strip()
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Try logging in instead.",
        )

    from app.core.security import hash_password

    user = User(email=email, full_name=payload.full_name, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Try logging in instead.",
        )
    db.refresh(user)
    return _issue_token(user, request, response)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response,
          db: Session = Depends(get_db)):
    """Authenticate with email + password (JSON body). Sets an HttpOnly cookie."""
    email = payload.email.lower().strip()
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Generic message: never reveal whether the email exists.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please try again.",
        )
    return _issue_token(user, request, response)


@router.post("/token", response_model=TokenResponse)
def issue_token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow for API clients. Returns the JWT; does not set cookies."""
    user = db.scalars(select(User).where(User.email == form.username.lower().strip())).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_at = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user=UserOut.model_validate(user),
    )


@router.get("/logout")
def logout_get(response: Response):
    """Clear the session cookie and end the authenticated session (browser flow)."""
    clear_auth_cookie(response)
    return {"detail": "Logged out successfully."}


@router.post("/logout")
def logout_post(response: Response):
    """Clear the session cookie and end the authenticated session (API flow)."""
    clear_auth_cookie(response)
    return {"detail": "Logged out successfully."}
