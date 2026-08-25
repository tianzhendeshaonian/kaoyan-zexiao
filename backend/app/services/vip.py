"""VIP 会员开通/查询/续费服务。

订单状态机：
    pending → paid → refunded
    pending → cancelled（15 分钟未支付）

支付成功（idempotent）：同一 order_no 多次回调只开通一次。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import VipMembership, VipOrder, WechatAccount
from .payment import (
    PLANS,
    gen_order_no,
    plan_days,
    plan_total_fee,
    verify_notify,
)


ORDER_TTL_MINUTES = 15  # 订单未支付自动取消时长


# ---------- 订单 ----------

async def create_order(db: AsyncSession, user_id: int, plan: str,
                       client_ip: str = "0.0.0.0",
                       notify_url: str = "") -> dict:
    """创建 VIP 订单（status=pending）。

    返回订单详情 + payment_params（微信支付参数）。
    """
    if plan not in PLANS:
        raise ValueError(f"套餐不存在: {plan}")

    # 同一用户存在 pending 同套餐订单时复用（避免重复下单）
    existing = (await db.execute(
        select(VipOrder).where(
            VipOrder.user_id == user_id,
            VipOrder.plan == plan,
            VipOrder.status == "pending",
        ).order_by(VipOrder.id.desc()).limit(1)
    )).scalar_one_or_none()

    now = datetime.utcnow()
    if existing and (now - existing.created_at) < timedelta(minutes=ORDER_TTL_MINUTES):
        order = existing
    else:
        order_no = gen_order_no()
        order = VipOrder(
            user_id=user_id,
            order_no=order_no,
            plan=plan,
            amount=PLANS[plan]["amount"],
            status="pending",
        )
        db.add(order)
        await db.flush()

    # 取该用户 openid（用于微信支付下单）
    wa = (await db.execute(
        select(WechatAccount).where(WechatAccount.user_id == user_id).limit(1)
    )).scalar_one_or_none()
    openid = wa.openid if wa else ""

    # 调用微信支付下单
    from .payment import unifiedorder
    payment_params = await unifiedorder(
        order.order_no, plan, user_id, openid, client_ip, notify_url,
    )

    return {
        "order_no": order.order_no,
        "plan": order.plan,
        "amount": float(order.amount),
        "status": order.status,
        "created_at": int(order.created_at.timestamp()),
        "expire_at": int((order.created_at + timedelta(minutes=ORDER_TTL_MINUTES)).timestamp()),
        "payment_params": payment_params,
    }


async def handle_payment_success(
    db: AsyncSession, order_no: str, transaction_id: str,
) -> dict:
    """支付成功处理（幂等）。

    状态机：
    - pending → paid + 开通 VIP
    - 已 paid → 幂等返回（不重复开通）
    - cancelled/refunded → 拒绝（不应再支付）

    返回: {"ok": bool, "msg": str, "vip_expire_at": int|None}
    """
    order = (await db.execute(
        select(VipOrder).where(VipOrder.order_no == order_no).limit(1)
    )).scalar_one_or_none()
    if not order:
        return {"ok": False, "msg": "订单不存在", "vip_expire_at": None}

    if order.status == "paid":
        # 幂等：已支付，不重复开通
        vip = await _get_active_vip(db, order.user_id)
        return {
            "ok": True, "msg": "订单已支付（幂等）",
            "vip_expire_at": int(vip.expire_at.timestamp()) if vip else None,
        }
    if order.status in ("cancelled", "refunded"):
        return {"ok": False, "msg": f"订单状态 {order.status}，无法支付",
                "vip_expire_at": None}

    # pending → paid
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    await db.flush()

    # 开通/续费 VIP
    vip = await _grant_vip(db, order.user_id, plan_days(order.plan))
    return {
        "ok": True, "msg": "支付成功",
        "vip_expire_at": int(vip.expire_at.timestamp()),
    }


async def handle_notify(db: AsyncSession, payload: dict) -> dict:
    """微信支付异步通知入口。

    校验 → 状态机更新。失败返回 False，路由层回微信失败 XML。
    """
    order_no = payload.get("out_trade_no", "")
    order = (await db.execute(
        select(VipOrder).where(VipOrder.order_no == order_no).limit(1)
    )).scalar_one_or_none()
    if not order:
        return {"ok": False, "msg": "订单不存在"}

    expected_fee = plan_total_fee(order.plan)
    if not verify_notify(payload, order_no, expected_fee):
        return {"ok": False, "msg": "通知校验失败"}

    transaction_id = payload.get("transaction_id", "")
    return await handle_payment_success(db, order_no, transaction_id)


async def cancel_expired_orders(db: AsyncSession) -> int:
    """清理 15 分钟未支付的 pending 订单。返回取消数量。"""
    threshold = datetime.utcnow() - timedelta(minutes=ORDER_TTL_MINUTES)
    rows = (await db.execute(
        select(VipOrder).where(
            VipOrder.status == "pending",
            VipOrder.created_at < threshold,
        )
    )).scalars().all()
    for r in rows:
        r.status = "cancelled"
    await db.flush()
    return len(rows)


# ---------- VIP 开通/查询 ----------

async def _grant_vip(db: AsyncSession, user_id: int, days: int) -> VipMembership:
    """开通或续费 VIP。

    续费规则：当前 VIP 有效则 expire_at += days；否则 start_at=now, expire_at=now+days。
    """
    now = datetime.utcnow()
    existing = await _get_active_vip(db, user_id)
    if existing:
        existing.expire_at = existing.expire_at + timedelta(days=days)
        await db.flush()
        return existing

    vip = VipMembership(
        user_id=user_id,
        level="vip",
        start_at=now,
        expire_at=now + timedelta(days=days),
        status="active",
    )
    db.add(vip)
    await db.flush()
    return vip


async def _get_active_vip(db: AsyncSession, user_id: int) -> VipMembership | None:
    now = datetime.utcnow()
    return (await db.execute(
        select(VipMembership).where(
            VipMembership.user_id == user_id,
            VipMembership.status == "active",
            VipMembership.expire_at > now,
        ).order_by(VipMembership.expire_at.desc()).limit(1)
    )).scalar_one_or_none()


async def get_user_orders(db: AsyncSession, user_id: int, limit: int = 20) -> list[dict]:
    rows = (await db.execute(
        select(VipOrder).where(VipOrder.user_id == user_id)
        .order_by(VipOrder.id.desc()).limit(limit)
    )).scalars().all()
    return [_order_to_dict(r) for r in rows]


async def get_order_detail(db: AsyncSession, user_id: int,
                           order_no: str) -> dict | None:
    """IDOR 防护：仅返回属于该 user_id 的订单。"""
    order = (await db.execute(
        select(VipOrder).where(
            VipOrder.order_no == order_no,
            VipOrder.user_id == user_id,
        ).limit(1)
    )).scalar_one_or_none()
    if not order:
        return None
    vip = await _get_active_vip(db, user_id)
    return {
        **_order_to_dict(order),
        "vip_active": vip is not None,
        "vip_expire_at": int(vip.expire_at.timestamp()) if vip else None,
    }


def _order_to_dict(o: VipOrder) -> dict:
    return {
        "order_no": o.order_no,
        "plan": o.plan,
        "amount": float(o.amount),
        "status": o.status,
        "created_at": int(o.created_at.timestamp()),
        "paid_at": int(o.paid_at.timestamp()) if o.paid_at else None,
    }
