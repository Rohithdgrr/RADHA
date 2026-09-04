import structlog
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings

log = structlog.get_logger()
pwd_context = None
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=False)
except Exception:
    pass

bearer_scheme = HTTPBearer(auto_error=False)
bearer_required = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    # fallback plain (dev only) — should not happen
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if pwd_context:
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            return False
    import hashlib
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token_optional(token: str) -> dict | None:
    if not token or len(token) < 10:
        return None
    try:
        from jose import jwt

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception as e:
        log.debug("jwt decode optional failed", error=str(e))
        return None


def decode_token_required(token: str) -> dict:
    from jose import jwt

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(lambda: None),  # placeholder, overridden per route via Depends
) -> dict | None:
    # Generic optional — actual DB lookup is done in router deps
    if not credentials:
        return None
    payload = decode_token_optional(credentials.credentials)
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_required),
    db: AsyncSession = None,
) -> dict:
    # This will be overridden with DB session in router's dependency wrapper
    payload = decode_token_required(credentials.credentials)
    return payload
