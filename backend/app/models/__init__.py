from datetime import datetime

from sqlalchemy import (
    Integer,
    Integer,
    SMALLINT,
    VARCHAR,
    DATETIME,
    DECIMAL,
    JSON,
    TEXT,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _dt_now() -> datetime:
    return datetime.utcnow()


class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    province: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    city: Mapped[str | None] = mapped_column(VARCHAR(32))
    level: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    school_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(VARCHAR(255))
    official_site: Mapped[str | None] = mapped_column(VARCHAR(255))
    graduate_site: Mapped[str | None] = mapped_column(VARCHAR(255))
    is_self_line: Mapped[int] = mapped_column(SMALLINT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)

    __table_args__ = (
        UniqueConstraint("code", name="uk_schools_code"),
        Index("idx_schools_level_province", "level", "province"),
        Index("idx_schools_name", "name"),
    )


class Discipline(Base):
    __tablename__ = "disciplines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(8), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    __table_args__ = (UniqueConstraint("code", name="uk_disciplines_code"),)


class Major(Base):
    __tablename__ = "majors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    discipline_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("disciplines.id"), nullable=False
    )
    degree_type: Mapped[str] = mapped_column(VARCHAR(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        UniqueConstraint("code", name="uk_majors_code"),
        Index("idx_majors_discipline", "discipline_id"),
        Index("idx_majors_name", "name"),
    )


class SchoolMajor(Base):
    __tablename__ = "school_majors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id"), nullable=False
    )
    major_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("majors.id"), nullable=False
    )
    college_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        UniqueConstraint("school_id", "major_id", "college_name", name="uk_school_major_college"),
        Index("idx_sm_major", "major_id"),
    )


class AdmissionCatalog(Base):
    __tablename__ = "admission_catalogs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_major_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("school_majors.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    direction: Mapped[str | None] = mapped_column(VARCHAR(255))
    exam_subjects: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    planned_number: Mapped[int] = mapped_column(SMALLINT, default=0)
    push_number: Mapped[int] = mapped_column(SMALLINT, default=0)
    reference_books: Mapped[str | None] = mapped_column(TEXT)
    source_url: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (Index("idx_ac_sm_year", "school_major_id", "year"),)


class ScoreLine(Base):
    __tablename__ = "score_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_major_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("school_majors.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    line_type: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    total_score: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    politics_score: Mapped[int | None] = mapped_column(SMALLINT)
    foreign_lang_score: Mapped[int | None] = mapped_column(SMALLINT)
    business1_score: Mapped[int | None] = mapped_column(SMALLINT)
    business2_score: Mapped[int | None] = mapped_column(SMALLINT)
    source_url: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        UniqueConstraint("school_major_id", "year", "line_type", name="uk_sl_sm_year_type"),
    )


class AdmissionStat(Base):
    __tablename__ = "admission_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_major_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("school_majors.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    retest_count: Mapped[int] = mapped_column(SMALLINT, default=0)
    admit_count: Mapped[int] = mapped_column(SMALLINT, default=0)
    max_score: Mapped[int | None] = mapped_column(SMALLINT)
    min_score: Mapped[int | None] = mapped_column(SMALLINT)
    avg_score: Mapped[float | None] = mapped_column(DECIMAL(5, 1))
    score_segments: Mapped[list | dict | None] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (UniqueConstraint("school_major_id", "year", name="uk_as_sm_year"),)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nickname: Mapped[str | None] = mapped_column(VARCHAR(64))
    avatar_url: Mapped[str | None] = mapped_column(VARCHAR(255))
    phone: Mapped[str | None] = mapped_column(VARCHAR(20))
    status: Mapped[int] = mapped_column(SMALLINT, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (Index("idx_users_status", "status"),)


class WechatAccount(Base):
    __tablename__ = "wechat_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    openid: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    unionid: Mapped[str | None] = mapped_column(VARCHAR(64))
    session_key: Mapped[str | None] = mapped_column(VARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        UniqueConstraint("openid", name="uk_wa_openid"),
        Index("idx_wa_user", "user_id"),
    )


class UserScoreReport(Base):
    __tablename__ = "user_score_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    school_major_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("school_majors.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    total_score: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    subject_scores: Mapped[dict | list | None] = mapped_column(JSON)
    origin_type: Mapped[str] = mapped_column(VARCHAR(8), nullable=False)
    result: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    undergrad_level: Mapped[str | None] = mapped_column(VARCHAR(32))
    origin_province: Mapped[str | None] = mapped_column(VARCHAR(32))
    is_anonymous: Mapped[int] = mapped_column(SMALLINT, nullable=False, default=1)
    audit_status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        Index("idx_usr_sm_year", "school_major_id", "year"),
        Index("idx_usr_user", "user_id"),
        Index("idx_usr_audit", "audit_status"),
    )


class VipMembership(Base):
    __tablename__ = "vip_memberships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(VARCHAR(8), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DATETIME(3), nullable=False)
    expire_at: Mapped[datetime] = mapped_column(DATETIME(3), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (Index("idx_vm_user_expire", "user_id", "expire_at"),)


class VipOrder(Base):
    __tablename__ = "vip_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    order_no: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    plan: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DATETIME(3))
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        UniqueConstraint("order_no", name="uk_vo_order_no"),
        Index("idx_vo_user", "user_id"),
    )


class PdfSource(Base):
    __tablename__ = "pdf_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(SMALLINT, nullable=False)
    pdf_url: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(VARCHAR(255))
    doc_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="pending")
    parsed_at: Mapped[datetime | None] = mapped_column(DATETIME(3))
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now, onupdate=_dt_now)
    __table_args__ = (
        Index("idx_ps_school_year", "school_id", "year"),
        Index("idx_ps_status", "status"),
    )


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_url: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    source_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    http_code: Mapped[int | None] = mapped_column(SMALLINT)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    delay_seconds: Mapped[float] = mapped_column(DECIMAL(4, 1), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    message: Mapped[str | None] = mapped_column(VARCHAR(255))
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    __table_args__ = (
        Index("idx_cl_created", "created_at"),
        Index("idx_cl_status", "status"),
    )


class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    __table_args__ = (UniqueConstraint("user_id", "school_id", name="uk_fav_user_school"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    endpoint: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    ip: Mapped[str | None] = mapped_column(VARCHAR(45))
    result: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(VARCHAR(255))
    created_at: Mapped[datetime] = mapped_column(DATETIME(3), default=_dt_now)
    __table_args__ = (
        Index("idx_al_user_created", "user_id", "created_at"),
        Index("idx_al_result", "result"),
    )


# 导入顺序：Base.metadata 需在所有 model 注册完成后引用
from ..database import Base as _Base  # noqa: E402

__all__ = [
    "School",
    "Discipline",
    "Major",
    "SchoolMajor",
    "AdmissionCatalog",
    "ScoreLine",
    "AdmissionStat",
    "User",
    "WechatAccount",
    "UserScoreReport",
    "VipMembership",
    "VipOrder",
    "PdfSource",
    "CrawlLog",
    "Favorite",
    "AuditLog",
]
