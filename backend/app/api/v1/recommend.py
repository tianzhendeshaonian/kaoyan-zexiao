from __future__ import annotations

from fastapi import APIRouter, Query

from ...core import check_vip_active, recommend_rate_limit
from ...deps import CurrentUser, DB
from ...schemas import RecommendIn, ok
from ...services.recommend import build_recommendation


router = APIRouter(prefix="/recommend", tags=["冲稳保"])


@router.post(
    "",
    description="冲稳保推荐（免费 3 次/日；VIP 无限）",
)
async def post_recommend(p: RecommendIn, user: CurrentUser, db: DB):
    is_vip = await check_vip_active(db, user.id) is not None
    # 限流：免费用户每日 3 次，VIP 跳过
    await recommend_rate_limit(user.id, is_vip)

    result = await build_recommendation(db, p)
    # 配额信息
    result["used_quota"] = 1  # 本次调用计数（实际计数由限流器维护）
    result["quota_remaining"] = None if is_vip else 0  # 简化：路由层已抛 429
    return ok(result)
