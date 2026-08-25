from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ...core import report_rate_limit
from ...deps import CurrentUser, DB
from ...schemas import ReportIn, ReportListIn, ok
from ...services.reports import (
    create_report,
    get_my_report,
    list_my_reports,
)


router = APIRouter(prefix="/reports", tags=["上岸分数填报"])


@router.post("", description="用户自愿填报上岸分数（需二次确认同意匿名）")
async def post_report(p: ReportIn, user: CurrentUser, db: DB):
    # 限流：每日 5 次
    await report_rate_limit(user.id)
    try:
        rec = await create_report(db, user.id, p)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return ok(rec)


@router.get("/mine", description="我的填报记录（IDOR 防护：仅当前用户）")
async def my_reports(
    user: CurrentUser, db: DB,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int | None = Query(default=None),
):
    result = await list_my_reports(db, user.id, limit=limit, cursor=cursor)
    return ok(result)


@router.get("/mine/{report_id}", description="我的填报详情（IDOR 防护：不存在或不属于自己均返回 404）")
async def my_report_detail(report_id: int, user: CurrentUser, db: DB):
    rec = await get_my_report(db, user.id, report_id)
    if not rec:
        # 故意不区分"不存在"与"不属于自己"（防枚举/探测）
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")
    return ok(rec)
