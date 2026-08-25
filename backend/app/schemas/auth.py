from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict

from .common import UserDTO, VipInfo


class WechatLoginIn(BaseModel):
    code: str = Field(..., min_length=8, max_length=64)
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    access_expire_at: int
    refresh_token: str
    refresh_expire_at: int
    token_type: str = "Bearer"


class LoginOut(BaseModel):
    user: UserDTO
    token: TokenPair
    vip: VipInfo | None = None


class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class LogoutIn(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: UserDTO
    vip: VipInfo | None = None
