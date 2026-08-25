<template>
  <view class="container">
    <view class="header">
      <text class="title">我的订单</text>
    </view>

    <view v-for="o in orders" :key="o.order_no" class="card order-card">
      <view class="row">
        <text class="plan">{{ o.plan }}</text>
        <text class="status" :class="o.status">{{ statusLabel(o.status) }}</text>
      </view>
      <view class="meta">
        <text class="text-muted">订单号：{{ o.order_no }}</text>
      </view>
      <view class="meta">
        <text class="amount">¥{{ o.amount }}</text>
      </view>
      <view class="meta">
        <text class="text-muted">创建：{{ formatTime(o.created_at) }}</text>
        <text v-if="o.paid_at" class="text-muted"> · 支付：{{ formatTime(o.paid_at) }}</text>
      </view>
      <view v-if="o.status === 'pending' && IS_DEV" class="action">
        <button class="btn-ghost small" @tap="simulatePay(o)">[DEV] 模拟支付</button>
      </view>
    </view>

    <view v-if="!loading && orders.length === 0" class="empty">
      <text class="text-muted">暂无订单</text>
      <button class="btn-primary" @tap="goPlans">去开通 VIP</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { API, IS_DEV } from "@/utils/config"
import { get, post } from "@/utils/request"
import { requireAuth, fetchProfile } from "@/utils/auth"

const orders = ref([])
const loading = ref(false)

onShow(async () => {
  if (!(await requireAuth())) return
  loadOrders()
})

async function loadOrders() {
  loading.value = true
  try {
    const r = await get(API.VIP_ORDERS_MINE, {}, { needAuth: true })
    if (r && r.code === 0) orders.value = r.data.items || r.data || []
  } catch (e) {} finally {
    loading.value = false
  }
}

function statusLabel(s) {
  return { pending: "待支付", paid: "已支付", cancelled: "已取消",
           refunded: "已退款" }[s] || s
}

function formatTime(ts) {
  if (!ts) return ""
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()} ${d.getHours()}:${d.getMinutes()}`
}

async function simulatePay(o) {
  try {
    const r = await post(API.vipSimulatePay(o.order_no), { paid: true },
      { needAuth: true })
    if (r && r.code === 0) {
      uni.showToast({ title: "支付成功", icon: "success" })
      await fetchProfile()
      loadOrders()
    }
  } catch (e) {}
}

function goPlans() {
  uni.navigateTo({ url: "/pages/vip/plans" })
}
</script>

<style scoped>
.header {
  margin-bottom: 24rpx;
}
.title {
  font-size: 36rpx;
  font-weight: bold;
}
.order-card {
  margin-bottom: 16rpx;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.plan {
  font-size: 32rpx;
  font-weight: bold;
}
.status {
  font-size: 22rpx;
  padding: 4rpx 16rpx;
  border-radius: 16rpx;
}
.status.pending { background: #fff4e6; color: #ff8c00; }
.status.paid { background: #e6ffed; color: #52c41a; }
.status.cancelled, .status.refunded { background: #f5f5f5; color: #999; }
.meta {
  font-size: 24rpx;
  margin-top: 8rpx;
}
.amount {
  font-size: 32rpx;
  color: #ff6b6b;
  font-weight: bold;
}
.action {
  margin-top: 16rpx;
}
.small {
  height: 60rpx;
  line-height: 60rpx;
  font-size: 24rpx;
  border-radius: 32rpx;
}
.empty {
  text-align: center;
  padding: 80rpx 0;
}
.empty .btn-primary {
  margin-top: 24rpx;
  width: 320rpx;
}
</style>
