from __future__ import annotations

from pydantic import BaseModel, Field


class VipPlanOut(BaseModel):
    plan: str
    amount: float
    days: int
    title: str


class VipOrderIn(BaseModel):
    plan: str = Field(..., pattern=r"^(monthly|quarterly|yearly)$")


class VipOrderOut(BaseModel):
    order_no: str
    plan: str
    amount: float
    status: str
    created_at: int
    expire_at: int  # 订单本身过期时间（创建后 15 分钟未支付自动取消）


class VipOrderDetailOut(BaseModel):
    """订单详情：含微信支付参数（prepay_id 等）+ VIP 状态。"""
    order_no: str
    plan: str
    amount: float
    status: str
    created_at: int
    paid_at: int | None = None
    # 微信小程序支付参数（实际接入时由 payment.unifiedorder 返回）
    payment_params: dict | None = None
    vip_active: bool = False
    vip_expire_at: int | None = None


class WechatNotifyIn(BaseModel):
    """微信支付异步通知（XML 解析后字段）。

    实际接入：路由层解析 XML → 解析为 dict → 业务校验 → 状态机更新。
    本 schema 仅做关键字段约束。
    """
    appid: str
    mch_id: str
    out_trade_no: str
    transaction_id: str
    total_fee: int  # 单位：分
    result_code: str
    return_code: str
    sign: str


class SimulatePayIn(BaseModel):
    """dev/test 模拟支付入参。仅 APP_ENV=dev 可用。"""
    paid: bool = Field(default=True)
