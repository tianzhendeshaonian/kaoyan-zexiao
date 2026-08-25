<template>
  <view class="container">
    <!-- 顶部搜索 -->
    <view class="search-bar">
      <view class="search-input" @tap="goSchoolList">
        <text class="search-icon">🔍</text>
        <text class="placeholder">搜索院校名称</text>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="quick-grid">
      <view class="quick-item" @tap="go('/pages/school/list')">
        <text class="quick-icon">🏫</text>
        <text class="quick-text">院校检索</text>
      </view>
      <view class="quick-item" @tap="go('/pages/major/list')">
        <text class="quick-icon">📚</text>
        <text class="quick-text">专业检索</text>
      </view>
      <view class="quick-item" @tap="go('/pages/recommend/index')">
        <text class="quick-icon">🎯</text>
        <text class="quick-text">冲稳保</text>
      </view>
      <view class="quick-item" @tap="go('/pages/report/mine')">
        <text class="quick-icon">✍️</text>
        <text class="quick-text">我的填报</text>
      </view>
    </view>

    <!-- 热门院校 -->
    <view class="section">
      <view class="section-title">
        <text>热门院校</text>
        <text class="more" @tap="go('/pages/school/list')">查看更多 ›</text>
      </view>
      <view v-for="s in hotSchools" :key="s.id" class="card school-card"
            @tap="goSchoolDetail(s.id)">
        <view class="school-header">
          <text class="school-name">{{ s.name }}</text>
          <view class="school-tags">
            <text v-if="s.level === '985'" class="tag tag-985">985</text>
            <text v-if="s.level === '211'" class="tag tag-211">211</text>
          </view>
        </view>
        <view class="school-meta">
          <text class="text-muted">{{ s.province }} · {{ s.city }}</text>
          <text class="text-muted">· {{ s.school_type }}</text>
        </view>
      </view>
      <view v-if="hotSchools.length === 0" class="empty">
        <text class="text-muted">暂无数据，请先在「我的」登录</text>
      </view>
    </view>

    <!-- VIP 入口 -->
    <view class="vip-banner" @tap="go('/pages/vip/plans')">
      <view class="vip-left">
        <text class="vip-title">VIP 会员</text>
        <text class="vip-desc">解锁近5年复试线 · 复录比明细 · 无限冲稳保</text>
      </view>
      <text class="vip-arrow">立即开通 ›</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onPullDownRefresh } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { ensureLogin } from "@/utils/auth"

const hotSchools = ref([])

async function loadHot() {
  try {
    const r = await get(API.SCHOOLS, { limit: 5 })
    if (r && r.code === 0) {
      hotSchools.value = r.data.items || []
    }
  } catch (e) {
    // 静默
  }
}

onPullDownRefresh(async () => {
  await loadHot()
  uni.stopPullDownRefresh()
})

async function ensureAndLoad() {
  await ensureLogin()
  await loadHot()
}

ensureAndLoad()

function go(url) {
  uni.navigateTo({ url })
}

function goSchoolList() {
  uni.navigateTo({ url: "/pages/school/list" })
}

function goSchoolDetail(id) {
  uni.navigateTo({ url: `/pages/school/detail?id=${id}` })
}
</script>

<style scoped>
.search-bar {
  margin-bottom: 24rpx;
}
.search-input {
  background: #fff;
  border-radius: 48rpx;
  height: 80rpx;
  padding: 0 28rpx;
  display: flex;
  align-items: center;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.search-icon {
  font-size: 32rpx;
  margin-right: 12rpx;
}
.placeholder {
  color: #aaa;
  font-size: 28rpx;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 0;
  margin-bottom: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}
.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16rpx 0;
}
.quick-icon {
  font-size: 56rpx;
  margin-bottom: 12rpx;
}
.quick-text {
  font-size: 24rpx;
  color: #555;
}

.section {
  margin-bottom: 32rpx;
}
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
  font-size: 32rpx;
  font-weight: bold;
}
.more {
  font-size: 24rpx;
  color: #3a7afe;
  font-weight: normal;
}

.school-card {
  margin-bottom: 16rpx;
}
.school-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.school-name {
  font-size: 32rpx;
  font-weight: bold;
}
.school-tags {
  display: flex;
}
.school-meta {
  font-size: 24rpx;
}

.empty {
  text-align: center;
  padding: 60rpx 0;
}

.vip-banner {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  color: #fff;
  padding: 32rpx;
  border-radius: 16rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}
.vip-title {
  font-size: 32rpx;
  font-weight: bold;
  display: block;
}
.vip-desc {
  font-size: 24rpx;
  display: block;
  margin-top: 8rpx;
}
.vip-arrow {
  font-size: 28rpx;
}
</style>
