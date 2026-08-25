from __future__ import annotations

import httpx
from loguru import logger

from ..config import settings
from .ratelimit import mark_wechat_code_used


WECHAT_CODE2SESSION = "https://api.weixin.qq.com/sns/jscode2session"


class WeChatError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"wechat error {code}: {msg}")


async def code2session(code: str) -> dict:
    """换取 openid/session_key，同时防止 code 重放。"""
    if not code:
        raise WeChatError(400, "empty code")
    if not await mark_wechat_code_used(code):
        raise WeChatError(429, "code reused")

    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
        logger.warning("WECHAT_APP_ID/SECRET 未设置，返回测试 openid")
        return {
            "openid": "test_openid_" + code[:8],
            "session_key": "test_session_key",
            "unionid": None,
        }
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=8) as cli:
        r = await cli.get(WECHAT_CODE2SESSION, params=params)
        data = r.json()
    if "errcode" in data and data["errcode"] != 0:
        raise WeChatError(data["errcode"], data.get("errmsg", ""))
    return data
