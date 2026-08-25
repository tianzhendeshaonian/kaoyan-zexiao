"""用户上岸分数填报服务。

对应 PRD §5.5 + CRAWLER_COMPLIANCE.md §1 安全清单：
- A6 IDOR：查询/修改只走 user_id=current_user.id，不接受 path param user_id。
- A10 SQL 注入：全 ORM 参数化。
- #14 隐私：默认 is_anonymous=1；不存储手机号/姓名。
- 异常值检测：分数超 school_major 历史合理区间 → 标记 pending 审核状态。
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AdmissionStat, UserScoreReport
from ..schemas import ReportIn, ReportOut


# ---------- 异常值检测 ----------

async def _detect_outlier(db: AsyncSession, school_major_id: int,
                          score: int, year: int) -> tuple[bool, str]:
    """基于该 school_major 历史年份分数分布判定当前填报是否异常。

    判定规则（保守）：
    - 历史数据 < 3 条：放行 pending
    - 当前分数 > 历史 max + 50 或 < 历史 min - 50：flagged（异常值标记）
    - 否则：pending（默认待人工或自动审计）
    """
    rows = (await db.execute(
        select(AdmissionStat).where(
            AdmissionStat.school_major_id == school_major_id,
        ).order_by(AdmissionStat.year.desc()).limit(3)
    )).scalars().all()
    if len(rows) < 1:
        return False, "pending"
    maxes = [r.max_score for r in rows if r.max_score is not None]
    mins = [r.min_score for r in rows if r.min_score is not None]
    if not maxes or not mins:
        return False, "pending"
    hmax = max(maxes)
    hmin = min(mins)
    if score > hmax + 50 or score < hmin - 50:
        return True, "flagged"
    return False, "pending"


# ---------- 填报 ----------

async def create_report(
    db: AsyncSession, user_id: int, p: ReportIn,
) -> dict:
    """创建一条上岸分数填报。

    强约束：
    - 必须二次确认 agree_anonymized=True
    - is_anonymous 默认 1（脱敏存储，不返回可识别身份字段）
    """
    if not p.agree_anonymized:
        raise ValueError("必须二次确认同意匿名脱敏使用")
    is_outlier, audit_status = await _detect_outlier(
        db, p.school_major_id, p.total_score, p.year,
    )
    rec = UserScoreReport(
        user_id=user_id,
        school_major_id=p.school_major_id,
        year=p.year,
        total_score=p.total_score,
        subject_scores=p.subject_scores,
        origin_type=p.origin_type,
        result=p.result,
        undergrad_level=p.undergrad_level,
        origin_province=p.origin_province,
        is_anonymous=p.is_anonymous,
        audit_status=audit_status,
    )
    db.add(rec)
    await db.flush()
    return _report_to_dict(rec)


# ---------- 我的填报（IDOR 防护：仅看自己） ----------

async def list_my_reports(
    db: AsyncSession, user_id: int, limit: int = 20, cursor: int | None = None,
) -> dict:
    """列出当前用户的填报记录。

    IDOR 防护：where user_id = current_user.id，不接受 path 传 user_id。
    """
    stmt = select(UserScoreReport).where(UserScoreReport.user_id == user_id)
    if cursor:
        stmt = stmt.where(UserScoreReport.id > cursor)
    stmt = stmt.order_by(UserScoreReport.id.desc()).limit(limit + 1)
    rows = (await db.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if items and has_more else None
    return {
        "items": [_report_to_dict(r) for r in items],
        "page": {
            "cursor": cursor,
            "next_cursor": next_cursor,
            "limit": limit,
            "has_more": has_more,
        },
    }


# ---------- 单条详情（IDOR 防护） ----------

async def get_my_report(db: AsyncSession, user_id: int, report_id: int) -> dict | None:
    """查询单条填报：必须 user_id 匹配（A6）。

    若不匹配，返回 None → 路由层抛 404，避免暴露存在性。
    """
    rec = (await db.execute(
        select(UserScoreReport).where(
            and_(
                UserScoreReport.id == report_id,
                UserScoreReport.user_id == user_id,
            ),
        )
    )).scalar_one_or_none()
    if not rec:
        return None
    return _report_to_dict(rec)


# ---------- 脱敏序列化 ----------

def _report_to_dict(r: UserScoreReport) -> dict:
    """脱敏输出：is_anonymous=1 时屏蔽 user_id。"""
    out = {
        "id": r.id,
        "school_major_id": r.school_major_id,
        "year": r.year,
        "total_score": r.total_score,
        "subject_scores": r.subject_scores,
        "origin_type": r.origin_type,
        "result": r.result,
        "undergrad_level": r.undergrad_level,
        "origin_province": r.origin_province,
        "is_anonymous": r.is_anonymous,
        "audit_status": r.audit_status,
        "created_at": int(r.created_at.timestamp()) if r.created_at else 0,
    }
    if r.is_anonymous == 1:
        # 脱敏：不返回 user_id（即使前端不展示，也避免泄露）
        out["user_id"] = None
    else:
        out["user_id"] = r.user_id
    return out
