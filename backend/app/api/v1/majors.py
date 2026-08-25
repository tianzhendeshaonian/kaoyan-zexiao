from __future__ import annotations

from fastapi import APIRouter, Query

from ...deps import DB
from ...schemas import MajorIn, ok
from ...services.search import search_majors


router = APIRouter(prefix="/majors", tags=["专业"])


@router.get("", description="专业检索（关键词 + 学科 + 学位类型）")
async def list_majors(
    db: DB,
    keyword: str | None = Query(default=None, max_length=64),
    discipline_id: int | None = Query(default=None),
    degree_type: str | None = Query(default=None, pattern=r"^(学硕|专硕)$"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int | None = Query(default=None),
):
    p = MajorIn(
        keyword=keyword, discipline_id=discipline_id, degree_type=degree_type,
        limit=limit, cursor=cursor,
    )
    result = await search_majors(db, p)
    return ok(result)
