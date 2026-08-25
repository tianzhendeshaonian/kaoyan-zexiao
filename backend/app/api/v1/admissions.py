from __future__ import annotations

from fastapi import APIRouter, Query

from ...core import check_vip_active
from ...deps import DB, OptionalUser
from ...schemas import ok
from ...services.search import (
    list_admission_catalogs,
    list_admission_stats,
)
from ...services.stats import compute_ratio_for_school_major


router = APIRouter(tags=["招生目录/复录比"])


@router.get(
    "/admission-catalogs",
    description="招生目录（匿名/免费=当前年；VIP=历年近5年）",
)
async def list_catalogs(
    db: DB,
    school_id: int | None = Query(default=None),
    major_id: int | None = Query(default=None),
    school_major_id: int | None = Query(default=None),
    year: int | None = Query(default=None, ge=2015, le=2099),
    limit: int = Query(default=20, ge=1, le=100),
    user: OptionalUser = None,
):
    is_vip = False
    if user is not None:
        vip = await check_vip_active(db, user.id)
        is_vip = vip is not None
    items = await list_admission_catalogs(
        db, school_id=school_id, major_id=major_id,
        school_major_id=school_major_id, year=year, is_vip=is_vip, limit=limit,
    )
    return ok(items)


@router.get(
    "/admission-stats",
    description="复录比概览（匿名/免费=近1年；VIP=近5年+分段明细）",
)
async def list_admission_stats_route(
    db: DB,
    school_major_id: int | None = Query(default=None),
    school_id: int | None = Query(default=None),
    major_id: int | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    user: OptionalUser = None,
):
    is_vip = False
    if user is not None:
        vip = await check_vip_active(db, user.id)
        is_vip = vip is not None

    # 复录比查询需 school_major_id；若传 school_id/major_id 但未传 sm_id，
    # 这里要求调用方先解析到具体 school_major_id（避免跨专业聚合误导）。
    if not school_major_id:
        return ok([], msg="请提供 school_major_id（先调 /schools/{id}/majors 获取）")

    items = await compute_ratio_for_school_major(db, school_major_id, is_vip, limit)
    return ok(items)


@router.get(
    "/admission-stats/raw",
    description="复录比原始（兼容旧路径，行为同 /admission-stats）",
)
async def list_admission_stats_raw(
    db: DB,
    school_major_id: int = Query(...),
    limit: int = Query(default=5, ge=1, le=20),
    user: OptionalUser = None,
):
    is_vip = False
    if user is not None:
        vip = await check_vip_active(db, user.id)
        is_vip = vip is not None
    items = await list_admission_stats(db, school_major_id, is_vip, limit)
    return ok(items)
