<template>
  <view class="container">
    <view v-for="r in list" :key="r.id" class="card report-card">
      <view class="row">
        <text class="score">{{ r.total_score }}</text>
        <text class="year">{{ r.year }}</text>
      </view>
      <view class="meta">
        <text class="text-muted">{{ r.origin_type }} · {{ r.result }}</text>
      </view>
      <view class="meta">
        <text class="text-muted">
          {{ r.undergrad_level || '—' }} · {{ r.origin_province || '—' }}
        </text>
      </view>
      <view class="status-row">
        <text class="audit-tag" :class="r.audit_status">
          {{ auditLabel(r.audit_status) }}
        </text>
        <text class="text-muted">{{ formatTime(r.created_at) }}</text>
      </view>
    </view>

    <view v-if="!loading && list.length === 0" class="empty">
      <text class="text-muted">暂无填报记录</text>
      <button class="btn-ghost" @tap="goSchoolList">去填报</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { requireAuth } from "@/utils/auth"

const list = ref([])
const loading = ref(false)

onShow(async () => {
  if (!(await requireAuth())) return
  loadList()
})

async function loadList() {
  loading.value = true
  try {
    const r = await get(API.REPORTS_MINE, {}, { needAuth: true })
    if (r && r.code === 0) {
      list.value = r.data.items || []
    }
  } catch (e) {} finally {
    loading.value = false
  }
}

function auditLabel(s) {
  return { pending: "待审核", flagged: "异常标记", approved: "已通过", rejected: "已拒绝" }[s] || s
}

function formatTime(ts) {
  if (!ts) return ""
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

function goSchoolList() {
  uni.navigateTo({ url: "/pages/school/list" })
}
</script>

<style scoped>
.report-card {
  margin-bottom: 16rpx;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.score {
  font-size: 40rpx;
  font-weight: bold;
  color: #ff6b6b;
}
.year {
  font-size: 28rpx;
  color: #3a7afe;
  font-weight: bold;
}
.meta {
  font-size: 24rpx;
  margin-top: 8rpx;
}
.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16rpx;
  border-top: 2rpx solid #f0f0f0;
  padding-top: 16rpx;
}
.audit-tag {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
}
.audit-tag.pending {
  background: #fff4e6;
  color: #ff8c00;
}
.audit-tag.flagged {
  background: #fff1f0;
  color: #ff4d4f;
}
.audit-tag.approved {
  background: #e6ffed;
  color: #52c41a;
}
.audit-tag.rejected {
  background: #f5f5f5;
  color: #999;
}
.empty {
  text-align: center;
  padding: 80rpx 0;
}
.empty .btn-ghost {
  margin-top: 24rpx;
  width: 320rpx;
}
</style>
