from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .core.security import decode_access_token
from .core.ratelimit import _get_client_ip
from .models import User, VipMembership
from .schemas.common import UserDTO


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not token:
        # fallback to header x-token
        token = request.headers.get("x-authorization") or request.headers.get("x-token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        token_family = payload.get("typ")
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录状态无效")
    if token_family != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 类型错误")
    user = await db.get(User, user_id)
    if not user or user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在或已封禁")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
ClientIP = Annotated[str, Depends(_get_client_ip)]


async def get_optional_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """匿名可达接口使用：未带 token 返回 None；带 token 但无效直接 401。"""
    if not token:
        token = request.headers.get("x-authorization") or request.headers.get("x-token")
    if not token:
        return None
    return await get_current_user(request, token, db)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def require_vip(
    user: CurrentUser,
    db: DB,
) -> User:
    now = datetime.utcnow()
    row = (
        await db.execute(
            select(VipMembership)
            .where(
                VipMembership.user_id == user.id,
                VipMembership.status == "active",
                VipMembership.start_at <= now,
                VipMembership.expire_at > now,
            )
            .order_by(VipMembership.expire_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要 VIP 会员")
    return user


VipUser = Annotated[User, Depends(require_vip)]


def user_to_dto(u: User) -> UserDTO:
    return UserDTO(
        id=u.id,
        nickname=u.nickname,
        avatar_url=u.avatar_url,
    )
