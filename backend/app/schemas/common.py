from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="0=ok,其他=错误")
    msg: str = Field(default="ok")
    data: T | None = Field(default=None)

    model_config = ConfigDict(json_encoders={}, from_attributes=True)


def ok(data: Any = None, msg: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, msg=msg, data=data)


def fail(code: int = 1, msg: str = "fail", data: Any = None) -> ApiResponse:
    return ApiResponse(code=code, msg=msg, data=data)


class PageInfo(BaseModel):
    cursor: int | str | None = Field(default=None)
    next_cursor: int | str | None = Field(default=None)
    limit: int = 20
    has_more: bool = False


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: PageInfo


class UserDTO(BaseModel):
    id: int
    nickname: str | None = None
    avatar_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class VipInfo(BaseModel):
    level: str
    expire_at: int | None = None  # epoch seconds, None=未开通
