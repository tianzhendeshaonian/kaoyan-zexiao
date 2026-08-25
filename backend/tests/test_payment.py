"""VIP 订单 + 支付状态机 + 幂等回调 + 自动开通测试。

覆盖：
- 创建订单（pending）
- 状态机：pending → paid（自动开通 VIP）
- 幂等：同 order_no 重复支付回调只开通一次
- 续费：已有 VIP 时再次支付 → expire_at 在原基础上累加
- IDOR：B 用户查 A 的订单 → 404
- 取消订单：pending → cancelled → 再支付应失败
- 套餐校验：未知套餐 → 400
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test_secret_at_least_32_bytes_long_enough_xxx")
os.environ.setdefault("WECHAT_APP_ID", "")
os.environ.setdefault("WECHAT_APP_SECRET", "")

from app.database import Base  # noqa: E402
from app.models import User, VipMembership, VipOrder, WechatAccount  # noqa: E402
from app.services.vip import (  # noqa: E402
    _get_active_vip,
    cancel_expired_orders,
    create_order,
    get_order_detail,
    get_user_orders,
    handle_payment_success,
)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sm() as s:
        await _seed(s)
    try:
        yield sm
    finally:
        await engine.dispose()


async def _seed(s: AsyncSession):
    u1 = User(nickname="user1", status=1)
    u2 = User(nickname="user2", status=1)
    s.add(u1)
    s.add(u2)
    await s.flush()
    # 给 user1 加 wechat_account（openid 用于支付下单）
    s.add(WechatAccount(user_id=u1.id, openid="openid_user1"))
    await s.commit()


# ---------- 订单创建 ----------

@pytest.mark.asyncio
async def test_create_order_pending(db):
    async with db() as s:
        result = await create_order(s, 1, "monthly", "127.0.0.1", "https://x/notify")
        await s.commit()
        assert result["status"] == "pending"
        assert result["plan"] == "monthly"
        assert result["amount"] == 19.9
        assert result["payment_params"]["_demo"] is True  # demo 模式


@pytest.mark.asyncio
async def test_create_order_reuses_pending(db):
    """同一用户同套餐 pending 订单 → 复用"""
    async with db() as s:
        r1 = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        r2 = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        assert r1["order_no"] == r2["order_no"]


@pytest.mark.asyncio
async def test_create_order_unknown_plan(db):
    async with db() as s:
        with pytest.raises(ValueError, match="套餐不存在"):
            await create_order(s, 1, "weekly", "127.0.0.1", "")


# ---------- 状态机：pending → paid + 自动开通 ----------

@pytest.mark.asyncio
async def test_payment_success_activates_vip(db):
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        order_no = r["order_no"]

        # 模拟支付成功
        result = await handle_payment_success(s, order_no, "txn_1")
        await s.commit()
        assert result["ok"] is True
        assert result["msg"] == "支付成功"
        assert result["vip_expire_at"] is not None

        # 订单状态 = paid
        order = (await s.execute(
            select(VipOrder).where(VipOrder.order_no == order_no)
        )).scalar_one()
        assert order.status == "paid"
        assert order.paid_at is not None

        # VIP 已开通，30 天后过期
        vip = await _get_active_vip(s, 1)
        assert vip is not None
        assert vip.level == "vip"
        delta = (vip.expire_at - datetime.utcnow()).days
        assert 29 <= delta <= 30


# ---------- 幂等：重复回调只开通一次 ----------

@pytest.mark.asyncio
async def test_payment_idempotent(db):
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        order_no = r["order_no"]

        # 首次支付
        r1 = await handle_payment_success(s, order_no, "txn_1")
        await s.commit()
        assert r1["ok"] is True
        first_expire = r1["vip_expire_at"]

        # 再次回调（同 order_no，不同 transaction_id 也视为幂等）
        r2 = await handle_payment_success(s, order_no, "txn_2")
        await s.commit()
        assert r2["ok"] is True
        assert r2["msg"] == "订单已支付（幂等）"
        # expire_at 不变（未续费）
        assert r2["vip_expire_at"] == first_expire

        # 仍是单条 VIP 记录
        vips = (await s.execute(
            select(VipMembership).where(VipMembership.user_id == 1)
        )).scalars().all()
        assert len(vips) == 1


# ---------- 续费 ----------

@pytest.mark.asyncio
async def test_renewal_extends_expire(db):
    """已有 VIP → 再次支付（新订单）→ expire_at += days"""
    async with db() as s:
        # 第一次开通月卡
        r1 = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        first = await handle_payment_success(s, r1["order_no"], "t1")
        await s.commit()
        first_expire = first["vip_expire_at"]

        # 第二次购买年卡
        r2 = await create_order(s, 1, "yearly", "127.0.0.1", "")
        await s.commit()
        second = await handle_payment_success(s, r2["order_no"], "t2")
        await s.commit()
        second_expire = second["vip_expire_at"]

        # 续费后 expire_at 应在原 expire_at + 365 天附近
        delta_days = (second_expire - first_expire) / 86400
        assert 364 <= delta_days <= 366


# ---------- 取消订单 ----------

@pytest.mark.asyncio
async def test_cancel_then_pay_fails(db):
    """pending → cancelled → 再支付应失败"""
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        order_no = r["order_no"]

        # 取消
        order = (await s.execute(
            select(VipOrder).where(VipOrder.order_no == order_no)
        )).scalar_one()
        order.status = "cancelled"
        await s.commit()

        # 再支付
        result = await handle_payment_success(s, order_no, "t_late")
        await s.commit()
        assert result["ok"] is False
        assert "cancelled" in result["msg"]


@pytest.mark.asyncio
async def test_cancel_expired_orders(db):
    """15 分钟未支付的 pending → cancelled"""
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        # 手动把 created_at 改为 20 分钟前
        order = (await s.execute(
            select(VipOrder).where(VipOrder.order_no == r["order_no"])
        )).scalar_one()
        order.created_at = datetime.utcnow() - timedelta(minutes=20)
        await s.commit()

    async with db() as s:
        n = await cancel_expired_orders(s)
        await s.commit()
        assert n == 1
        order = (await s.execute(
            select(VipOrder).where(VipOrder.order_no == r["order_no"])
        )).scalar_one()
        assert order.status == "cancelled"


# ---------- IDOR ----------

@pytest.mark.asyncio
async def test_idor_other_user_cannot_see_order(db):
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        # user_id=2 查 user_id=1 的订单 → None
        detail = await get_order_detail(s, 2, r["order_no"])
        assert detail is None


@pytest.mark.asyncio
async def test_idor_owner_can_see_order(db):
    async with db() as s:
        r = await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        detail = await get_order_detail(s, 1, r["order_no"])
        assert detail is not None
        assert detail["order_no"] == r["order_no"]
        assert detail["vip_active"] is False  # 未支付


# ---------- 我的订单列表 ----------

@pytest.mark.asyncio
async def test_my_orders_list(db):
    async with db() as s:
        await create_order(s, 1, "monthly", "127.0.0.1", "")
        await s.commit()
        await create_order(s, 1, "yearly", "127.0.0.1", "")
        await s.commit()
        # user 1 应有 2 条
        items = await get_user_orders(s, 1)
        assert len(items) == 2
        # user 2 应有 0 条
        items2 = await get_user_orders(s, 2)
        assert len(items2) == 0
