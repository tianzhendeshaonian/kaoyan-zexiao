"""冲稳保推荐服务（基于 stats.classify + 历史 admission_stats）。

对应 PRD §5.6：基于近3年复试线最低/平均/最高，结合用户分数与风险偏好，
将候选 school_major 三档分类输出。

限流：免费 3 次/日，VIP 无限（在路由层 recommend_rate_limit 实现）。
"""
from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AdmissionStat, Major, School, SchoolMajor
from ..schemas import RecommendIn, RecommendItem
from .stats import classify


async def build_recommendation(
    db: AsyncSession, p: RecommendIn,
) -> dict:
    """生成冲稳保推荐。"""
    # 1) 取候选 school_major 列表（按学科/省份过滤）
    sm_stmt = (
        select(SchoolMajor, Major, School)
        .join(Major, SchoolMajor.major_id == Major.id)
        .join(School, SchoolMajor.school_id == School.id)
    )
    conds = []
    if p.discipline_id:
        conds.append(Major.discipline_id == p.discipline_id)
    if p.province:
        conds.append(School.province == p.province)
    if conds:
        sm_stmt = sm_stmt.where(*conds)
    sm_stmt = sm_stmt.limit(p.top_n * 5)  # 取候选集后筛选
    sm_rows = (await db.execute(sm_stmt)).all()

    items: list[RecommendItem] = []
    for sm, m, s in sm_rows:
        # 2) 取近3年 admission_stats 的 min/avg/max
        stat_rows = (await db.execute(
            select(AdmissionStat).where(
                AdmissionStat.school_major_id == sm.id,
            ).order_by(AdmissionStat.year.desc()).limit(3)
        )).scalars().all()
        if len(stat_rows) < 1:
            continue  # 无历史数据，跳过（不能盲推）
        mins = [r.min_score for r in stat_rows if r.min_score is not None]
        maxs = [r.max_score for r in stat_rows if r.max_score is not None]
        avgs = [float(r.avg_score) for r in stat_rows if r.avg_score is not None]
        if not mins or not maxs or not avgs:
            continue
        recent_min = min(mins)
        recent_max = max(maxs)
        recent_avg = round(sum(avgs) / len(avgs))

        bucket = classify(
            p.score, recent_min, recent_avg, recent_max,
            risk_pref=p.risk_pref,  # type: ignore[arg-type]
        )
        if bucket == "none":
            continue

        # 复录比摘要
        latest = stat_rows[0]
        ratio = round(latest.admit_count / latest.retest_count, 3) if latest.retest_count else None
        items.append(RecommendItem(
            school_id=s.id, school_name=s.name,
            school_major_id=sm.id, major_code=m.code, major_name=m.name,
            year=latest.year,
            recent_min=recent_min, recent_avg=recent_avg, recent_max=recent_max,
            bucket=bucket,
            admit_count=latest.admit_count, retest_count=latest.retest_count,
            ratio=ratio,
        ))

    # 3) 按桶分组（每桶至多 top_n）
    chong = [it for it in items if it.bucket == "chong"][:p.top_n]
    wen = [it for it in items if it.bucket == "wen"][:p.top_n]
    bao = [it for it in items if it.bucket == "bao"][:p.top_n]

    return {
        "score": p.score,
        "risk_pref": p.risk_pref,
        "chong": [it.model_dump() for it in chong],
        "wen": [it.model_dump() for it in wen],
        "bao": [it.model_dump() for it in bao],
    }
