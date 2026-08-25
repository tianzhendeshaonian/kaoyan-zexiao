<template>
  <view class="login-page">
    <view class="logo">
      <text class="title">考研择校</text>
      <text class="subtitle">院校 · 复试线 · 复录比 · 冲稳保</text>
    </view>

    <view class="actions">
      <button class="btn-primary" @tap="onLogin" :loading="loading">
        微信一键登录
      </button>
      <view class="tips">
        <text>登录即代表同意</text>
        <text class="text-primary">《用户协议》</text>
        <text>和</text>
        <text class="text-primary">《隐私政策》</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { wechatLogin } from "@/utils/auth"
import { STORAGE_KEYS } from "@/utils/config"
import * as storage from "@/utils/storage"

const loading = ref(false)

onShow(() => {
  const token = storage.get(STORAGE_KEYS.ACCESS_TOKEN)
  if (token) {
    uni.switchTab({ url: "/pages/index/index" })
  }
})

async function onLogin() {
  if (loading.value) return
  loading.value = true
  try {
    await wechatLogin()
    uni.showToast({ title: "登录成功", icon: "success" })
    setTimeout(() => uni.switchTab({ url: "/pages/index/index" }), 600)
  } catch (e) {
    uni.showToast({ title: e.message || "登录失败", icon: "none" })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60rpx;
  background: linear-gradient(180deg, #eaf2ff 0%, #ffffff 100%);
}
.logo {
  text-align: center;
  margin-bottom: 120rpx;
}
.title {
  display: block;
  font-size: 64rpx;
  font-weight: bold;
  color: #3a7afe;
  margin-bottom: 16rpx;
}
.subtitle {
  display: block;
  color: #888;
  font-size: 28rpx;
}
.actions {
  margin-top: 40rpx;
}
.btn-primary {
  width: 100%;
  background: linear-gradient(135deg, #4a8bff 0%, #3a7afe 100%);
  color: #fff;
  border-radius: 48rpx;
  height: 96rpx;
  line-height: 96rpx;
  font-size: 32rpx;
}
.tips {
  text-align: center;
  margin-top: 24rpx;
  font-size: 24rpx;
  color: #999;
}
</style>
