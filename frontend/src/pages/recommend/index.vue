<template>
  <view class="container">
    <view class="card input-card">
      <view class="input-row">
        <text class="label">我的分数</text>
        <input v-model.number="form.score" type="number" class="score-input" placeholder="如 360" />
      </view>
      <view class="input-row">
        <text class="label">风险偏好</text>
        <view class="radio-group">
          <view v-for="r in riskOptions" :key="r.value" class="radio-item"
                :class="{ active: form.risk_pref === r.value }"
                @tap="form.risk_pref = r.value">
            <text>{{ r.label }}</text>
          </view>
        </view>
      </view>
      <view class="input-row">
        <text class="label">省份（选填）</text>
        <input v-model="form.province" class="input" placeholder="如 北京" />
      </view>
      <button class="btn-primary" :loading="loading" @tap="onRecommend">开始推荐</button>
    </view>

    <view v-if="result">
      <view v-for="bucket in buckets" :key="bucket.key" class="bucket-section">
        <view class="bucket-title" :style="{ color: bucket.color }">
          <text>{{ bucket.label }} ({{ result[bucket.key].length }})</text>
        </view>
        <view v-for="item in result[bucket.key]" :key="item.school_major_id"
              class="card item-card" @tap="goDetail(item)">
          <view class="item-header">
            <text class="school-name">{{ item.school_name }}</text>
            <text class="bucket-badge" :style="{ background: bucket.color }">
              {{ bucket.label }}
            </text>
          </view>
          <view class="item-meta">
            <text class="major">{{ item.major_name }}（{{ item.major_code }}）</text>
          </view>
          <view class="score-range">
            <text class="text-muted">近年</text>
            <text class="range">{{ item.recent_min }} - {{ item.recent_max }}</text>
            <text class="text-muted">均 {{ item.recent_avg }}</text>
          </view>
          <view v-if="item.ratio" class="ratio-row">
            <text class="text-muted">复录比 {{ item.ratio }}</text>
          </view>
        </view>
        <view v-if="result[bucket.key].length === 0" class="bucket-empty">
          <text class="text-muted">无 {{ bucket.label }} 档推荐</text>
        </view>
      </view>
    </view>

    <view v-if="needVipTip" class="vip-tip" @tap="goVip">
      <text class="text-muted">免费用户每日 3 次，开通 VIP 无限次推荐 ›</text>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from "vue"
import { API, BUCKET_COLORS, BUCKET_LABELS } from "@/utils/config"
import { post } from "@/utils/request"
import { requireAuth, isVip } from "@/utils/auth"

const riskOptions = [
  { value: "conservative", label: "保守" },
  { value: "balance", label: "平衡" },
  { value: "aggressive", label: "激进" },
]

const form = reactive({
  score: "",
  risk_pref: "balance",
  province: "",
})

const result = ref(null)
const loading = ref(false)
const needVipTip = ref(false)

const buckets = [
  { key: "chong", label: BUCKET_LABELS.chong, color: BUCKET_COLORS.chong },
  { key: "wen", label: BUCKET_LABELS.wen, color: BUCKET_COLORS.wen },
  { key: "bao", label: BUCKET_LABELS.bao, color: BUCKET_COLORS.bao },
]

async function onRecommend() {
  if (!(await requireAuth())) return
  if (!form.score || form.score < 200 || form.score > 500) {
    uni.showToast({ title: "请输入 200-500 之间的分数", icon: "none" })
    return
  }
  loading.value = true
  try {
    const r = await post(API.RECOMMEND, {
      score: Number(form.score),
      risk_pref: form.risk_pref,
      province: form.province || undefined,
    }, { needAuth: true })
    if (r && r.code === 0) {
      result.value = r.data
      needVipTip.value = !isVip()
    }
  } catch (e) {
    // 429 限流：免费超额
    if (String(e.message).includes("429") || String(e.message).includes("次数")) {
      uni.showModal({
        title: "已达上限",
        content: "免费用户每日 3 次，是否开通 VIP 无限使用？",
        confirmText: "开通 VIP",
        success: (r) => { if (r.confirm) goVip() },
      })
    }
  } finally {
    loading.value = false
  }
}

function goDetail(item) {
  uni.navigateTo({
    url: `/pages/admission/stats?sm_id=${item.school_major_id}&title=${encodeURIComponent(item.major_name)}`,
  })
}

function goVip() {
  uni.navigateTo({ url: "/pages/vip/plans" })
}
</script>

<style scoped>
.input-card {
  margin-bottom: 32rpx;
}
.input-row {
  display: flex;
  align-items: center;
  margin-bottom: 24rpx;
}
.label {
  width: 180rpx;
  color: #333;
  font-size: 28rpx;
}
.score-input, .input {
  flex: 1;
  background: #f5f6fa;
  border-radius: 8rpx;
  padding: 16rpx 20rpx;
  font-size: 28rpx;
}
.radio-group {
  flex: 1;
  display: flex;
  gap: 16rpx;
}
.radio-item {
  flex: 1;
  padding: 12rpx 0;
  background: #f5f6fa;
  border-radius: 32rpx;
  text-align: center;
  font-size: 26rpx;
  color: #666;
}
.radio-item.active {
  background: #3a7afe;
  color: #fff;
}
.bucket-section {
  margin-bottom: 32rpx;
}
.bucket-title {
  font-size: 32rpx;
  font-weight: bold;
  margin-bottom: 16rpx;
}
.item-card {
  margin-bottom: 16rpx;
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.school-name {
  font-size: 30rpx;
  font-weight: bold;
}
.bucket-badge {
  color: #fff;
  font-size: 22rpx;
  padding: 4rpx 16rpx;
  border-radius: 16rpx;
}
.item-meta, .score-range, .ratio-row {
  font-size: 24rpx;
  margin-top: 8rpx;
}
.score-range {
  display: flex;
  gap: 16rpx;
  align-items: center;
}
.range {
  font-weight: bold;
  color: #ff6b6b;
}
.bucket-empty, .vip-tip {
  text-align: center;
  padding: 24rpx 0;
}
.vip-tip {
  background: linear-gradient(135deg, #fff8e6 0%, #fff4d9 100%);
  border-radius: 16rpx;
  margin-top: 24rpx;
}
</style>
