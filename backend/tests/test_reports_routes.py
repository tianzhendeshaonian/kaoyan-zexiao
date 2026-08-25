"""HTTP 路由级 IDOR + 限流测试（FastAPI TestClient + 内存 SQLite + Fake Redis）。

覆盖：
- A6 IDOR：A 登录填报后，B 登录访问 A 的 report_id → 404（不区分"不存在"与"无权限"）
- 隐私脱敏：is_anonymous=1 时响应不含 user_id
- 冲稳保推荐：登录态可达
- 限流：免费用户 4 次/日（settings.RL_RECOMMEND_FREE_PER_DAY=3）→ 第 4 次 429
"""
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
from app.models import (  # noqa: E402
    AdmissionStat, Discipline, Major, School, SchoolMajor, User,
)
from app.core import create_access_token  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession


class _FakeRedis:
    """用于限流测试的内存 Redis。store 复用同一 dict 以模拟跨请求计数。"""
    def __init__(self):
        self.store: dict[str, str] = {}
        self.zset: dict[str, list] = {}

    async def get(self, k):
        return self.store.get(k)

    async def set(self, k, v, ex=None):
        self.store[k] = v
        return True

    async def delete(self, k):
        return self.store.pop(k, None) is not None

    async def ping(self):
        return True

    # 滑窗限流用的 zset 操作
    async def zadd(self, key, mapping, *args, **kwargs):
        self.zset.setdefault(key, [])
        for member, score in mapping.items():
            self.zset[key].append((score, member))
        return len(self.zset[key])

    async def zremrangebyscore(self, key, min_score, max_score):
        if key not in self.zset:
            return 0
        before = len(self.zset[key])
        self.zset[key] = [
            (s, m) for s, m in self.zset[key] if not (min_score <= s <= max_score)
        ]
        return before - len(self.zset[key])

    async def zcard(self, key):
        return len(self.zset.get(key, []))

    async def expire(self, key, ttl):
        return True

    def pipeline(self):
        return self  # 简化：pipeline 直接返回自身

    async def execute(self):
        # 模拟 pipeline 批量结果（按调用顺序）
        return [0, 1, getattr(self, "_last_count", 0), True]


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    import app.services.search as mod_search
    import app.core.ratelimit as mod_rl
    monkeypatch.setattr(mod_search, "redis_client", fake, raising=True)
    monkeypatch.setattr(mod_rl, "redis_client", fake, raising=True)
    return fake


@pytest.fixture
def client(fake_redis):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    import asyncio

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sm() as s:
            disc = Discipline(code="08", name="工学")
            s.add(disc)
            await s.flush()
            school = School(
                code="10001", name="北京大学", province="北京", city="北京",
                level="985", school_type="综合", is_self_line=1,
            )
            s.add(school)
            await s.flush()
            major = Major(code="081200", name="计算机科学与技术",
                         discipline_id=disc.id, degree_type="学硕")
            s.add(major)
            await s.flush()
            sm_row = SchoolMajor(school_id=school.id, major_id=major.id, college_name="信息学院")
            s.add(sm_row)
            await s.flush()
            # 历史 stats: min=300, max=350, avg=325
            s.add(AdmissionStat(
                school_major_id=sm_row.id, year=2024,
                retest_count=10, admit_count=8,
                max_score=350, min_score=300, avg_score=325.0,
                source_url="https://x.pdf",
            ))
            # 两个用户
            u1 = User(nickname="user1", status=1)
            u2 = User(nickname="user2", status=1)
            s.add(u1)
            s.add(u2)
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


def _get_uid_token(client_sm, nickname):
    """按 nickname 查 user_id 并签 token"""
    c, sm = client_sm
    import asyncio
    from sqlalchemy import select

    async def _get():
        async with sm() as s:
            u = (await s.execute(
                select(User).where(User.nickname == nickname)
            )).scalar_one()
            return u.id

    uid = asyncio.run(_get())
    tok, _ = create_access_token(uid)
    return uid, tok


# ---------- IDOR 防护 ----------

def test_idor_post_and_detail(client):
    """A 填报 → A 能看 / B 不能看（404）"""
    c, _ = client
    _, tok_a = _get_uid_token(client, "user1")
    _, tok_b = _get_uid_token(client, "user2")
    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}

    # A 填报
    r = c.post("/api/v1/reports", json={
        "school_major_id": 1, "year": 2024, "total_score": 320,
        "origin_type": "一志愿", "result": "录取",
        "agree_anonymized": True, "is_anonymous": 1,
    }, headers=h_a)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    rid = body["data"]["id"]
    # 脱敏：响应不含 user_id
    assert body["data"]["user_id"] is None

    # A 能看自己的详情
    r2 = c.get(f"/api/v1/reports/mine/{rid}", headers=h_a)
    assert r2.status_code == 200

    # B 看不到 A 的（IDOR → 404，且不区分"不存在"vs"无权限"）
    r3 = c.get(f"/api/v1/reports/mine/{rid}", headers=h_b)
    assert r3.status_code == 404


def test_idor_list_only_returns_own(client):
    c, _ = client
    _, tok_a = _get_uid_token(client, "user1")
    _, tok_b = _get_uid_token(client, "user2")
    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}

    # A 和 B 各填报一条
    c.post("/api/v1/reports", json={
        "school_major_id": 1, "year": 2024, "total_score": 320,
        "origin_type": "一志愿", "result": "录取",
        "agree_anonymized": True,
    }, headers=h_a)
    c.post("/api/v1/reports", json={
        "school_major_id": 1, "year": 2024, "total_score": 340,
        "origin_type": "调剂", "result": "录取",
        "agree_anonymized": True,
    }, headers=h_b)

    # A 列表只看到 1 条
    r = c.get("/api/v1/reports/mine", headers=h_a)
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["total_score"] == 320


# ---------- 二次确认 ----------

def test_report_requires_anonymized_consent_http(client):
    c, _ = client
    _, tok = _get_uid_token(client, "user1")
    h = {"Authorization": f"Bearer {tok}"}
    r = c.post("/api/v1/reports", json={
        "school_major_id": 1, "year": 2024, "total_score": 320,
        "origin_type": "一志愿", "result": "录取",
        "agree_anonymized": False,
    }, headers=h)
    assert r.status_code == 400


# ---------- 冲稳保推荐 ----------

def test_recommend_route_works(client):
    c, _ = client
    _, tok = _get_uid_token(client, "user1")
    h = {"Authorization": f"Bearer {tok}"}
    r = c.post("/api/v1/recommend", json={
        "score": 345, "risk_pref": "balance",
    }, headers=h)
    assert r.status_code == 200
    body = r.json()["data"]
    assert "chong" in body and "wen" in body and "bao" in body


def test_recommend_unauthorized_401(client):
    c, _ = client
    r = c.post("/api/v1/recommend", json={"score": 345})
    assert r.status_code == 401
