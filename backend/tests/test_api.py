"""API 与检索行为测试（基于内存 SQLite + Fake Redis，避免依赖外部服务）。

覆盖：
- 院校检索：游标分页、关键词 LIKE 转义（A10 SQL 注入映射）
- 院校详情 404
- 复试线：免费近1年 / VIP近5年（A7 鉴权映射）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test_secret_at_least_32_bytes_long_enough_xxx")
os.environ.setdefault("WECHAT_APP_ID", "")
os.environ.setdefault("WECHAT_APP_SECRET", "")

from app.database import Base  # noqa: E402
from app.models import (  # noqa: E402
    Discipline, Major, ScoreLine, School, SchoolMajor,
)
from app.schemas import MajorIn, ScoreLineIn, SchoolIn  # noqa: E402
from app.services import search as search_svc  # noqa: E402


class _FakeRedis:
    """最小可用假 Redis：仅 get/set/delete，全内存 dict。"""
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


@pytest_asyncio.fixture
async def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(search_svc, "redis_client", fake, raising=True)
    return fake


@pytest_asyncio.fixture
async def db():
    """每个测试一个全新的内存 SQLite + 种子数据。"""
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
        code="081200", name="计算机科学与技术", discipline_id=disc.id, degree_type="学硕",
    )
    s.add(major)
    await s.flush()
    sm = SchoolMajor(school_id=school.id, major_id=major.id, college_name="信息科学技术学院")
    s.add(sm)
    await s.flush()
    for year, total in [(2024, 320), (2023, 310), (2022, 300), (2021, 295), (2020, 290)]:
        s.add(ScoreLine(
            school_major_id=sm.id, year=year, line_type="college",
            total_score=total, source_url="https://grs.pku.edu.cn/x.pdf",
        ))
    await s.commit()


# ---------- 院校检索 ----------

@pytest.mark.asyncio
async def test_school_search_keyword_like_escape(fake_redis, db):
    """LIKE 转义：搜索含 % 与 _ 的关键词不应触发通配或注入（A10）"""
    async with db() as s:
        r = await search_svc.search_schools(s, SchoolIn(keyword="北京"))
        assert len(r["items"]) == 1
        assert r["items"][0]["name"] == "北京大学"
        # 通配字符作为字面量
        r2 = await search_svc.search_schools(s, SchoolIn(keyword="%北京_"))
        assert r2["items"] == []
        # 游标分页
        r3 = await search_svc.search_schools(s, SchoolIn(limit=1))
        assert len(r3["items"]) == 1


@pytest.mark.asyncio
async def test_school_detail_404(fake_redis, db):
    async with db() as s:
        assert await search_svc.get_school_detail(s, 99999) is None
        d = await search_svc.get_school_detail(s, 1)
        assert d is not None and d["name"] == "北京大学"


@pytest.mark.asyncio
async def test_school_majors(fake_redis, db):
    async with db() as s:
        items = await search_svc.list_school_majors(s, 1)
        assert len(items) == 1
        assert items[0]["major_code"] == "081200"
        assert items[0]["college_name"] == "信息科学技术学院"


# ---------- 专业检索 ----------

@pytest.mark.asyncio
async def test_major_search(fake_redis, db):
    async with db() as s:
        r = await search_svc.search_majors(s, MajorIn(keyword="计算机"))
        assert len(r["items"]) == 1
        assert r["items"][0]["code"] == "081200"
        # 学位类型筛选
        r2 = await search_svc.search_majors(s, MajorIn(degree_type="专硕"))
        assert r2["items"] == []
        r3 = await search_svc.search_majors(s, MajorIn(degree_type="学硕"))
        assert len(r3["items"]) == 1


# ---------- 复试线：免费 vs VIP ----------

@pytest.mark.asyncio
async def test_score_lines_free_vs_vip(fake_redis, db):
    """A7：免费仅近 1 年，VIP 近 5 年"""
    async with db() as s:
        # 免费用户：近 1 年（2024）
        r = await search_svc.list_score_lines(s, ScoreLineIn(school_id=1), is_vip=False)
        years = [x["year"] for x in r["items"]]
        assert years == [2024]
        # VIP：近 5 年
        r2 = await search_svc.list_score_lines(s, ScoreLineIn(school_id=1), is_vip=True)
        years2 = sorted([x["year"] for x in r2["items"]], reverse=True)
        assert years2 == [2024, 2023, 2022, 2021, 2020]


@pytest.mark.asyncio
async def test_score_lines_filter_by_year(fake_redis, db):
    async with db() as s:
        r = await search_svc.list_score_lines(
            s, ScoreLineIn(school_id=1, year=2022), is_vip=False,
        )
        assert [x["year"] for x in r["items"]] == [2022]
