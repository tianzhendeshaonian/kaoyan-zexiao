<template>
  <view class="container">
    <view class="filter-bar">
      <picker :value="yearIdx" :range="years" @change="onYearChange">
        <view class="filter-item">{{ years[yearIdx] }} ▾</view>
      </picker>
    </view>

    <view v-for="c in list" :key="c.id" class="card catalog-card">
      <view class="header">
        <text class="year">{{ c.year }}</text>
        <text class="direction">{{ c.direction || '—' }}</text>
      </view>
      <view class="info-grid">
        <view class="info-item">
          <text class="text-muted">拟招</text>
          <text class="num">{{ c.planned_number }}</text>
        </view>
        <view class="info-item">
          <text class="text-muted">推免</text>
          <text class="num">{{ c.push_number }}</text>
        </view>
      </view>
      <view v-if="c.exam_subjects && c.exam_subjects.length" class="subjects">
        <text v-for="(s, i) in c.exam_subjects" :key="i" class="subject-tag">{{ s }}</text>
      </view>
      <view v-if="c.reference_books" class="books">
        <text class="text-muted">参考书：{{ c.reference_books }}</text>
      </view>
    </view>

    <view v-if="!loading && list.length === 0" class="empty">
      <text class="text-muted">暂无招生目录数据</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { isVip } from "@/utils/auth"

const years = ["全部", "2025", "2024", "2023", "2022", "2021"]
const yearIdx = ref(0)
const list = ref([])
const loading = ref(false)

async function loadList() {
  loading.value = true
  try {
    const params = {}
    if (yearIdx.value > 0) params.year = years[yearIdx.value]
    const r = await get(API.ADMISSION_CATALOGS, params, { needAuth: isVip() })
    if (r && r.code === 0) list.value = r.data.items || r.data || []
  } catch (e) {} finally {
    loading.value = false
  }
}

function onYearChange(e) {
  yearIdx.value = e.detail.value
  loadList()
}

loadList()
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
.catalog-card {
  margin-bottom: 16rpx;
}
.header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 16rpx;
}
.year {
  font-size: 28rpx;
  font-weight: bold;
  color: #3a7afe;
}
.direction {
  font-size: 28rpx;
  color: #333;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-bottom: 16rpx;
}
.info-item {
  background: #f5f6fa;
  padding: 16rpx;
  border-radius: 8rpx;
  text-align: center;
}
.num {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-top: 8rpx;
}
.subjects {
  margin-top: 8rpx;
}
.subject-tag {
  display: inline-block;
  background: #e6f4ff;
  color: #1890ff;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
  font-size: 22rpx;
  margin: 4rpx 8rpx 4rpx 0;
}
.books {
  margin-top: 12rpx;
  font-size: 24rpx;
}
.empty {
  text-align: center;
  padding: 60rpx 0;
}
</style>
