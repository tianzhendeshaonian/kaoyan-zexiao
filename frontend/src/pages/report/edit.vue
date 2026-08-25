<template>
  <view class="container">
    <view v-if="title" class="page-title">
      <text>{{ title }}</text>
    </view>

    <view class="card form-card">
      <view class="form-item">
        <text class="label">年份</text>
        <picker :value="yearIdx" :range="years" @change="e => form.year = years[e.detail.value]">
          <view class="picker-value">{{ form.year }} ▾</view>
        </picker>
      </view>

      <view class="form-item">
        <text class="label">总分</text>
        <input v-model.number="form.total_score" type="number" class="input" placeholder="如 380" />
      </view>

      <view class="form-item">
        <text class="label">来源</text>
        <view class="radio-group">
          <view v-for="o in originTypes" :key="o" class="radio-item"
                :class="{ active: form.origin_type === o }"
                @tap="form.origin_type = o">
            <text>{{ o }}</text>
          </view>
        </view>
      </view>

      <view class="form-item">
        <text class="label">结果</text>
        <view class="radio-group">
          <view v-for="o in resultOptions" :key="o" class="radio-item"
                :class="{ active: form.result === o }"
                @tap="form.result = o">
            <text>{{ o }}</text>
          </view>
        </view>
      </view>

      <view class="form-item">
        <text class="label">本科层次（选填）</text>
        <input v-model="form.undergrad_level" class="input" placeholder="如 211" />
      </view>

      <view class="form-item">
        <text class="label">生源地（选填）</text>
        <input v-model="form.origin_province" class="input" placeholder="如 山东" />
      </view>

      <view class="form-item">
        <text class="label">匿名填报</text>
        <switch :checked="form.is_anonymous === 1" @change="onAnonChange" color="#3a7afe" />
        <text class="text-muted tip">不存储姓名/手机号等隐私字段</text>
      </view>

      <view class="consent-block">
        <view class="consent-row" @tap="consent = !consent">
          <view class="checkbox" :class="{ checked: consent }">
            <text v-if="consent" class="check-mark">✓</text>
          </view>
          <text class="consent-text">
            我已阅读并同意，自愿匿名分享上岸分数，仅用于平台统计参考
          </text>
        </view>
      </view>
    </view>

    <button class="btn-primary submit-btn" :loading="submitting" @tap="onSubmit">
      提交填报
    </button>
  </view>
</template>

<script setup>
import { ref, reactive } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { API } from "@/utils/config"
import { post } from "@/utils/request"
import { requireAuth } from "@/utils/auth"

const title = ref("")
const smId = ref(null)
const years = ["2025", "2024", "2023", "2022"]
const originTypes = ["一志愿", "调剂"]
const resultOptions = ["录取", "复试未录", "未进复试"]
const consent = ref(false)
const submitting = ref(false)

const form = reactive({
  year: "2024",
  total_score: "",
  origin_type: "一志愿",
  result: "录取",
  undergrad_level: "",
  origin_province: "",
  is_anonymous: 1,
  agree_anonymized: false,
})

onLoad(async (opts) => {
  if (!(await requireAuth())) {
    uni.navigateBack()
    return
  }
  if (opts.sm_id) {
    smId.value = opts.sm_id
    form.school_major_id = Number(opts.sm_id)
  }
  if (opts.title) title.value = decodeURIComponent(opts.title)
})

function onAnonChange(e) {
  form.is_anonymous = e.detail.value ? 1 : 0
}

async function onSubmit() {
  if (!smId.value) {
    uni.showToast({ title: "缺少专业信息", icon: "none" })
    return
  }
  if (!form.total_score || form.total_score < 0 || form.total_score > 500) {
    uni.showToast({ title: "请输入正确的总分", icon: "none" })
    return
  }
  if (!consent.value) {
    uni.showToast({ title: "请勾选同意匿名授权", icon: "none" })
    return
  }
  form.agree_anonymized = true
  submitting.value = true
  try {
    const r = await post(API.REPORTS, {
      ...form,
      school_major_id: smId.value,
    }, { needAuth: true })
    if (r && r.code === 0) {
      uni.showToast({ title: "填报成功", icon: "success" })
      setTimeout(() => uni.navigateBack(), 800)
    }
  } catch (e) {} finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page-title {
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 24rpx;
}
.form-card {
  margin-bottom: 32rpx;
}
.form-item {
  display: flex;
  align-items: center;
  margin-bottom: 24rpx;
  font-size: 28rpx;
}
.label {
  width: 200rpx;
  color: #333;
}
.input, .picker-value {
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
  padding: 12rpx 32rpx;
  background: #f5f6fa;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #666;
}
.radio-item.active {
  background: #3a7afe;
  color: #fff;
}
.tip {
  display: block;
  margin-left: 16rpx;
  font-size: 22rpx;
}
.consent-block {
  background: #f5f6fa;
  padding: 16rpx;
  border-radius: 8rpx;
  margin-top: 16rpx;
}
.consent-row {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}
.checkbox {
  width: 36rpx;
  height: 36rpx;
  border: 2rpx solid #ccc;
  border-radius: 6rpx;
  flex-shrink: 0;
  margin-top: 4rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.checkbox.checked {
  background: #3a7afe;
  border-color: #3a7afe;
}
.check-mark {
  color: #fff;
  font-size: 24rpx;
}
.consent-text {
  font-size: 24rpx;
  color: #666;
  line-height: 1.5;
}
.submit-btn {
  margin-top: 24rpx;
}
</style>
