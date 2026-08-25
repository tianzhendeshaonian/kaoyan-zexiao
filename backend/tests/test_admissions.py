"""招生目录 + 复录比 + 统计聚合测试。"""
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
    AdmissionCatalog, AdmissionStat, Discipline, Major, School, SchoolMajor,
)
from app.services.search import list_admission_catalogs, list_admission_stats  # noqa: E402
from app.services.stats import compute_ratio_for_school_major, upsert_admission_stat  # noqa: E402


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


@pytest_asyncio.fixture
async def fake_redis(monkeypatch):
    fake = _FakeRedis()
    import app.services.search as mod
    monkeypatch.setattr(mod, "redis_client", fake, raising=True)
    return fake


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
    sm = SchoolMajor(school_id=school.id, major_id=major.id, college_name="信息学院")
    s.add(sm)
    await s.flush()
    # 招生目录：2024 + 2023
    s.add(AdmissionCatalog(
        school_major_id=sm.id, year=2024, direction="计算机技术",
        exam_subjects=["政治", "英语一", "数学一", "408"],
        planned_number=20, push_number=5,
        reference_books="《数据结构》严蔚敏",
        source_url="https://grs.pku.edu.cn/2024_catalog.pdf",
    ))
    s.add(AdmissionCatalog(
        school_major_id=sm.id, year=2023, direction="计算机技术",
        exam_subjects=["政治", "英语一", "数学一", "408"],
        planned_number=18, push_number=4,
        reference_books="《数据结构》严蔚敏",
        source_url="https://grs.pku.edu.cn/2023_catalog.pdf",
    ))
    await s.commit()


# ---------- 招生目录 ----------

@pytest.mark.asyncio
async def test_catalog_free_only_latest_year(fake_redis, db):
    """免费用户：仅最近一年"""
    async with db() as s:
        items = await list_admission_catalogs(
            s, school_major_id=1, is_vip=False,
        )
        assert len(items) == 1
        assert items[0]["year"] == 2024
        assert items[0]["planned_number"] == 20
        assert "408" in items[0]["exam_subjects"]


@pytest.mark.asyncio
async def test_catalog_vip_multi_years(fake_redis, db):
    """VIP：近 5 年"""
    async with db() as s:
        items = await list_admission_catalogs(
            s, school_major_id=1, is_vip=True,
        )
        assert len(items) == 2
        years = sorted([x["year"] for x in items], reverse=True)
        assert years == [2024, 2023]


# ---------- 复录比 upsert + 查询 ----------

@pytest.mark.asyncio
async def test_upsert_and_query_ratio(fake_redis, db):
    """先 upsert 一条 admission_stat，再分别按免费/VIP 查"""
    async with db() as s:
        scores = [380, 365, 350, 360, 370]
        stat = await upsert_admission_stat(
            s, school_major_id=1, year=2024,
            retest_count=5, admit_count=5, scores=scores,
            source_url="https://grs.pku.edu.cn/2024_admit.pdf",
        )
        await s.commit()
        assert stat.max_score == 380
        assert stat.min_score == 350
        assert stat.avg_score == round(sum(scores) / len(scores), 1)
        # score_segments 脱敏：仅区间与计数
        assert isinstance(stat.score_segments, list)
        assert all(set(s.keys()) == {"min", "max", "count"} for s in stat.score_segments)

    async with db() as s:
        # 免费用户：仅概览字段
        free_items = await compute_ratio_for_school_major(s, 1, is_vip=False)
        assert len(free_items) == 1
        free_item = free_items[0]
        assert free_item["ratio"] == 1.0
        assert "score_segments" not in free_item

        # VIP：含 score_segments 明细
        vip_items = await compute_ratio_for_school_major(s, 1, is_vip=True)
        assert len(vip_items) == 1
        assert "score_segments" in vip_items[0]
        assert vip_items[0]["score_segments"] is not None


@pytest.mark.asyncio
async def test_upsert_is_idempotent(fake_redis, db):
    """同一 (school_major_id, year) upsert 多次应更新而非新增"""
    async with db() as s:
        await upsert_admission_stat(
            s, school_major_id=1, year=2024,
            retest_count=3, admit_count=3, scores=[300, 310, 320],
            source_url="https://x.pdf",
        )
        await s.commit()
        # 再次 upsert 不同分数
        stat = await upsert_admission_stat(
            s, school_major_id=1, year=2024,
            retest_count=5, admit_count=5, scores=[350, 360, 370, 380, 390],
            source_url="https://y.pdf",
        )
        await s.commit()
        assert stat.max_score == 390
        assert stat.retest_count == 5

    from sqlalchemy import select
    async with db() as s:
        rows = (await s.execute(
            select(AdmissionStat).where(
                AdmissionStat.school_major_id == 1,
                AdmissionStat.year == 2024,
            )
        )).scalars().all()
        assert len(rows) == 1  # 唯一性保证不重复插入
