"""Shared FastAPI dependencies: DB session, current user, auth cookie helpers."""
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import jwt as pyjwt

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

AUTH_COOKIE_NAME = "ps_access_token"

# auto_error=False so page routes can fall back to cookie auth / render redirects.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


def _extract_token(request: Request, bearer_token: str | None) -> str | None:
    if bearer_token:
        return bearer_token
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the user from the Authorization header or the auth cookie."""
    token = _extract_token(request, bearer_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to be logged in to access this.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account no longer exists. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.auth_token = token
    return user


def get_optional_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Same as get_current_user but returns None instead of raising."""
    token = _extract_token(request, bearer_token)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        return db.get(User, int(payload["sub"]))
    except (pyjwt.PyJWTError, KeyError, ValueError):
        return None


def set_auth_cookie(response: Response, token: str, secure: bool = False) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
