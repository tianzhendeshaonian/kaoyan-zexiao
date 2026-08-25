<template>
  <view class="container">
    <view class="filter-bar">
      <picker :value="schoolIdx" :range="schoolNames" @change="onSchoolChange">
        <view class="filter-item">{{ schoolIdx === 0 ? '选择院校' : schoolNames[schoolIdx] }} ▾</view>
      </picker>
    </view>

    <view v-if="needVip" class="vip-tip">
      <text class="text-muted">开通 VIP 可查看近 5 年复试线明细</text>
      <button class="vip-btn" @tap="goVip">开通 VIP</button>
    </view>

    <view v-for="l in list" :key="l.id" class="card score-card">
      <view class="row">
        <text class="year">{{ l.year }}</text>
        <text class="score">{{ l.score }}</text>
      </view>
      <view class="meta">
        <text class="text-muted">{{ l.subject || '—' }}</text>
        <text class="text-muted"> · {{ l.major_direction || '—' }}</text>
      </view>
      <view v-if="l.school_name" class="school">
        <text class="text-muted">{{ l.school_name }}</text>
      </view>
    </view>

    <view v-if="!loading && list.length === 0" class="empty">
      <text class="text-muted">暂无复试线数据</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { isVip } from "@/utils/auth"

const schools = ref([])
const schoolIdx = ref(0)
const schoolNames = computed(() => ["全部", ...schools.value.map(s => s.name)])

const list = ref([])
const loading = ref(false)
const needVip = ref(false)

async function loadSchools() {
  try {
    const r = await get(API.SCHOOLS, { limit: 50 })
    if (r && r.code === 0) schools.value = r.data.items || []
  } catch (e) {}
}

async function loadLines() {
  loading.value = true
  try {
    const params = {}
    if (schoolIdx.value > 0) params.school_id = schools.value[schoolIdx.value - 1].id
    const r = await get(API.SCORE_LINES, params, { needAuth: isVip() })
    if (r && r.code === 0) {
      list.value = r.data.items || r.data || []
      // 若免费且返回较少，提示开通 VIP
      needVip.value = !isVip()
    }
  } catch (e) {} finally {
    loading.value = false
  }
}

function onSchoolChange(e) {
  schoolIdx.value = e.detail.value
  loadLines()
}

function goVip() {
  uni.navigateTo({ url: "/pages/vip/plans" })
}

loadSchools()
loadLines()
</script>

<style scoped>
.filter-bar {
  margin-bottom: 24rpx;
}
.filter-item {
  background: #fff;
  padding: 16rpx 24rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
  color: #555;
  display: inline-block;
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
.score-card {
  margin-bottom: 16rpx;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.year {
  font-size: 28rpx;
  color: #3a7afe;
  font-weight: bold;
}
.score {
  font-size: 48rpx;
  color: #ff6b6b;
  font-weight: bold;
}
.meta, .school {
  font-size: 24rpx;
  margin-top: 8rpx;
}
.empty {
  text-align: center;
  padding: 60rpx 0;
}
</style>
