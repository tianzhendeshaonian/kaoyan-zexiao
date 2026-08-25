<template>
  <view class="container">
    <view class="search-bar">
      <input v-model="keyword" class="search-input" placeholder="搜索专业名称/代码"
             confirm-type="search" @confirm="onSearch" />
    </view>

    <view class="filter-bar">
      <picker :value="degreeIdx" :range="degrees" @change="onDegreeChange">
        <view class="filter-item">{{ degrees[degreeIdx] }} ▾</view>
      </picker>
    </view>

    <view v-for="m in list" :key="m.id" class="card major-card"
          @tap="goSchoolMajor(m)">
      <view class="major-header">
        <text class="major-name">{{ m.name }}</text>
        <text class="major-code text-muted">{{ m.code }}</text>
      </view>
      <view class="major-meta">
        <text class="text-muted">{{ m.discipline_name || '' }} · {{ m.degree_type }}</text>
      </view>
    </view>

    <view v-if="!loading && list.length === 0" class="empty">
      <text class="text-muted">暂无专业</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { API } from "@/utils/config"
import { get } from "@/utils/request"

const keyword = ref("")
const degreeIdx = ref(0)
const degrees = ["全部", "学硕", "专硕"]
const list = ref([])
const loading = ref(false)

async function fetchList() {
  loading.value = true
  try {
    const r = await get(API.MAJORS, {
      keyword: keyword.value || undefined,
      degree_type: degreeIdx.value > 0 ? degrees[degreeIdx.value] : undefined,
      limit: 30,
    })
    if (r && r.code === 0) list.value = r.data.items || r.data || []
  } catch (e) {} finally {
    loading.value = false
  }
}

function onSearch() { fetchList() }
function onDegreeChange(e) {
  degreeIdx.value = e.detail.value
  fetchList()
}

function goSchoolMajor(m) {
  // 后端 majors 接口返回的是 Major，未带 school_major_id
  // 简化：跳到院校检索让用户选具体院校
  uni.showActionSheet({
    itemList: ["查看开设此专业的院校"],
    success: () => {
      uni.navigateTo({
        url: `/pages/school/list?major_id=${m.id}&major_name=${encodeURIComponent(m.name)}`,
      })
    },
  })
}

fetchList()
</script>

<style scoped>
.search-bar {
  margin-bottom: 16rpx;
}
.search-input {
  background: #fff;
  border-radius: 48rpx;
  height: 80rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
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
.major-card {
  margin-bottom: 16rpx;
}
.major-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.major-name {
  font-size: 30rpx;
  font-weight: bold;
}
.major-code {
  font-size: 24rpx;
}
.major-meta {
  font-size: 24rpx;
}
.empty {
  text-align: center;
  padding: 60rpx 0;
}
</style>
