<template>
  <view class="container">
    <!-- 用户信息 -->
    <view class="card profile-card">
      <view class="avatar">
        <text class="avatar-text">{{ userInfo.nickname ? userInfo.nickname[0] : 'U' }}</text>
      </view>
      <view class="info">
        <text class="nickname">{{ userInfo.nickname || '未登录' }}</text>
        <view class="vip-tag" v-if="vipActive">
          <text class="tag tag-vip">VIP</text>
          <text class="text-muted" v-if="vipInfo && vipInfo.expire_at">
            到期 {{ formatDate(vipInfo.expire_at) }}
          </text>
        </view>
        <view v-else>
          <button class="open-vip" @tap="goVip">开通 VIP</button>
        </view>
      </view>
    </view>

    <!-- 功能列表 -->
    <view class="menu">
      <view class="menu-item" @tap="go('/pages/report/mine')">
        <text>我的填报</text>
        <text class="arrow">›</text>
      </view>
      <view class="menu-item" @tap="go('/pages/vip/orders')">
        <text>我的订单</text>
        <text class="arrow">›</text>
      </view>
      <view class="menu-item" @tap="go('/pages/vip/plans')">
        <text>VIP 权益</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <view class="menu">
      <view class="menu-item" @tap="showPrivacy">
        <text>隐私政策</text>
        <text class="arrow">›</text>
      </view>
      <view class="menu-item" @tap="showAgreement">
        <text>用户协议</text>
        <text class="arrow">›</text>
      </view>
      <view class="menu-item" @tap="showCompliance">
        <text>数据来源与合规说明</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <button v-if="isLoggedIn" class="btn-ghost logout-btn" @tap="onLogout">
      退出登录
    </button>
    <button v-else class="btn-primary login-btn" @tap="goLogin">
      微信登录
    </button>

    <view class="version">
      <text class="text-muted">考研择校 v1.0.0</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue"
import { onShow } from "@dcloudio/uni-app"
import {
  ensureLogin, logout, fetchProfile, getUserInfo, getVipInfo,
} from "@/utils/auth"
import { STORAGE_KEYS } from "@/utils/config"
import * as storage from "@/utils/storage"

const userInfo = ref({})
const vipInfo = ref(null)
const vipActive = computed(() => !!(vipInfo.value && vipInfo.value.is_active))
const isLoggedIn = computed(() => !!userInfo.value.nickname)

onShow(async () => {
  // 切回页面时刷新本地状态
  userInfo.value = getUserInfo()
  vipInfo.value = getVipInfo()
  // 已登录则同步远端最新状态
  if (isLoggedIn.value) {
    await fetchProfile()
    userInfo.value = getUserInfo()
    vipInfo.value = getVipInfo()
  } else {
    // 静默登录（小程序场景）
    await ensureLogin()
    userInfo.value = getUserInfo()
    vipInfo.value = getVipInfo()
  }
})

function formatDate(ts) {
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

function go(url) {
  uni.navigateTo({ url })
}

function goVip() {
  uni.navigateTo({ url: "/pages/vip/plans" })
}

function goLogin() {
  uni.navigateTo({ url: "/pages/login/index" })
}

async function onLogout() {
  await logout()
  userInfo.value = {}
  vipInfo.value = null
  uni.showToast({ title: "已退出", icon: "success" })
}

function showPrivacy() {
  uni.showModal({
    title: "隐私政策",
    content: "本小程序不收集考生姓名、证件号、手机号等隐私字段。上岸分数填报默认匿名，仅用于统计参考。",
    showCancel: false,
  })
}

function showAgreement() {
  uni.showModal({
    title: "用户协议",
    content: "数据来源于高校研究生院公开发布的拟录取名单/招生目录。本平台不对数据准确性承担责任，仅供参考。",
    showCancel: false,
  })
}

function showCompliance() {
  uni.showModal({
    title: "数据来源与合规说明",
    content: "数据来源：高校研究生院官网公开发布的拟录取名单/复试名单/招生目录 PDF。爬虫仅本地测试用途，商用部署需取得授权。不存储考生姓名等隐私字段。",
    showCancel: false,
  })
}
</script>

<style scoped>
.profile-card {
  display: flex;
  align-items: center;
  padding: 32rpx 24rpx;
  margin-bottom: 24rpx;
}
.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #4a8bff 0%, #3a7afe 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 24rpx;
}
.avatar-text {
  color: #fff;
  font-size: 48rpx;
  font-weight: bold;
}
.info {
  flex: 1;
}
.nickname {
  font-size: 36rpx;
  font-weight: bold;
  display: block;
  margin-bottom: 8rpx;
}
.vip-tag {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.open-vip {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  color: #fff;
  border-radius: 32rpx;
  font-size: 24rpx;
  height: 56rpx;
  line-height: 56rpx;
  padding: 0 32rpx;
  margin: 0;
  display: inline-block;
}
.menu {
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}
.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 24rpx;
  font-size: 28rpx;
  border-bottom: 2rpx solid #f5f5f5;
}
.menu-item:last-child {
  border-bottom: none;
}
.arrow {
  color: #ccc;
  font-size: 32rpx;
}
.logout-btn, .login-btn {
  margin-top: 48rpx;
}
.version {
  text-align: center;
  margin-top: 32rpx;
  margin-bottom: 32rpx;
}
</style>
