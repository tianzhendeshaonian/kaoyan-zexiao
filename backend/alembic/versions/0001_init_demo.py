"""样例版本：首次建表（从 models.metadata 自动生成）。

实际使用：
    pip install -r requirements.txt
    cp .env.example .env
    alembic revision --autogenerate -m "init"
    alembic upgrade head

若不使用 alembic，也可直接运行 backend/scripts/init_db.py 进行 metadata.create_all。
"""
revision = "0001_init_demo"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 生产由 alembic --autogenerate 生成实际操作
    raise NotImplementedError("请执行 alembic revision --autogenerate 生成正式迁移")


def downgrade() -> None:
    raise NotImplementedError
