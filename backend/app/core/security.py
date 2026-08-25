from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from ..config import settings


pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _exp(delta: timedelta) -> datetime:
    return _now() + delta


def create_access_token(sub: int | str, extra: dict | None = None) -> tuple[str, datetime]:
    exp = _exp(timedelta(minutes=settings.JWT_ACCESS_TTL_MIN))
    payload = {
        "sub": str(sub),
        "typ": "access",
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, exp


def create_refresh_token(sub: int | str) -> tuple[str, datetime]:
    exp = _exp(timedelta(days=settings.JWT_REFRESH_TTL_DAY))
    payload = {
        "sub": str(sub),
        "typ": "refresh",
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, exp


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)
