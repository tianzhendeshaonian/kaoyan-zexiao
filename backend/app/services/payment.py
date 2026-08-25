"""微信支付服务。

⚠️ 商用前需要：
1. 申请微信支付商户号 mch_id
2. 在 .env 配置 WECHAT_PAY_MCH_ID / WECHAT_PAY_API_KEY / WECHAT_PAY_CERT_PATH
3. 回调接口配置在微信支付商户后台（HTTPS 域名）

本模块为完整接口形态，未配置商户号时进入 demo 模式：
  - create_order：返回模拟 payment_params（小程序可调起 wx.requestPayment 调试）
  - verify_notify：本地 demo 跳过验签，仅校验金额与订单匹配
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from ..config import settings


# 微信支付统一下单 URL（V2 API，小程序场景）
WECHAT_PAY_UNIFIEDORDER = "https://api.mch.weixin.qq.com/pay/unifiedorder"


# 套餐配置（与 vip.py 的 PLANS 保持一致）
PLANS: dict[str, dict] = {
    "monthly":   {"title": "月卡",  "amount": 19.9,  "days": 30},
    "quarterly": {"title": "季卡",  "amount": 49.9,  "days": 90},
    "yearly":    {"title": "年卡",  "amount": 158.0, "days": 365},
}


def gen_order_no() -> str:
    """生成订单号：VIP + 时间戳 + 随机后缀。"""
    return "VIP" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + secrets.token_hex(3)


def plan_total_fee(plan: str) -> int:
    """元 → 分（微信支付以分为单位）。"""
    p = PLANS.get(plan)
    if not p:
        raise ValueError(f"unknown plan: {plan}")
    return int(round(p["amount"] * 100))


def plan_days(plan: str) -> int:
    return PLANS[plan]["days"]


def _is_demo_mode() -> bool:
    """无 mch_id / api_key 配置时进入 demo 模式。"""
    return not (settings.WECHAT_APP_ID and getattr(settings, "WECHAT_PAY_MCH_ID", ""))


async def unifiedorder(
    order_no: str, plan: str, user_id: int, openid: str,
    client_ip: str, notify_url: str,
) -> dict:
    """调用微信支付统一下单接口，返回小程序支付参数。

    返回结构（实际接入）:
      {
        "appId": "...",
        "timeStamp": "...",
        "nonceStr": "...",
        "package": "prepay_id=...",
        "signType": "RSA",
        "paySign": "..."
      }

    demo 模式返回模拟字段，便于前端联调。
    """
    if _is_demo_mode():
        logger.warning("demo 模式：未配置微信支付商户号，返回模拟 payment_params")
        return {
            "appId": settings.WECHAT_APP_ID or "demo_appid",
            "timeStamp": str(int(datetime.utcnow().timestamp())),
            "nonceStr": secrets.token_hex(8),
            "package": f"prepay_id=demo_{order_no}",
            "signType": "RSA",
            "paySign": "demo_sign",
            "_demo": True,
        }

    # 真实接入：构造 XML 调用统一下单
    import httpx
    total_fee = plan_total_fee(plan)
    nonce = secrets.token_hex(8)
    body = (
        "<xml>"
        f"<appid>{settings.WECHAT_APP_ID}</appid>"
        f"<mch_id>{settings.WECHAT_PAY_MCH_ID}</mch_id>"
        f"<nonce_str>{nonce}</nonce_str>"
        f"<body>考研择校VIP-{PLANS[plan]['title']}</body>"
        f"<out_trade_no>{order_no}</out_trade_no>"
        f"<total_fee>{total_fee}</total_fee>"
        f"<spbill_create_ip>{client_ip}</spbill_create_ip>"
        f"<notify_url>{notify_url}</notify_url>"
        f"<trade_type>JSAPI</trade_type>"
        f"<openid>{openid}</openid>"
        f"<sign>{_sign_v2(...)}</sign>"
        "</xml>"
    )
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.post(WECHAT_PAY_UNIFIEDORDER, content=body,
                           headers={"Content-Type": "text/xml"})
        # 解析 XML → 取 prepay_id → 二次签名返回支付参数
        # 此处省略 XML 解析实现，真实接入补 xmltodict 或 lxml
        raise NotImplementedError("完整 XML 解析需商用环境实现")


def _sign_v2(params: dict, api_key: str) -> str:
    """微信支付 V2 签名：MD5(按 key 排序拼接 + &key=api_key)。"""
    items = sorted((k, v) for k, v in params.items() if v and k != "sign")
    raw = "&".join(f"{k}={v}" for k, v in items) + f"&key={api_key}"
    return hashlib.md5(raw.encode()).hexdigest().upper()


def verify_notify(payload: dict, expected_order_no: str,
                  expected_total_fee: int) -> bool:
    """校验微信支付异步通知。

    校验项（实际接入）：
    1. return_code == SUCCESS
    2. result_code == SUCCESS
    3. 签名验证（_sign_v2 重新计算并比对）
    4. out_trade_no 与本地订单号一致
    5. total_fee 与本地订单金额一致（防篡改）

    demo 模式：跳过签名验证，仅校验金额与订单号。
    """
    if payload.get("return_code") != "SUCCESS":
        return False
    if payload.get("result_code") != "SUCCESS":
        return False
    if payload.get("out_trade_no") != expected_order_no:
        logger.warning("notify out_trade_no mismatch: {} vs {}",
                       payload.get("out_trade_no"), expected_order_no)
        return False
    try:
        if int(payload.get("total_fee", 0)) != expected_total_fee:
            logger.warning("notify total_fee mismatch: {} vs {}",
                           payload.get("total_fee"), expected_total_fee)
            return False
    except (TypeError, ValueError):
        return False

    if _is_demo_mode():
        logger.warning("demo 模式：跳过微信支付签名验证（仅本地测试）")
        return True

    # 真实接入：重新计算签名比对
    api_key = getattr(settings, "WECHAT_PAY_API_KEY", "")
    if not api_key:
        return False
    expected_sign = _sign_v2({k: v for k, v in payload.items() if k != "sign"}, api_key)
    received_sign = payload.get("sign", "")
    return hmac.compare_digest(expected_sign, received_sign)
