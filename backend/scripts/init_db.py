"""直接建表（不依赖 alembic）+ 种子数据。适合本地快速跑通。

使用：
    python -m scripts.init_db
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger

from app.database import engine, Base, AsyncSessionLocal
from app.models import School, Discipline, Major, SchoolMajor  # noqa: F401  触发注册


async def create_all():
    # 1) 建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("表创建完成")

    # 2) 种子数据（少量示例）
    async with AsyncSessionLocal() as session:
        # 学科门类
        codes = [
            ("01", "哲学"), ("02", "经济学"), ("03", "法学"), ("04", "教育学"),
            ("05", "文学"), ("06", "历史学"), ("07", "理学"), ("08", "工学"),
            ("09", "农学"), ("10", "医学"), ("11", "军事学"), ("12", "管理学"),
            ("13", "艺术学"), ("14", "交叉学科"),
        ]
        from app.models import Discipline as D
        from sqlalchemy import select
        for code, name in codes:
            exists = (await session.execute(select(D).where(D.code == code))).scalar_one_or_none()
            if not exists:
                session.add(D(code=code, name=name))
        await session.flush()

        # 2 所示例院校
        samples = [
            dict(code="10001", name="北京大学", province="北京", city="北京",
                 level="985", school_type="综合", is_self_line=1,
                 official_site="https://www.pku.edu.cn",
                 graduate_site="https://grs.pku.edu.cn"),
            dict(code="10246", name="复旦大学", province="上海", city="上海",
                 level="985", school_type="综合", is_self_line=1,
                 official_site="https://www.fudan.edu.cn",
                 graduate_site="https://gs.fudan.edu.cn"),
        ]
        for s in samples:
            exists = (await session.execute(select(School).where(School.code == s["code"]))).scalar_one_or_none()
            if not exists:
                session.add(School(**s))
        await session.commit()
    logger.info("种子数据写入完成")


if __name__ == "__main__":
    asyncio.run(create_all())
