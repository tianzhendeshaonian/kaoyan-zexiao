<template>
  <view class="container">
    <view v-if="title" class="page-title">
      <text class="title">{{ title }}</text>
    </view>

    <view v-if="needVip" class="vip-tip">
      <text class="text-muted">免费版仅展示近1年，开通 VIP 可查看近5年+分段明细</text>
      <button class="vip-btn" @tap="goVip">开通 VIP</button>
    </view>

    <view v-for="s in stats" :key="s.year" class="card stat-card">
      <view class="year-row">
        <text class="year">{{ s.year }}</text>
        <text v-if="s.ratio" class="ratio">复录比 {{ s.ratio }}</text>
      </view>
      <view class="score-grid">
        <view class="score-item">
          <text class="label">最高分</text>
          <text class="value">{{ s.max_score ?? '—' }}</text>
        </view>
        <view class="score-item">
          <text class="label">最低分</text>
          <text class="value">{{ s.min_score ?? '—' }}</text>
        </view>
        <view class="score-item">
          <text class="label">平均分</text>
          <text class="value">{{ s.avg_score ?? '—' }}</text>
        </view>
      </view>
      <view class="count-row">
        <text class="text-muted">进复试 {{ s.retest_count }} · 录取 {{ s.admit_count }}</text>
      </view>
      <!-- VIP 分段明细 -->
      <view v-if="s.score_segments && s.score_segments.length" class="segments">
        <view class="segments-title">
          <text class="text-muted">分数段分布</text>
        </view>
        <view v-for="seg in s.score_segments" :key="`${seg.min}-${seg.max}`" class="segment-bar">
          <text class="seg-range">{{ seg.min }}-{{ seg.max }}</text>
          <view class="bar-bg">
            <view class="bar-fill" :style="{ width: barWidth(seg.count) + '%' }"></view>
          </view>
          <text class="seg-count">{{ seg.count }}</text>
        </view>
      </view>
    </view>

    <view v-if="!loading && stats.length === 0" class="empty">
      <text class="text-muted">暂无复录比数据</text>
    </view>

    <view v-if="stats.length > 0" class="footer">
      <button class="btn-ghost" @tap="goReport">填报我的分数</button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { isVip } from "@/utils/auth"

const smId = ref(null)
const title = ref("")
const stats = ref([])
const loading = ref(false)
const needVip = ref(false)

const maxCount = computed(() => {
  let m = 0
  for (const s of stats.value) {
    if (s.score_segments) {
      for (const seg of s.score_segments) {
        if (seg.count > m) m = seg.count
      }
    }
  }
  return m || 1
})

function barWidth(c) {
  return Math.round((c / maxCount.value) * 100)
}

onLoad((opts) => {
  smId.value = opts.sm_id
  title.value = decodeURIComponent(opts.title || "")
  loadData()
})

async function loadData() {
  if (!smId.value) return
  loading.value = true
  try {
    const r = await get(API.ADMISSION_STATS,
      { school_major_id: smId.value }, { needAuth: isVip() })
    if (r && r.code === 0) {
      stats.value = r.data.items || r.data || []
      needVip.value = !isVip()
    }
  } catch (e) {} finally {
    loading.value = false
  }
}

function goVip() {
  uni.navigateTo({ url: "/pages/vip/plans" })
}

function goReport() {
  uni.navigateTo({
    url: `/pages/report/edit?sm_id=${smId.value}&title=${encodeURIComponent(title.value)}`,
  })
}
</script>

<style scoped>
.page-title {
  margin-bottom: 24rpx;
}
.title {
  font-size: 36rpx;
  font-weight: bold;
}
.vip-tip {
  background: linear-gradient(135deg, #fff8e6 0%, #fff4d9 100%);
  padding: 24rpx;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.vip-btn {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  color: #fff;
  border-radius: 32rpx;
  font-size: 24rpx;
  height: 60rpx;
  line-height: 60rpx;
  padding: 0 24rpx;
  margin: 0;
}
.stat-card {
  margin-bottom: 24rpx;
}
.year-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}
.year {
  font-size: 32rpx;
  font-weight: bold;
  color: #3a7afe;
}
.ratio {
  font-size: 24rpx;
  color: #ff6b6b;
  font-weight: bold;
}
.score-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-bottom: 16rpx;
}
.score-item {
  text-align: center;
  background: #f5f6fa;
  padding: 16rpx 0;
  border-radius: 8rpx;
}
.label {
  display: block;
  font-size: 22rpx;
  color: #999;
  margin-bottom: 8rpx;
}
.value {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}
.count-row {
  font-size: 24rpx;
}
.segments {
  margin-top: 16rpx;
  border-top: 2rpx solid #f0f0f0;
  padding-top: 16rpx;
}
.segments-title {
  margin-bottom: 12rpx;
}
.segment-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 8rpx;
}
.seg-range {
  width: 140rpx;
  font-size: 22rpx;
  color: #666;
}
.bar-bg {
  flex: 1;
  height: 16rpx;
  background: #f0f0f0;
  border-radius: 8rpx;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a8bff 0%, #3a7afe 100%);
  border-radius: 8rpx;
}
.seg-count {
  width: 60rpx;
  font-size: 22rpx;
  color: #3a7afe;
  text-align: right;
}
.empty {
  text-align: center;
  padding: 60rpx 0;
}
.footer {
  margin-top: 32rpx;
}
</style>
