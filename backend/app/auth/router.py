from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.auth.security import hash_password, verify_password, create_access_token, bearer_scheme
from app.config import settings

router = APIRouter()


def _to_read(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


@router.post("/register", status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    email_norm = body.email.lower().strip()
    q = await db.execute(select(User).where(User.email == email_norm))
    if q.scalars().first():
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(
        email=email_norm,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip() if body.display_name else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _to_read(user),
    }


@router.post("/login")
async def login(body: dict, db: AsyncSession = Depends(get_db)):
    # body via dict to allow raw {email, password} without schema yet? Use UserCreate partial
    email = str(body.get("email", "")).lower().strip()
    password = str(body.get("password", ""))
    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password required")
    q = await db.execute(select(User).where(User.email == email))
    user = q.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    # update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _to_read(user),
    }


@router.get("/me")
async def me(
    credentials=Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="not authenticated")
    from app.auth.security import decode_token_optional

    payload = decode_token_optional(credentials.credentials)
    if not payload or "uid" not in payload:
        raise HTTPException(status_code=401, detail="invalid token")
    q = await db.execute(select(User).where(User.id == payload["uid"]))
    user = q.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found")
    return _to_read(user)
