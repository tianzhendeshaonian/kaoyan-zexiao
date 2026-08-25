"""FastAPI 路由级集成测试：用 TestClient + 内存 SQLite + FakeRedis，全栈跑通。

覆盖：
- 院校检索 200 / 详情 404
- VIP 路由无登录 401 / 普通登录 403 / VIP 登录 200（A7 VIP 绕过）
- 复试线匿名可达、登录后按 VIP 判定
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
    Discipline, Major, ScoreLine, School, SchoolMajor, User, VipMembership,
)
from app.core import create_access_token  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, k):
        return self.store.get(k)

    async def set(self, k, v, ex=None):
        self.store[k] = v
        return True

    async def delete(self, k):
        return self.store.pop(k, None) is not None

    async def ping(self):
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    # 替换所有用到 redis_client 的模块
    import app.services.search as mod_search
    import app.core.ratelimit as mod_rl
    monkeypatch.setattr(mod_search, "redis_client", fake, raising=True)
    monkeypatch.setattr(mod_rl, "redis_client", fake, raising=True)
    return fake


@pytest.fixture
def client_and_sm(fake_redis):
    """内存 SQLite + 覆盖 get_db。返回 (TestClient, sessionmaker)。"""
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
            major = Major(
                code="081200", name="计算机科学与技术",
                discipline_id=disc.id, degree_type="学硕",
            )
            s.add(major)
            await s.flush()
            sm_row = SchoolMajor(
                school_id=school.id, major_id=major.id, college_name="信息学院",
            )
            s.add(sm_row)
            await s.flush()
            for year, total in [(2024, 320), (2023, 310), (2022, 300), (2021, 295), (2020, 290)]:
                s.add(ScoreLine(
                    school_major_id=sm_row.id, year=year, line_type="college",
                    total_score=total, source_url="https://grs.pku.edu.cn/x.pdf",
                ))
            # 普通用户 + VIP 用户
            u_normal = User(nickname="普通", status=1)
            u_vip = User(nickname="VIP", status=1)
            s.add(u_normal)
            s.add(u_vip)
            await s.flush()
            now = datetime.utcnow()
            s.add(VipMembership(
                user_id=u_vip.id, level="vip",
                start_at=now - timedelta(days=1),
                expire_at=now + timedelta(days=30),
                status="active",
            ))
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
    # lifespan 会触发 redis ping，用 fake
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, sm
    app.dependency_overrides.clear()


# ---------- 院校 ----------

def test_school_search_http(client_and_sm):
    c, _ = client_and_sm
    r = c.get("/api/v1/schools", params={"keyword": "北京"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["name"] == "北京大学"


def test_school_detail_404_http(client_and_sm):
    c, _ = client_and_sm
    r = c.get("/api/v1/schools/99999")
    assert r.status_code == 404


def test_school_majors_http(client_and_sm):
    c, _ = client_and_sm
    r = c.get("/api/v1/schools/1/majors")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 1
    assert items[0]["major_code"] == "081200"


# ---------- 专业 ----------

def test_major_search_http(client_and_sm):
    c, _ = client_and_sm
    r = c.get("/api/v1/majors", params={"keyword": "计算机"})
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1


# ---------- 复试线 ----------

def test_score_lines_anonymous_only_recent_year(client_and_sm):
    c, _ = client_and_sm
    r = c.get("/api/v1/score-lines", params={"school_id": 1})
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert [x["year"] for x in items] == [2024]


def test_score_lines_vip_sees_5_years(client_and_sm):
    c, sm = client_and_sm
    import asyncio

    async def _get_vip_user_id():
        async with sm() as s:
            u = (await s.execute(
                __import__("sqlalchemy").select(User).where(User.nickname == "VIP")
            )).scalar_one()
            return u.id

    uid = asyncio.run(_get_vip_user_id())
    tok, _ = create_access_token(uid)
    r = c.get("/api/v1/score-lines", params={"school_id": 1},
              headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    years = sorted([x["year"] for x in items], reverse=True)
    assert years == [2024, 2023, 2022, 2021, 2020]


# ---------- VIP 路由鉴权 ----------

def test_vip_route_no_token_401(client_and_sm):
    """A7：未登录访问 VIP 接口 → 401（不是 200）"""
    c, _ = client_and_sm
    r = c.get("/api/v1/vip/advanced-example")
    assert r.status_code == 401


def test_vip_route_normal_user_403(client_and_sm):
    """A7：普通登录访问 VIP 接口 → 403（后端守卫，不能靠前端隐藏）"""
    c, sm = client_and_sm
    import asyncio

    async def _get_normal_uid():
        async with sm() as s:
            u = (await s.execute(
                __import__("sqlalchemy").select(User).where(User.nickname == "普通")
            )).scalar_one()
            return u.id

    uid = asyncio.run(_get_normal_uid())
    tok, _ = create_access_token(uid)
    r = c.get("/api/v1/vip/advanced-example",
              headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_vip_route_vip_user_200(client_and_sm):
    c, sm = client_and_sm
    import asyncio

    async def _get_vip_uid():
        async with sm() as s:
            u = (await s.execute(
                __import__("sqlalchemy").select(User).where(User.nickname == "VIP")
            )).scalar_one()
            return u.id

    uid = asyncio.run(_get_vip_uid())
    tok, _ = create_access_token(uid)
    r = c.get("/api/v1/vip/advanced-example",
              headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["code"] == 0
