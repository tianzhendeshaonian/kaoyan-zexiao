"""院校 / 专业 / 历年复试线检索服务。

设计要点（对应 TECH_DESIGN.md §3 §7 与 CRAWLER_COMPLIANCE.md 安全清单）：
- 全程参数化/ORM 查询，绝不字符串拼接 SQL（A10）。
- 关键词 LIKE 走 SQLAlchemy `like()`，自动转义。
- 热点查询走 Redis 缓存：检索 5min、复试线 1h。
- 复试线对免费用户限制近 1 年、VIP 近 5 年（A7 由 require_vip 兜底）。
- IDOR：所有详情查询带 user 校验在调用方完成（A6）。
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import (
    AdmissionCatalog,
    AdmissionStat,
    Major,
    ScoreLine,
    School,
    SchoolMajor,
)
from ..redis_client import redis_client
from ..schemas import (
    MajorIn,
    ScoreLineIn,
    SchoolIn,
)


# ---------- 缓存工具 ----------

async def _cache_get(key: str) -> Any | None:
    raw = await redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def _cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        await redis_client.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except Exception:
        # 缓存失败不影响主流程
        pass


# ---------- 院校检索 ----------

async def search_schools(db: AsyncSession, p: SchoolIn) -> dict:
    """分页 + 多条件院校检索。

    返回: {"items": [...], "page": {"cursor":..., "next_cursor":..., "limit":..., "has_more":...}}
    """
    # 缓存键：基于参数指纹（不含 cursor，分页内复用）
    cache_key = (
        "schools:search:"
        f"{p.keyword}:{p.province}:{p.level}:{p.school_type}:{p.limit}:{p.cursor}"
    )
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(School)
    conds = []
    if p.keyword:
        # LIKE 已由 SQLAlchemy 参数化绑定，自动转义 % 与 _
        kw = p.keyword.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        conds.append(School.name.like(f"%{kw}%", escape="\\"))
    if p.province:
        conds.append(School.province == p.province)
    if p.level:
        conds.append(School.level == p.level)
    if p.school_type:
        conds.append(School.school_type == p.school_type)
    if p.cursor:
        conds.append(School.id > p.cursor)
    if conds:
        stmt = stmt.where(*conds)

    stmt = stmt.order_by(School.id.asc()).limit(p.limit + 1)
    rows = (await db.execute(stmt)).scalars().all()

    has_more = len(rows) > p.limit
    items = rows[:p.limit]
    next_cursor = items[-1].id if items and has_more else None

    # 增强列表项：最近 1 年复试线摘要（最多 1 条 subquery）
    out_items = []
    for s in items:
        sm_count = (
            await db.execute(
                select(func.count(SchoolMajor.id)).where(SchoolMajor.school_id == s.id)
            )
        ).scalar() or 0
        latest_line = (
            await db.execute(
                select(ScoreLine.total_score)
                .join(SchoolMajor, ScoreLine.school_major_id == SchoolMajor.id)
                .where(SchoolMajor.school_id == s.id)
                .order_by(ScoreLine.year.desc(), ScoreLine.id.desc())
                .limit(1)
            )
        ).scalar()
        out_items.append({
            "id": s.id, "code": s.code, "name": s.name, "province": s.province,
            "city": s.city, "level": s.level, "school_type": s.school_type,
            "is_self_line": s.is_self_line,
            "matched_major_count": int(sm_count),
            "latest_score_line": latest_line,
        })

    result = {
        "items": out_items,
        "page": {
            "cursor": p.cursor,
            "next_cursor": next_cursor,
            "limit": p.limit,
            "has_more": has_more,
        },
    }
    await _cache_set(cache_key, result, ttl=300)
    return result


async def get_school_detail(db: AsyncSession, school_id: int) -> dict | None:
    cache_key = f"schools:detail:{school_id}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached
    s = await db.get(School, school_id)
    if not s:
        return None
    result = {
        "id": s.id, "code": s.code, "name": s.name, "province": s.province,
        "city": s.city, "level": s.level, "school_type": s.school_type,
        "is_self_line": s.is_self_line, "logo_url": s.logo_url,
        "official_site": s.official_site, "graduate_site": s.graduate_site,
    }
    await _cache_set(cache_key, result, ttl=300)
    return result


async def list_school_majors(
    db: AsyncSession, school_id: int, keyword: str | None = None, limit: int = 50
) -> list[dict]:
    """院校下开设专业列表（含专业代码、学院、学科）。"""
    stmt = (
        select(SchoolMajor, Major)
        .join(Major, SchoolMajor.major_id == Major.id)
        .where(SchoolMajor.school_id == school_id)
    )
    if keyword:
        kw = keyword.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        stmt = stmt.where(
            (Major.name.like(f"%{kw}%", escape="\\")) |
            (SchoolMajor.college_name.like(f"%{kw}%", escape="\\"))
        )
    stmt = stmt.order_by(SchoolMajor.id.asc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": sm.id, "school_id": sm.school_id, "major_id": sm.major_id,
            "major_code": m.code, "major_name": m.name,
            "college_name": sm.college_name, "degree_type": m.degree_type,
            "discipline_id": m.discipline_id,
        }
        for sm, m in rows
    ]


# ---------- 专业检索 ----------

async def search_majors(db: AsyncSession, p: MajorIn) -> dict:
    cache_key = (
        "majors:search:"
        f"{p.keyword}:{p.discipline_id}:{p.degree_type}:{p.limit}:{p.cursor}"
    )
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(Major)
    conds = []
    if p.keyword:
        kw = p.keyword.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        conds.append(Major.name.like(f"%{kw}%", escape="\\"))
    if p.discipline_id:
        conds.append(Major.discipline_id == p.discipline_id)
    if p.degree_type:
        conds.append(Major.degree_type == p.degree_type)
    if p.cursor:
        conds.append(Major.id > p.cursor)
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(Major.id.asc()).limit(p.limit + 1)
    rows = (await db.execute(stmt)).scalars().all()
    has_more = len(rows) > p.limit
    items = rows[:p.limit]
    result = {
        "items": [
            {"id": m.id, "code": m.code, "name": m.name,
             "degree_type": m.degree_type, "discipline_id": m.discipline_id}
            for m in items
        ],
        "page": {
            "cursor": p.cursor,
            "next_cursor": items[-1].id if items and has_more else None,
            "limit": p.limit,
            "has_more": has_more,
        },
    }
    await _cache_set(cache_key, result, ttl=300)
    return result


# ---------- 历年复试线 ----------

async def list_score_lines(
    db: AsyncSession, p: ScoreLineIn, is_vip: bool
) -> dict:
    """历年复试线。

    免费：仅近 1 年；VIP：近 5 年（对应 PRD §6 与安全清单 A7）。
    """
    # 缓存键区分 VIP/免费
    cache_key = (
        "score_lines:"
        f"{p.school_id}:{p.major_id}:{p.school_major_id}:{p.year}:{p.line_type}:"
        f"{p.limit}:{'vip' if is_vip else 'free'}"
    )
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(ScoreLine)
    conds = []
    need_join = False
    if p.school_major_id:
        conds.append(ScoreLine.school_major_id == p.school_major_id)
    elif p.school_id:
        need_join = True
        conds.append(SchoolMajor.school_id == p.school_id)
        if p.major_id:
            conds.append(SchoolMajor.major_id == p.major_id)
    elif p.major_id:
        need_join = True
        conds.append(SchoolMajor.major_id == p.major_id)
    if need_join:
        stmt = stmt.join(SchoolMajor, ScoreLine.school_major_id == SchoolMajor.id)
    if p.year:
        conds.append(ScoreLine.year == p.year)
    elif not is_vip:
        # 免费：取最近 1 年；先查最近 year
        latest_year_stmt = select(func.max(ScoreLine.year))
        if need_join:
            latest_year_stmt = latest_year_stmt.join(
                SchoolMajor, ScoreLine.school_major_id == SchoolMajor.id
            )
        if conds:
            latest_year_stmt = latest_year_stmt.where(*conds)
        latest_year = (await db.execute(latest_year_stmt)).scalar()
        if latest_year:
            conds.append(ScoreLine.year == latest_year)
    else:
        # VIP：近 5 年（取 top5 distinct year）
        years_stmt = select(ScoreLine.year)
        if need_join:
            years_stmt = years_stmt.join(
                SchoolMajor, ScoreLine.school_major_id == SchoolMajor.id
            )
        if conds:
            years_stmt = years_stmt.where(*conds)
        years = list((await db.execute(
            years_stmt.distinct().order_by(ScoreLine.year.desc()).limit(5)
        )).scalars().all())
        if years:
            conds.append(ScoreLine.year.in_(years))

    if p.line_type:
        conds.append(ScoreLine.line_type == p.line_type)
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(ScoreLine.year.desc(), ScoreLine.id.asc()).limit(p.limit)
    rows = (await db.execute(stmt)).scalars().all()

    result = {
        "items": [
            {"id": r.id, "school_major_id": r.school_major_id, "year": r.year,
             "line_type": r.line_type, "total_score": r.total_score,
             "politics_score": r.politics_score, "foreign_lang_score": r.foreign_lang_score,
             "business1_score": r.business1_score, "business2_score": r.business2_score,
             "source_url": r.source_url}
            for r in rows
        ],
        "page": {"limit": p.limit, "has_more": False},
    }
    await _cache_set(cache_key, result, ttl=3600)
    return result


# ---------- 复录比概览（M3 复用） ----------

async def list_admission_stats(
    db: AsyncSession, school_major_id: int, is_vip: bool, limit: int = 5
) -> list[dict]:
    cache_key = f"admission_stats:{school_major_id}:{'vip' if is_vip else 'free'}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached
    stmt = (
        select(AdmissionStat)
        .where(AdmissionStat.school_major_id == school_major_id)
        .order_by(AdmissionStat.year.desc())
        .limit(limit if is_vip else 1)
    )
    rows = (await db.execute(stmt)).scalars().all()
    out = [
        {"id": r.id, "school_major_id": r.school_major_id, "year": r.year,
         "retest_count": r.retest_count, "admit_count": r.admit_count,
         "max_score": r.max_score, "min_score": r.min_score,
         "avg_score": float(r.avg_score) if r.avg_score is not None else None,
         # 免费用户屏蔽 score_segments 明细（VIP 才看分方向明细）
         "score_segments": r.score_segments if is_vip else None,
         "source_url": r.source_url}
        for r in rows
    ]
    await _cache_set(cache_key, out, ttl=3600)
    return out


# ---------- 招生目录 ----------

async def list_admission_catalogs(
    db: AsyncSession,
    school_id: int | None = None,
    major_id: int | None = None,
    school_major_id: int | None = None,
    year: int | None = None,
    is_vip: bool = False,
    limit: int = 20,
) -> list[dict]:
    """招生目录。

    免费：当前年（最近一年）；VIP：历年（近 5 年）。
    """
    cache_key = (
        "admission_catalogs:"
        f"{school_id}:{major_id}:{school_major_id}:{year}:{limit}:"
        f"{'vip' if is_vip else 'free'}"
    )
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(AdmissionCatalog)
    conds = []
    need_join = False
    if school_major_id:
        conds.append(AdmissionCatalog.school_major_id == school_major_id)
    elif school_id or major_id:
        need_join = True
        if school_id:
            conds.append(SchoolMajor.school_id == school_id)
        if major_id:
            conds.append(SchoolMajor.major_id == major_id)
    if need_join:
        stmt = stmt.join(
            SchoolMajor, AdmissionCatalog.school_major_id == SchoolMajor.id
        )
    if year:
        conds.append(AdmissionCatalog.year == year)
    elif not is_vip:
        # 免费：最近 1 年
        latest_year_stmt = select(func.max(AdmissionCatalog.year))
        if need_join:
            latest_year_stmt = latest_year_stmt.join(
                SchoolMajor, AdmissionCatalog.school_major_id == SchoolMajor.id
            )
        if conds:
            latest_year_stmt = latest_year_stmt.where(*conds)
        latest_year = (await db.execute(latest_year_stmt)).scalar()
        if latest_year:
            conds.append(AdmissionCatalog.year == latest_year)
    else:
        # VIP：近 5 年（distinct year desc limit 5）
        years_stmt = select(AdmissionCatalog.year)
        if need_join:
            years_stmt = years_stmt.join(
                SchoolMajor, AdmissionCatalog.school_major_id == SchoolMajor.id
            )
        if conds:
            years_stmt = years_stmt.where(*conds)
        years = list((await db.execute(
            years_stmt.distinct().order_by(AdmissionCatalog.year.desc()).limit(5)
        )).scalars().all())
        if years:
            conds.append(AdmissionCatalog.year.in_(years))

    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(AdmissionCatalog.year.desc(), AdmissionCatalog.id.asc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    out = [
        {"id": r.id, "school_major_id": r.school_major_id, "year": r.year,
         "direction": r.direction, "exam_subjects": r.exam_subjects,
         "planned_number": r.planned_number, "push_number": r.push_number,
         "reference_books": r.reference_books, "source_url": r.source_url}
        for r in rows
    ]
    await _cache_set(cache_key, out, ttl=3600)
    return out
