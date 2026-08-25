from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ...config import settings
from ...deps import ClientIP, CurrentUser, DB, VipUser
from ...schemas import SimulatePayIn, VipOrderIn, ok
from ...services.payment import PLANS, plan_total_fee
from ...services.vip import (
    create_order,
    get_order_detail,
    get_user_orders,
    handle_notify,
    handle_payment_success,
)


router = APIRouter(prefix="/vip", tags=["VIP 会员"])


@router.get("/plans", description="VIP 套餐列表")
async def list_plans():
    return [
        {"plan": k, "title": v["title"], "amount": v["amount"], "days": v["days"]}
        for k, v in PLANS.items()
    ]


@router.post("/orders", description="创建 VIP 订单（返回微信支付参数）")
async def create_order_route(p: VipOrderIn, user: CurrentUser, db: DB, ip: ClientIP):
    notify_url = f"https://your-domain/api/v1/vip/orders/{{order_no}}/notify"
    try:
        result = await create_order(db, user.id, p.plan, ip, notify_url)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    await db.commit()
    return ok(result)


@router.get("/orders/mine", description="我的订单列表（IDOR 防护）")
async def my_orders(
    user: CurrentUser, db: DB,
    limit: int = Query(default=20, ge=1, le=100),
):
    items = await get_user_orders(db, user.id, limit=limit)
    return ok(items)


@router.get("/orders/{order_no}", description="订单详情（IDOR 防护：仅本人）")
async def order_detail(order_no: str, user: CurrentUser, db: DB):
    detail = await get_order_detail(db, user.id, order_no)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    return ok(detail)


@router.post(
    "/orders/{order_no}/notify",
    description="微信支付异步通知（XML 解析后业务校验 + 状态机）",
)
async def notify_route(order_no: str, db: DB):
    """微信支付异步通知入口。

    实际接入：从 Request.body 解析 XML → 转 dict → 调 handle_notify。
    此处接受 JSON 简化测试；商用接入需补 XML 解析。
    """
    # demo：直接构造一个返回 SUCCESS 的 payload（实际从 XML 解析）
    from fastapi import Request
    # 占位：实际接入请解析 XML，此处返回失败提示
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "微信支付通知需 XML 解析，请接入 xmltodict 或在 dev 用 /simulate-pay",
    )


@router.post(
    "/orders/{order_no}/simulate-pay",
    description="【dev/test only】模拟支付完成 → 直接调用状态机",
)
async def simulate_pay(
    order_no: str, p: SimulatePayIn, user: CurrentUser, db: DB,
):
    if settings.APP_ENV not in ("dev", "test"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅 dev/test 可用")
    # IDOR：必须订单属于本人
    detail = await get_order_detail(db, user.id, order_no)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")

    if p.paid:
        result = await handle_payment_success(
            db, order_no, transaction_id=f"demo_{order_no}",
        )
        await db.commit()
        if not result["ok"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, result["msg"])
        return ok(result)
    else:
        # 取消订单（用户主动）
        from sqlalchemy import select
        from ...models import VipOrder
        order = (await db.execute(
            select(VipOrder).where(
                VipOrder.order_no == order_no,
                VipOrder.user_id == user.id,
            )
        )).scalar_one_or_none()
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
        if order.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"订单状态 {order.status}")
        order.status = "cancelled"
        await db.commit()
        return ok({"ok": True, "msg": "已取消"})


@router.get("/advanced-example", description="演示 VIP 守卫：仅 VIP 可访问")
async def advanced(user: VipUser):
    return ok({"msg": "vip advanced data", "user_id": user.id})
