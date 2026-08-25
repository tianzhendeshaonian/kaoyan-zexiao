from __future__ import annotations

from fastapi import APIRouter, Query

from ...core import check_vip_active
from ...deps import DB, OptionalUser
from ...schemas import ScoreLineIn, ok
from ...services.search import list_score_lines


router = APIRouter(tags=["复试线"])


@router.get(
    "/score-lines",
    description="历年复试线（匿名/免费=近1年；VIP=近5年，自动按登录态判断）",
)
async def list_score_lines_route(
    db: DB,
    school_id: int | None = Query(default=None),
    major_id: int | None = Query(default=None),
    school_major_id: int | None = Query(default=None),
    year: int | None = Query(default=None, ge=2015, le=2099),
    line_type: str | None = Query(default=None, pattern=r"^(national|self|college)$"),
    limit: int = Query(default=20, ge=1, le=100),
    user: OptionalUser = None,
):
    is_vip = False
    if user is not None:
        vip = await check_vip_active(db, user.id)
        is_vip = vip is not None

    p = ScoreLineIn(
        school_id=school_id, major_id=major_id, school_major_id=school_major_id,
        year=year, line_type=line_type, limit=limit,
    )
    result = await list_score_lines(db, p, is_vip=is_vip)
    return ok(result)
