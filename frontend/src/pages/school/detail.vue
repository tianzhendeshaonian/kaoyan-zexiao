<template>
  <view class="container">
    <view v-if="school" class="card school-header-card">
      <view class="name-row">
        <text class="name">{{ school.name }}</text>
        <view class="tags">
          <text v-if="school.level === '985'" class="tag tag-985">985</text>
          <text v-if="school.level === '211'" class="tag tag-211">211</text>
          <text v-if="school.is_self_line" class="tag"
                style="background:#e6ffed;color:#52c41a">自划线</text>
        </view>
      </view>
      <view class="meta-row">
        <text class="text-muted">{{ school.province }} · {{ school.city }}</text>
        <text class="text-muted"> · {{ school.school_type }}</text>
      </view>
      <view v-if="school.official_url" class="meta-row" @tap="copyUrl">
        <text class="text-primary">官网：{{ school.official_url }}</text>
      </view>
    </view>

    <!-- Tab 切换 -->
    <view class="tab-bar">
      <view v-for="t in tabs" :key="t.key" class="tab-item"
            :class="{ active: activeTab === t.key }" @tap="activeTab = t.key">
        <text>{{ t.label }}</text>
      </view>
    </view>

    <!-- 各 Tab 内容 -->
    <view v-if="activeTab === 'majors'">
      <view v-for="m in majors" :key="m.id" class="card major-card"
            @tap="goMajorStats(m.id, m.major_code, m.major_name)">
        <view class="major-header">
          <text class="major-name">{{ m.major_name }}（{{ m.major_code }}）</text>
          <text class="text-muted">{{ m.degree_type }}</text>
        </view>
        <view class="major-meta">
          <text class="text-muted">学院：{{ m.college_name || '—' }}</text>
        </view>
      </view>
      <view v-if="majors.length === 0" class="empty">
        <text class="text-muted">暂无专业数据</text>
      </view>
    </view>

    <view v-if="activeTab === 'scores'">
      <view v-for="l in scoreLines" :key="l.id" class="card">
        <view class="score-row">
          <text class="year">{{ l.year }}</text>
          <text class="score">{{ l.score }}</text>
          <text class="text-muted">{{ l.subject }} · {{ l.major_direction || '—' }}</text>
        </view>
      </view>
      <view v-if="scoreLines.length === 0" class="empty">
        <text class="text-muted">暂无复试线数据（开通 VIP 可查看近5年）</text>
      </view>
    </view>

    <view v-if="activeTab === 'catalogs'">
      <view v-for="c in catalogs" :key="c.id" class="card">
        <view class="catalog-row">
          <text class="year">{{ c.year }}</text>
          <text class="catalog-title">{{ c.direction || '—' }}</text>
        </view>
        <view class="catalog-meta">
          <text class="text-muted">拟招 {{ c.planned_number }} · 推免 {{ c.push_number }}</text>
        </view>
        <view v-if="c.reference_books" class="catalog-books">
          <text class="text-muted">参考书：{{ c.reference_books }}</text>
        </view>
      </view>
      <view v-if="catalogs.length === 0" class="empty">
        <text class="text-muted">暂无招生目录数据</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onLoad, onShow } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { get } from "@/utils/request"
import { isVip } from "@/utils/auth"

const schoolId = ref(null)
const school = ref(null)
const majors = ref([])
const scoreLines = ref([])
const catalogs = ref([])
const activeTab = ref("majors")
const tabs = [
  { key: "majors", label: "开设专业" },
  { key: "scores", label: "复试线" },
  { key: "catalogs", label: "招生目录" },
]

onLoad((opts) => {
  schoolId.value = opts.id
  loadSchool()
  loadMajors()
})

onShow(() => {
  // 切回页面时刷新 VIP 状态
  if (schoolId.value && activeTab.value === "scores") loadScoreLines()
  if (schoolId.value && activeTab.value === "catalogs") loadCatalogs()
})

async function loadSchool() {
  try {
    const r = await get(API.schoolDetail(schoolId.value))
    if (r && r.code === 0) school.value = r.data
  } catch (e) {}
}

async function loadMajors() {
  try {
    const r = await get(API.schoolMajors(schoolId.value))
    if (r && r.code === 0) majors.value = r.data.items || r.data || []
  } catch (e) {}
}

async function loadScoreLines() {
  try {
    const r = await get(API.SCORE_LINES, { school_id: schoolId.value },
      { needAuth: isVip() })
    if (r && r.code === 0) scoreLines.value = r.data.items || r.data || []
  } catch (e) {}
}

async function loadCatalogs() {
  try {
    const r = await get(API.ADMISSION_CATALOGS,
      { school_id: schoolId.value }, { needAuth: isVip() })
    if (r && r.code === 0) catalogs.value = r.data.items || r.data || []
  } catch (e) {}
}

function watchTab(val) {
  if (val === "scores" && scoreLines.value.length === 0) loadScoreLines()
  if (val === "catalogs" && catalogs.value.length === 0) loadCatalogs()
}

// 简易 watch
import { watch } from "vue"
watch(activeTab, watchTab)

function goMajorStats(smId, code, name) {
  uni.navigateTo({
    url: `/pages/admission/stats?sm_id=${smId}&title=${code} ${name}`,
  })
}

function copyUrl() {
  if (school.value && school.value.official_url) {
    uni.setClipboardData({ data: school.value.official_url })
  }
}
</script>

<style scoped>
.school-header-card {
  margin-bottom: 24rpx;
}
.name-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}
.name {
  font-size: 40rpx;
  font-weight: bold;
}
.tags {
  display: flex;
}
.meta-row {
  margin-top: 8rpx;
  font-size: 26rpx;
}

.tab-bar {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
  padding: 8rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}
.tab-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  font-size: 28rpx;
  color: #666;
  border-radius: 12rpx;
}
.tab-item.active {
  background: #3a7afe;
  color: #fff;
  font-weight: bold;
}

.major-card, .card {
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
.major-meta, .catalog-meta {
  font-size: 24rpx;
}
.catalog-books {
  margin-top: 8rpx;
  font-size: 24rpx;
}

.score-row, .catalog-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
}
.year {
  font-weight: bold;
  color: #3a7afe;
  width: 100rpx;
}
.score {
  font-size: 40rpx;
  color: #ff6b6b;
  font-weight: bold;
}
.catalog-title {
  flex: 1;
}

.empty {
  text-align: center;
  padding: 60rpx 0;
}
</style>
