"""复录比计算/聚合/脱敏 + 冲稳保算法。

对应 PRD §5.4 复录比、§5.6 冲稳保。
"""
from __future__ import annotations

from typing import Iterable, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AdmissionStat
from .pdf_parser import build_score_segments


# ================= 冲稳保 =================

RISK_DELTA = {
    "conservative": {"chong": 0, "wen": -3, "bao": -7},
    "balance":      {"chong": -5, "wen": 0,  "bao": -10},
    "aggressive":   {"chong": -8, "wen": +3, "bao": -13},
}


def classify(score: int, recent_min: int, recent_avg: int, recent_max: int,
             risk_pref: Literal["conservative", "balance", "aggressive"] = "balance") -> str:
    """
    参考 PRD §5.6：
      chong: ≥ 近3年最低分 - Δchong 且 < 平均分
      wen:   平均分 ≤ 分数 < 平均分 + 10
      bao:   ≥ 近3年最高分 - Δbao
    优先判断 bao → wen → chong → none
    """
    delta = RISK_DELTA[risk_pref]
    if score >= recent_max + delta["bao"]:
        return "bao"
    if score >= recent_avg + delta["wen"] and score < recent_avg + 10:
        return "wen"
    if score >= recent_min + delta["chong"] and score < recent_avg:
        return "chong"
    return "none"


# ================= 复录比 =================

async def compute_ratio_for_school_major(
    db: AsyncSession, school_major_id: int, is_vip: bool, limit: int = 5,
) -> list[dict]:
    """复录比列表（按年倒序）。

    免费用户：返回近 1 年 + 概览字段（无 score_segments 明细）。
    VIP 用户：返回近 5 年 + score_segments 明细。
    """
    stmt = (
        select(AdmissionStat)
        .where(AdmissionStat.school_major_id == school_major_id)
        .order_by(AdmissionStat.year.desc())
        .limit(1 if not is_vip else min(limit, 5))
    )
    rows = (await db.execute(stmt)).scalars().all()

    out = []
    for r in rows:
        ratio = round(r.admit_count / r.retest_count, 3) if r.retest_count else None
        item = {
            "school_major_id": r.school_major_id,
            "year": r.year,
            "retest_count": r.retest_count,
            "admit_count": r.admit_count,
            "ratio": ratio,
            "max_score": r.max_score,
            "min_score": r.min_score,
            "avg_score": float(r.avg_score) if r.avg_score is not None else None,
            "source_url": r.source_url,
        }
        if is_vip:
            item["score_segments"] = r.score_segments
        out.append(item)
    return out


async def upsert_admission_stat(
    db: AsyncSession,
    school_major_id: int,
    year: int,
    retest_count: int,
    admit_count: int,
    scores: Iterable[int],
    source_url: str,
) -> AdmissionStat:
    """从解析后的分数列表聚合一条 admission_stats（upsert）。

    分数段聚合走 build_score_segments（脱敏：仅区间与计数）。
    """
    scores = list(scores)
    existing = (
        await db.execute(
            select(AdmissionStat).where(
                AdmissionStat.school_major_id == school_major_id,
                AdmissionStat.year == year,
            )
        )
    ).scalar_one_or_none()

    max_score = max(scores) if scores else None
    min_score = min(scores) if scores else None
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    segments = build_score_segments(scores, step=10)

    if existing:
        existing.retest_count = retest_count
        existing.admit_count = admit_count
        existing.max_score = max_score
        existing.min_score = min_score
        existing.avg_score = avg_score
        existing.score_segments = segments
        existing.source_url = source_url
        await db.flush()
        return existing

    stat = AdmissionStat(
        school_major_id=school_major_id,
        year=year,
        retest_count=retest_count,
        admit_count=admit_count,
        max_score=max_score,
        min_score=min_score,
        avg_score=avg_score,
        score_segments=segments,
        source_url=source_url,
    )
    db.add(stat)
    await db.flush()
    return stat
