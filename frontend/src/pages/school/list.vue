<template>
  <view class="container">
    <view class="search-bar">
      <input v-model="keyword" class="search-input" placeholder="搜索院校名称"
             confirm-type="search" @confirm="onSearch" />
      <button class="search-btn" @tap="onSearch">搜索</button>
    </view>

    <view class="filter-bar">
      <picker :value="provinceIdx" :range="provinces" @change="onProvinceChange">
        <view class="filter-item">{{ provinceIdx === 0 ? '全部省份' : provinces[provinceIdx] }} ▾</view>
      </picker>
      <picker :value="levelIdx" :range="levels" @change="onLevelChange">
        <view class="filter-item">{{ levelIdx === 0 ? '全部层次' : levels[levelIdx] }} ▾</view>
      </picker>
    </view>

    <view v-for="s in list" :key="s.id" class="card school-card"
          @tap="goDetail(s.id)">
      <view class="school-header">
        <text class="school-name">{{ s.name }}</text>
        <view class="tags">
          <text v-if="s.level === '985'" class="tag tag-985">985</text>
          <text v-if="s.level === '211'" class="tag tag-211">211</text>
          <text v-if="s.is_self_line" class="tag" style="background:#e6ffed;color:#52c41a">自划线</text>
        </view>
      </view>
      <view class="school-meta">
        <text class="text-muted">{{ s.province }} · {{ s.city }}</text>
        <text class="text-muted"> · {{ s.school_type }}</text>
      </view>
      <view v-if="s.match_majors_count" class="match-info">
        <text class="text-primary">匹配专业 {{ s.match_majors_count }} 个</text>
      </view>
    </view>

    <view v-if="!loading && list.length === 0" class="empty">
      <text class="text-muted">暂无符合条件的院校</text>
    </view>

    <view v-if="loading" class="loading">
      <text class="text-muted">加载中...</text>
    </view>

    <view v-if="nextCursor" class="load-more" @tap="loadMore">
      <text class="text-primary">加载更多</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onReachBottom } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { get } from "@/utils/request"

const keyword = ref("")
const provinceIdx = ref(0)
const levelIdx = ref(0)
const provinces = ["全部", "北京", "上海", "江苏", "浙江", "广东", "湖北", "陕西", "四川", "山东", "湖南"]
const levels = ["全部", "985", "211", "双一流"]

const list = ref([])
const loading = ref(false)
const nextCursor = ref(null)

async function fetchList(reset = true) {
  if (loading.value) return
  loading.value = true
  try {
    const params = {
      limit: 20,
      keyword: keyword.value || undefined,
      province: provinceIdx.value > 0 ? provinces[provinceIdx.value] : undefined,
      level: levelIdx.value > 0 ? levels[levelIdx.value] : undefined,
    }
    if (!reset && nextCursor.value) params.cursor = nextCursor.value
    const r = await get(API.SCHOOLS, params)
    if (r && r.code === 0) {
      const data = r.data
      const items = data.items || data
      list.value = reset ? items : [...list.value, ...items]
      nextCursor.value = data.page?.next_cursor || null
    }
  } catch (e) {
    // ignore
  } finally {
    loading.value = false
  }
}

function onSearch() {
  nextCursor.value = null
  fetchList(true)
}

function onProvinceChange(e) {
  provinceIdx.value = e.detail.value
  onSearch()
}

function onLevelChange(e) {
  levelIdx.value = e.detail.value
  onSearch()
}

function loadMore() {
  if (nextCursor.value) fetchList(false)
}

onReachBottom(() => loadMore())

function goDetail(id) {
  uni.navigateTo({ url: `/pages/school/detail?id=${id}` })
}

fetchList(true)
</script>

<style scoped>
.search-bar {
  display: flex;
  margin-bottom: 16rpx;
}
.search-input {
  flex: 1;
  background: #fff;
  border-radius: 48rpx;
  height: 80rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.search-btn {
  margin-left: 16rpx;
  background: #3a7afe;
  color: #fff;
  border-radius: 48rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 28rpx;
  padding: 0 32rpx;
}

.filter-bar {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}
.filter-item {
  background: #fff;
  padding: 12rpx 24rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
  color: #555;
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
.tags {
  display: flex;
}
.school-meta {
  font-size: 24rpx;
}
.match-info {
  margin-top: 8rpx;
}

.empty, .loading {
  text-align: center;
  padding: 60rpx 0;
}
.load-more {
  text-align: center;
  padding: 32rpx 0;
}
</style>
