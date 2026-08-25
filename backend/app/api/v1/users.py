from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...core import (
    code2session,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    login_ip_rate_limit,
    revoke_refresh_token,
    check_vip_active,
)
from ...core.ratelimit import is_refresh_revoked
from ...core.wechat import WeChatError
from ...deps import DB, ClientIP, CurrentUser, user_to_dto
from ...models import User, WechatAccount
from ...schemas import (
    LoginOut,
    LogoutIn,
    ProfileOut,
    RefreshTokenIn,
    TokenPair,
    VipInfo,
    WechatLoginIn,
    ok,
)


router = APIRouter(prefix="/auth", tags=["鉴权"])


def _vip_info(user: User, db: AsyncSession) -> VipInfo:
    # 需要同步，包装在小协程内由调用方 await
    return _vip_info_impl(user, db)


async def _vip_info_impl(user: User, db: AsyncSession) -> VipInfo:
    row = await check_vip_active(db, user.id)
    if not row:
        return VipInfo(level="none", expire_at=None)
    return VipInfo(
        level=row.level,
        expire_at=int(row.expire_at.timestamp()),
    )


def _ts(dt: datetime) -> int:
    return int(dt.timestamp())


@router.post(
    "/login",
    description="微信小程序 code 登录；未设置 AppID/Secret 时返回测试 openid（仅本地）",
    dependencies=[Depends(login_ip_rate_limit)],
)
async def wechat_login(data: WechatLoginIn, db: DB):
    try:
        sess = await code2session(data.code)
    except WeChatError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"微信登录失败: {e.msg}")
    openid = sess.get("openid")
    if not openid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未获取到 openid")

    row = (
        await db.execute(
            select(WechatAccount).where(WechatAccount.openid == openid).limit(1)
        )
    ).scalar_one_or_none()

    if row:
        user = await db.get(User, row.user_id)
    else:
        user = User(
            nickname=data.nickname or "考研人",
            avatar_url=data.avatar_url,
        )
        db.add(user)
        await db.flush()
        wa = WechatAccount(
            user_id=user.id,
            openid=openid,
            unionid=sess.get("unionid"),
            session_key=sess.get("session_key"),
        )
        db.add(wa)
        await db.flush()

    access, aexp = create_access_token(user.id)
    refresh, rexp = create_refresh_token(user.id)

    vip = await _vip_info_impl(user, db)
    return ok(
        LoginOut(
            user=user_to_dto(user),
            token=TokenPair(
                access_token=access,
                access_expire_at=_ts(aexp),
                refresh_token=refresh,
                refresh_expire_at=_ts(rexp),
            ),
            vip=vip,
        )
    )


@router.post("/refresh")
async def refresh_token(data: RefreshTokenIn, db: DB):
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh 无效")
    if payload.get("typ") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 类型错误")
    user_id = int(payload["sub"])
    if await is_refresh_revoked(user_id, data.refresh_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh 已失效")
    user = await db.get(User, user_id)
    if not user or user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号已失效")
    access, aexp = create_access_token(user.id)
    refresh, rexp = create_refresh_token(user.id)
    vip = await _vip_info_impl(user, db)
    return ok(
        LoginOut(
            user=user_to_dto(user),
            token=TokenPair(
                access_token=access,
                access_expire_at=_ts(aexp),
                refresh_token=refresh,
                refresh_expire_at=_ts(rexp),
            ),
            vip=vip,
        )
    )


@router.post("/logout")
async def logout(data: LogoutIn, user: CurrentUser):
    try:
        payload = decode_refresh_token(data.refresh_token)
        if int(payload["sub"]) != user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "不匹配的 refresh")
        exp = datetime.utcfromtimestamp(int(payload["exp"]))
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "refresh 无效")
    await revoke_refresh_token(user.id, data.refresh_token, exp)
    return ok(msg="已登出")


@router.get("/profile")
async def profile(user: CurrentUser, db: DB):
    vip = await _vip_info_impl(user, db)
    return ok(ProfileOut(user=user_to_dto(user), vip=vip))
