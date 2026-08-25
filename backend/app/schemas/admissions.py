from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ---------- 招生目录 ----------

class AdmissionCatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_major_id: int
    year: int
    direction: str | None = None
    exam_subjects: list[str] | None = None
    planned_number: int = 0
    push_number: int = 0
    reference_books: str | None = None
    source_url: str


class AdmissionCatalogIn(BaseModel):
    school_id: int | None = None
    major_id: int | None = None
    school_major_id: int | None = None
    year: int | None = Field(default=None, ge=2015, le=2099)
    limit: int = Field(default=20, ge=1, le=100)


# ---------- 复录比 ----------

class AdmissionStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_major_id: int
    year: int
    retest_count: int
    admit_count: int
    max_score: int | None
    min_score: int | None
    avg_score: float | None
    score_segments: Any | None = None  # VIP 才返回明细
    source_url: str


class AdmissionStatIn(BaseModel):
    school_major_id: int | None = None
    school_id: int | None = None
    major_id: int | None = None
    year: int | None = Field(default=None, ge=2015, le=2099)
    limit: int = Field(default=5, ge=1, le=20)


# ---------- 复录比 ratio（对外口径） ----------

class AdmissionRatioOut(BaseModel):
    """复录比概览（免费用户）。"""
    school_major_id: int
    year: int
    retest_count: int
    admit_count: int
    ratio: float | None = None
    max_score: int | None
    min_score: int | None
    avg_score: float | None
    source_url: str


class AdmissionRatioDetail(AdmissionRatioOut):
    """复录比明细（VIP）。"""
    score_segments: Any | None = None
