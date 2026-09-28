"""Password hashing (PBKDF2-HMAC-SHA256) and JWT creation/verification.

Passwords use stdlib PBKDF2 with per-user salt and constant-time comparison.
Tokens are signed with the configured secret via PyJWT.
"""
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

PBKDF2_ITERATIONS = 390_000

_TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> tuple[str, datetime]:
    """Return (token, expires_at_utc)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": _TOKEN_TYPE_ACCESS,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise jwt.PyJWTError on invalid/expired tokens."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != _TOKEN_TYPE_ACCESS:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def token_expiry_iso(token: str) -> str | None:
    """Best-effort ISO expiry timestamp for session info display."""
    try:
        payload = decode_access_token(token)
        return datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
    except (jwt.PyJWTError, KeyError, ValueError, OverflowError):
        return None


def _b64(data: bytes) -> str:  # pragma: no cover - reserved for future helpers
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
