"""VIP 路由级 HTTP 测试：创建订单 → 模拟支付 → VIP 自动开通 → 鉴权可见。"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test_secret_at_least_32_bytes_long_enough_xxx")
os.environ.setdefault("WECHAT_APP_ID", "")
os.environ.setdefault("WECHAT_APP_SECRET", "")

from app.database import Base  # noqa: E402
from app.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, WechatAccount  # noqa: E402
from app.core import create_access_token  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, k): return self.store.get(k)
    async def set(self, k, v, ex=None): self.store[k] = v; return True
    async def delete(self, k): return self.store.pop(k, None) is not None
    async def ping(self): return True


@pytest.fixture
def client():
    fake = _FakeRedis()
    import app.services.search as mod_search
    import app.core.ratelimit as mod_rl
    mod_search.redis_client = fake
    mod_rl.redis_client = fake

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    import asyncio

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sm() as s:
            u = User(nickname="user1", status=1)
            s.add(u)
            await s.flush()
            s.add(WechatAccount(user_id=u.id, openid="openid_user1"))
            await s.commit()

    asyncio.run(_setup())

    async def _override_get_db():
        async with sm() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, sm
    app.dependency_overrides.clear()


def _token(client_sm):
    c, sm = client_sm
    import asyncio
    from sqlalchemy import select

    async def _get():
        async with sm() as s:
            u = (await s.execute(select(User).where(User.nickname == "user1"))).scalar_one()
            return u.id

    uid = asyncio.run(_get())
    tok, _ = create_access_token(uid)
    return tok


def test_vip_plans(client):
    c, _ = client
    r = c.get("/api/v1/vip/plans")
    assert r.status_code == 200
    plans = r.json()
    assert len(plans) == 3
    plan_keys = {p["plan"] for p in plans}
    assert plan_keys == {"monthly", "quarterly", "yearly"}


def test_create_order_and_simulate_pay(client):
    """创建订单 → 模拟支付 → VIP 自动开通"""
    c, _ = client
    h = {"Authorization": f"Bearer {_token(client)}"}

    # 创建订单
    r = c.post("/api/v1/vip/orders", json={"plan": "monthly"}, headers=h)
    assert r.status_code == 200
    body = r.json()["data"]
    order_no = body["order_no"]
    assert body["status"] == "pending"
    assert body["payment_params"]["_demo"] is True

    # 此时 advanced-example 应 403（未开通）
    r2 = c.get("/api/v1/vip/advanced-example", headers=h)
    assert r2.status_code == 403

    # 模拟支付
    r3 = c.post(f"/api/v1/vip/orders/{order_no}/simulate-pay",
                json={"paid": True}, headers=h)
    assert r3.status_code == 200
    pay_result = r3.json()["data"]
    assert pay_result["ok"] is True
    assert pay_result["vip_expire_at"] is not None

    # 此时 advanced-example 应 200
    r4 = c.get("/api/v1/vip/advanced-example", headers=h)
    assert r4.status_code == 200

    # 订单详情显示 vip_active=True
    r5 = c.get(f"/api/v1/vip/orders/{order_no}", headers=h)
    assert r5.status_code == 200
    detail = r5.json()["data"]
    assert detail["status"] == "paid"
    assert detail["vip_active"] is True


def test_simulate_pay_idempotent(client):
    """重复模拟支付 → 幂等返回"""
    c, _ = client
    h = {"Authorization": f"Bearer {_token(client)}"}

    r = c.post("/api/v1/vip/orders", json={"plan": "monthly"}, headers=h)
    order_no = r.json()["data"]["order_no"]

    r1 = c.post(f"/api/v1/vip/orders/{order_no}/simulate-pay",
                json={"paid": True}, headers=h)
    assert r1.status_code == 200
    first_expire = r1.json()["data"]["vip_expire_at"]

    r2 = c.post(f"/api/v1/vip/orders/{order_no}/simulate-pay",
                json={"paid": True}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["data"]["msg"] == "订单已支付（幂等）"
    assert r2.json()["data"]["vip_expire_at"] == first_expire


def test_cancel_order_via_simulate_pay(client):
    c, _ = client
    h = {"Authorization": f"Bearer {_token(client)}"}

    r = c.post("/api/v1/vip/orders", json={"plan": "monthly"}, headers=h)
    order_no = r.json()["data"]["order_no"]

    r2 = c.post(f"/api/v1/vip/orders/{order_no}/simulate-pay",
                json={"paid": False}, headers=h)
    assert r2.status_code == 200

    # 取消后再模拟支付应失败
    r3 = c.post(f"/api/v1/vip/orders/{order_no}/simulate-pay",
                json={"paid": True}, headers=h)
    assert r3.status_code == 400


def test_idor_cannot_see_others_order(client):
    """需要第二个用户：直接 GET 一个不属于自己的订单 → 404"""
    c, _ = client
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = c.post("/api/v1/vip/orders", json={"plan": "monthly"}, headers=h)
    order_no = r.json()["data"]["order_no"]

    # 创建第二个用户 + token
    import asyncio
    from sqlalchemy import select

    async def _add_user2(sm):
        async with sm() as s:
            u2 = User(nickname="user2", status=1)
            s.add(u2)
            await s.commit()

    # 取 sm
    _, sm = client
    asyncio.run(_add_user2(sm))

    async def _get_user2_token():
        async with sm() as s:
            u2 = (await s.execute(select(User).where(User.nickname == "user2"))).scalar_one()
            tok, _ = create_access_token(u2.id)
            return tok

    tok2 = asyncio.run(_get_user2_token())
    h2 = {"Authorization": f"Bearer {tok2}"}

    # user2 尝试查看 user1 的订单 → 404
    r2 = c.get(f"/api/v1/vip/orders/{order_no}", headers=h2)
    assert r2.status_code == 404


def test_unknown_plan_rejected(client):
    c, _ = client
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = c.post("/api/v1/vip/orders", json={"plan": "weekly"}, headers=h)
    assert r.status_code == 422  # pydantic 正则拒绝


def test_orders_unauthorized_401(client):
    c, _ = client
    r = c.post("/api/v1/vip/orders", json={"plan": "monthly"})
    assert r.status_code == 401
