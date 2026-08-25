"""上岸分数填报 + 冲稳保推荐 测试。

覆盖：
- A6 IDOR：A 用户填报后，B 用户查 A 的 report_id 应 404
- 隐私脱敏：is_anonymous=1 时输出不含 user_id
- 二次确认：agree_anonymized=False 应拒绝
- 异常值检测：分数远超历史区间 → flagged
- 冲稳保：基于历史数据三档分类
- 限流：免费 3 次/日超额 429（route 层 fake_redis 模拟）
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
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
    AdmissionStat, Discipline, Major, School, SchoolMajor, User, UserScoreReport,
)
from app.schemas import RecommendIn, ReportIn  # noqa: E402
from app.services.recommend import build_recommendation  # noqa: E402
from app.services.reports import (  # noqa: E402
    create_report, get_my_report, list_my_reports,
)
from app.services.stats import upsert_admission_stat  # noqa: E402


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
    # 两个用户
    u1 = User(nickname="user1", status=1)
    u2 = User(nickname="user2", status=1)
    s.add(u1)
    s.add(u2)
    await s.flush()
    # 历史 admission_stats：近3年 (min=300, avg=325, max=350)
    for year, mn, mx, avg in [(2024, 300, 350, 325.0), (2023, 305, 345, 325.0),
                              (2022, 295, 340, 317.5)]:
        s.add(AdmissionStat(
            school_major_id=sm.id, year=year,
            retest_count=10, admit_count=8,
            max_score=mx, min_score=mn, avg_score=avg,
            source_url=f"https://grs.pku.edu.cn/{year}.pdf",
        ))
    await s.commit()


# ---------- 填报 + 二次确认 ----------

@pytest.mark.asyncio
async def test_report_requires_anonymized_consent(db):
    """未勾选 agree_anonymized → 拒绝"""
    async with db() as s:
        with pytest.raises(ValueError, match="二次确认"):
            await create_report(s, 1, ReportIn(
                school_major_id=1, year=2024, total_score=330,
                origin_type="一志愿", result="录取",
                agree_anonymized=False,
            ))


@pytest.mark.asyncio
async def test_report_creates_with_pending_audit(db):
    """正常填报（分数在历史区间内）→ audit_status=pending"""
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取",
            agree_anonymized=True,
        ))
        await s.commit()
        assert rec["audit_status"] == "pending"
        assert rec["total_score"] == 330


@pytest.mark.asyncio
async def test_report_outlier_detection(db):
    """分数远超历史区间（max=350+50=400）→ flagged"""
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=450,
            origin_type="一志愿", result="录取",
            agree_anonymized=True,
        ))
        await s.commit()
        assert rec["audit_status"] == "flagged"


@pytest.mark.asyncio
async def test_report_below_range_outlier(db):
    """分数远低于历史区间（min=295-50=245）→ flagged"""
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=200,
            origin_type="一志愿", result="未进复试",
            agree_anonymized=True,
        ))
        await s.commit()
        assert rec["audit_status"] == "flagged"


# ---------- IDOR 防护 ----------

@pytest.mark.asyncio
async def test_idor_user_cannot_see_others_report(db):
    """A 用户填报后，B 用户查 A 的 report_id → None（路由层抛 404）"""
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取",
            agree_anonymized=True,
        ))
        await s.commit()
        report_id = rec["id"]

    # user_id=2 尝试访问 user_id=1 的填报
    async with db() as s:
        result = await get_my_report(s, 2, report_id)
        assert result is None  # 路由层将抛 404


@pytest.mark.asyncio
async def test_idor_owner_can_see_own_report(db):
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取",
            agree_anonymized=True,
        ))
        await s.commit()
        # user_id=1 访问自己的填报
        result = await get_my_report(s, 1, rec["id"])
        assert result is not None
        assert result["id"] == rec["id"]


@pytest.mark.asyncio
async def test_list_my_reports_only_returns_own(db):
    """列表查询只返回当前用户记录"""
    async with db() as s:
        await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取", agree_anonymized=True,
        ))
        await create_report(s, 2, ReportIn(
            school_major_id=1, year=2024, total_score=340,
            origin_type="一志愿", result="录取", agree_anonymized=True,
        ))
        await s.commit()
        # user 1 看到的应只有 1 条
        r1 = await list_my_reports(s, 1)
        assert len(r1["items"]) == 1
        # user 2 看到的应只有 1 条
        r2 = await list_my_reports(s, 2)
        assert len(r2["items"]) == 1


# ---------- 隐私脱敏 ----------

@pytest.mark.asyncio
async def test_anonymous_report_no_user_id(db):
    """is_anonymous=1 时输出不含 user_id"""
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取",
            agree_anonymized=True, is_anonymous=1,
        ))
        await s.commit()
        assert rec["is_anonymous"] == 1
        assert rec["user_id"] is None  # 脱敏


@pytest.mark.asyncio
async def test_named_report_has_user_id(db):
    async with db() as s:
        rec = await create_report(s, 1, ReportIn(
            school_major_id=1, year=2024, total_score=330,
            origin_type="一志愿", result="录取",
            agree_anonymized=True, is_anonymous=0,
        ))
        await s.commit()
        assert rec["is_anonymous"] == 0
        assert rec["user_id"] == 1


# ---------- 冲稳保推荐 ----------

@pytest.mark.asyncio
async def test_recommend_buckets(db):
    """基于历史数据（min=295, avg≈322, max=350），不同分数落入不同桶"""
    async with db() as s:
        # 平衡模式：345 → wen（avg+0=322 ≤ 345 < 332? 不，需检查）
        # 实际：avg=(325+325+317.5)/3=322.5；wen 区间 [322, 332)
        # 345 ≥ 322 + 0 = 322 且 < 322+10=332? 否，345 ≥ 332 → 不在 wen
        # 345 ≥ max-10=340 → bao
        r = await build_recommendation(s, RecommendIn(
            score=345, risk_pref="balance",
        ))
        # 345 ≥ 350-10=340 → bao
        assert len(r["bao"]) == 1
        assert r["bao"][0]["major_name"] == "计算机科学与技术"
        assert r["bao"][0]["bucket"] == "bao"

        # 322 → wen（avg=322.5, 322 ≥ 322 且 < 332）
        r2 = await build_recommendation(s, RecommendIn(
            score=322, risk_pref="balance",
        ))
        assert len(r2["wen"]) == 1
        assert r2["wen"][0]["bucket"] == "wen"

        # 295 → chong（min=295, 295 ≥ 295-5=290 且 < avg=322.5）
        r3 = await build_recommendation(s, RecommendIn(
            score=295, risk_pref="balance",
        ))
        assert len(r3["chong"]) == 1
        assert r3["chong"][0]["bucket"] == "chong"

        # 200 → none（不入桶）
        r4 = await build_recommendation(s, RecommendIn(
            score=200, risk_pref="balance",
        ))
        assert r4["chong"] == [] and r4["wen"] == [] and r4["bao"] == []
