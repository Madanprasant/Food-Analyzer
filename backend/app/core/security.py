from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings


class InvalidTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, settings: Settings) -> tuple[str, datetime, str]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    token_id = str(uuid4())
    token = jwt.encode(
        {"sub": user_id, "jti": token_id, "iat": now, "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at, token_id


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as error:
        raise InvalidTokenError("Token is invalid or expired.") from error
    if not payload.get("sub") or not payload.get("jti"):
        raise InvalidTokenError("Token is missing required claims.")
    return payload
