from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import VipMembership


async def check_vip_active(db: AsyncSession, user_id: int) -> VipMembership | None:
    now = datetime.utcnow()
    row = (
        await db.execute(
            select(VipMembership)
            .where(
                VipMembership.user_id == user_id,
                VipMembership.status == "active",
                VipMembership.start_at <= now,
                VipMembership.expire_at > now,
            )
            .order_by(VipMembership.expire_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row
