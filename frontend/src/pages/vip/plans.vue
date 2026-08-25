<template>
  <view class="container">
    <view class="header">
      <text class="title">VIP 会员</text>
      <text class="subtitle">解锁完整数据 · 无限冲稳保</text>
    </view>

    <view class="benefits">
      <view v-for="b in benefits" :key="b" class="benefit-item">
        <text class="check">✓</text>
        <text>{{ b }}</text>
      </view>
    </view>

    <view class="plans">
      <view v-for="p in plans" :key="p.plan" class="plan-card"
            :class="{ active: selectedPlan === p.plan }"
            @tap="selectedPlan = p.plan">
        <text class="plan-title">{{ p.title }}</text>
        <view class="price-row">
          <text class="price">¥{{ p.amount }}</text>
          <text class="period">/ {{ p.days }}天</text>
        </view>
      </view>
    </view>

    <button class="btn-primary pay-btn" :loading="paying" @tap="onPay">
      立即开通 {{ selectedPlanTitle }}
    </button>

    <!-- dev 模拟支付（仅 IS_DEV 显示） -->
    <button v-if="IS_DEV && orderNo" class="btn-ghost sim-btn"
            :loading="simulating" @tap="onSimulatePay">
      [DEV] 模拟支付完成
    </button>

    <view class="tips">
      <text class="text-muted">· 支付即视为同意 VIP 服务条款</text>
      <text class="text-muted">· VIP 权益自支付成功日起生效</text>
      <text class="text-muted">· 演示环境模拟支付，正式版接入微信支付</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue"
import { API, IS_DEV } from "@/utils/config"
import { get, post } from "@/utils/request"
import { requireAuth, fetchProfile, isVip } from "@/utils/auth"

const benefits = [
  "近 5 年复试线数据",
  "复录比分段明细",
  "招生目录历年汇总",
  "冲稳保推荐无限次",
  "高级筛选与排序",
]

const plans = ref([])
const selectedPlan = ref("monthly")
const selectedPlanTitle = computed(() => {
  const p = plans.value.find(x => x.plan === selectedPlan.value)
  return p ? p.title : ""
})

const paying = ref(false)
const simulating = ref(false)
const orderNo = ref("")

async function loadPlans() {
  try {
    const r = await get(API.VIP_PLANS)
    if (r && r.code === 0) plans.value = r.data || []
  } catch (e) {}
}

async function onPay() {
  if (!(await requireAuth())) return
  if (isVip()) {
    uni.showToast({ title: "您已是 VIP，无需重复开通", icon: "none" })
    return
  }
  paying.value = true
  try {
    const r = await post(API.VIP_ORDERS, { plan: selectedPlan.value },
      { needAuth: true })
    if (r && r.code === 0) {
      orderNo.value = r.data.order_no
      const params = r.data.payment_params
      if (params && params._demo) {
        uni.showToast({ title: "订单已创建（demo 模式）", icon: "none" })
      } else if (params) {
        // 真实微信支付：调起 wx.requestPayment
        wx.requestPayment({
          timeStamp: params.timeStamp,
          nonceStr: params.nonceStr,
          package: params.package,
          signType: params.signType,
          paySign: params.paySign,
          success: async () => {
            uni.showToast({ title: "支付成功", icon: "success" })
            await fetchProfile()
            setTimeout(() => uni.navigateBack(), 800)
          },
          fail: () => {
            uni.showToast({ title: "支付取消", icon: "none" })
          },
        })
      }
    }
  } catch (e) {} finally {
    paying.value = false
  }
}

async function onSimulatePay() {
  if (!orderNo.value) return
  simulating.value = true
  try {
    const r = await post(API.vipSimulatePay(orderNo.value), { paid: true },
      { needAuth: true })
    if (r && r.code === 0) {
      uni.showToast({ title: "支付成功，VIP 已开通", icon: "success" })
      await fetchProfile()
      setTimeout(() => uni.navigateBack(), 800)
    }
  } catch (e) {} finally {
    simulating.value = false
  }
}

loadPlans()
</script>

<style scoped>
.header {
  text-align: center;
  padding: 48rpx 0 24rpx;
}
.title {
  font-size: 48rpx;
  font-weight: bold;
  color: #333;
  display: block;
}
.subtitle {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
.benefits {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}
.benefit-item {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 12rpx 0;
  font-size: 28rpx;
}
.check {
  color: #52c41a;
  font-weight: bold;
}
.plans {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.plan-card {
  background: #fff;
  border: 4rpx solid #eee;
  border-radius: 16rpx;
  padding: 24rpx 16rpx;
  text-align: center;
}
.plan-card.active {
  border-color: #3a7afe;
  background: linear-gradient(135deg, #f0f6ff 0%, #fff 100%);
}
.plan-title {
  font-size: 28rpx;
  font-weight: bold;
  display: block;
  margin-bottom: 12rpx;
}
.price {
  font-size: 40rpx;
  font-weight: bold;
  color: #ff6b6b;
}
.period {
  font-size: 22rpx;
  color: #999;
}
.pay-btn, .sim-btn {
  margin-top: 16rpx;
}
.sim-btn {
  margin-top: 16rpx;
}
.tips {
  margin-top: 32rpx;
}
.tips text {
  display: block;
  margin-top: 8rpx;
}
</style>
