from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class SchoolIn(BaseModel):
    keyword: str | None = Field(default=None, max_length=64, description="关键词模糊匹配")
    province: str | None = Field(default=None, max_length=32)
    level: str | None = Field(default=None, max_length=16)
    school_type: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: int | None = Field(default=None, description="上一页最后一条 id")


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    province: str
    city: str | None
    level: str
    school_type: str
    is_self_line: int


class SchoolListItem(SchoolOut):
    """列表项额外字段：匹配到的专业数与最近一年复试线摘要"""
    matched_major_count: int = 0
    latest_score_line: int | None = None


class SchoolMajorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    school_name: str
    major_id: int
    major_code: str
    major_name: str
    college_name: str
    degree_type: str
    discipline_id: int


class SchoolDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    province: str
    city: str | None
    level: str
    school_type: str
    is_self_line: int
    logo_url: str | None
    official_site: str | None
    graduate_site: str | None


class MajorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    degree_type: str
    discipline_id: int


class MajorIn(BaseModel):
    keyword: str | None = Field(default=None, max_length=64)
    discipline_id: int | None = None
    degree_type: str | None = Field(default=None, pattern=r"^(学硕|专硕)$")
    limit: int = Field(default=20, ge=1, le=100)
    cursor: int | None = Field(default=None)


class ScoreLineIn(BaseModel):
    school_id: int | None = None
    major_id: int | None = None
    school_major_id: int | None = None
    year: int | None = Field(default=None, ge=2015, le=2099)
    line_type: str | None = Field(default=None, pattern=r"^(national|self|college)$")
    limit: int = Field(default=20, ge=1, le=100)


class ScoreLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_major_id: int
    year: int
    line_type: str
    total_score: int
    politics_score: int | None
    foreign_lang_score: int | None
    business1_score: int | None
    business2_score: int | None
    source_url: str


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
    score_segments: Any | None = None
    source_url: str
