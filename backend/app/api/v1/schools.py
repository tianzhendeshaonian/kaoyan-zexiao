from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ...deps import DB
from ...schemas import SchoolIn, ok
from ...services.search import (
    get_school_detail,
    list_school_majors,
    search_schools,
)


router = APIRouter(prefix="/schools", tags=["院校"])


@router.get("", description="院校检索（多条件 + 关键词 + 游标分页）")
async def list_schools(
    db: DB,
    keyword: str | None = Query(default=None, max_length=64),
    province: str | None = Query(default=None, max_length=32),
    level: str | None = Query(default=None, max_length=16),
    school_type: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int | None = Query(default=None),
):
    p = SchoolIn(
        keyword=keyword, province=province, level=level, school_type=school_type,
        limit=limit, cursor=cursor,
    )
    result = await search_schools(db, p)
    return ok(result)


@router.get("/{school_id}", description="院校详情")
async def get_school(school_id: int, db: DB):
    detail = await get_school_detail(db, school_id)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "院校不存在")
    return ok(detail)


@router.get("/{school_id}/majors", description="院校下开设专业列表")
async def school_majors(
    school_id: int,
    db: DB,
    keyword: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
):
    items = await list_school_majors(db, school_id, keyword, limit)
    return ok(items)
