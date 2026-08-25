from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class ReportIn(BaseModel):
    school_major_id: int = Field(..., gt=0)
    year: int = Field(..., ge=2015, le=2099)
    total_score: int = Field(..., ge=0, le=500)
    subject_scores: dict | None = None
    origin_type: str = Field(..., pattern=r"^(一志愿|调剂)$")
    result: str = Field(..., pattern=r"^(录取|复试未录|未进复试)$")
    undergrad_level: str | None = Field(default=None, max_length=32)
    origin_province: str | None = Field(default=None, max_length=32)
    is_anonymous: int = Field(default=1, ge=0, le=1)
    agree_anonymized: bool = Field(..., description="二次确认:自愿授权匿名用于统计")


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_major_id: int
    year: int
    total_score: int
    subject_scores: dict | None = None
    origin_type: str
    result: str
    undergrad_level: str | None = None
    origin_province: str | None = None
    is_anonymous: int
    audit_status: str
    created_at: int


class ReportListIn(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: int | None = None


class RecommendIn(BaseModel):
    score: int = Field(..., ge=200, le=500)
    discipline_id: int | None = None
    province: str | None = Field(default=None, max_length=32)
    risk_pref: str = Field(default="balance", pattern=r"^(conservative|balance|aggressive)$")
    top_n: int = Field(default=10, ge=1, le=50)


class RecommendItem(BaseModel):
    school_id: int
    school_name: str
    school_major_id: int
    major_code: str
    major_name: str
    year: int
    recent_min: int
    recent_avg: int
    recent_max: int
    bucket: str  # chong / wen / bao / none
    admit_count: int | None = None
    retest_count: int | None = None
    ratio: float | None = None


class RecommendOut(BaseModel):
    score: int
    risk_pref: str
    chong: list[RecommendItem]
    wen: list[RecommendItem]
    bao: list[RecommendItem]
    used_quota: int
    quota_remaining: int | None = None  # None 表示 VIP 无限
