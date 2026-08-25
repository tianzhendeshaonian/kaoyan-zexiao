from __future__ import annotations

from datetime import datetime, timedelta
from typing import AsyncIterable

from fastapi import Depends, HTTPException, Request, status
from loguru import logger

from ..config import settings
from ..redis_client import redis_client


async def _get_client_ip(request: Request) -> str:
    # 真实部署在 Nginx 后面时需配置 X-Forwarded-For 的可信代理
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


class SlidingWindowLimiter:
    def __init__(self, redis_key_prefix: str, limit: int, window_seconds: int):
        self.prefix = redis_key_prefix
        self.limit = limit
        self.window = window_seconds

    @property
    def key(self) -> str:
        return self.prefix

    async def hit(self, identity: str, increment: int = 1) -> tuple[bool, int]:
        key = f"{self.prefix}:{identity}"
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        start_ms = now_ms - self.window * 1000
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, start_ms)
        pipe.zadd(key, {str(now_ms): now_ms})
        pipe.zcard(key)
        pipe.expire(key, self.window + 10)
        results = await pipe.execute()
        count = int(results[2]) if len(results) > 2 else 0
        remain = max(0, self.limit - count)
        ok = count <= self.limit
        return ok, remain


async def global_ip_rate_limit(ip: str = Depends(_get_client_ip)):
    ok, remain = await SlidingWindowLimiter(
        "rl:global_ip", settings.RL_GLOBAL_IP_PER_MIN, 60
    ).hit(ip)
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "请求过于频繁")
    return remain


async def login_ip_rate_limit(ip: str = Depends(_get_client_ip)):
    ok, _ = await SlidingWindowLimiter(
        "rl:login_ip", settings.RL_LOGIN_IP_PER_MIN, 60
    ).hit(ip)
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "登录请求过于频繁")


async def recommend_rate_limit(user_id: int, is_vip: bool) -> None:
    """冲稳保每日次数，VIP 不限。"""
    if is_vip:
        return
    day = datetime.utcnow().strftime("%Y%m%d")
    ok, remain = await SlidingWindowLimiter(
        f"rl:recommend:{day}", settings.RL_RECOMMEND_FREE_PER_DAY, 24 * 3600
    ).hit(str(user_id))
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "今日次数已用完，升级VIP可无限使用")


async def report_rate_limit(user_id: int) -> None:
    ok, _ = await SlidingWindowLimiter(
        "rl:report_per_day", settings.RL_REPORT_PER_DAY, 24 * 3600
    ).hit(str(user_id))
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "今日填报次数已达上限")


# --- 原子工具（防重放/吊销刷新token） ---

async def mark_wechat_code_used(code: str, ttl_seconds: int = 300) -> bool:
    key = f"wechat:code_used:{code}"
    # SETNX: return True if set (first time), False if existed
    ok = await redis_client.set(key, "1", nx=True, ex=ttl_seconds)
    return bool(ok)


async def revoke_refresh_token(user_id: int, token: str, expire_at: datetime) -> None:
    now = datetime.utcnow()
    ttl = max(60, int((expire_at - now).total_seconds()))
    await redis_client.set(f"jwt:revoke:{user_id}:{hash(token)}", "1", ex=ttl)


async def is_refresh_revoked(user_id: int, token: str) -> bool:
    v = await redis_client.get(f"jwt:revoke:{user_id}:{hash(token)}")
    return v is not None
