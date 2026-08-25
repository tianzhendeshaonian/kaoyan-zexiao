<script setup>
import { onLaunch, onShow } from "@dcloudio/uni-app"
import { ensureLogin } from "@/utils/auth"
import { initMockStorage } from "@/utils/mock"

onLaunch(() => {
  console.log("App onLaunch")
  initMockStorage()
  ensureLogin()
})
onShow(() => {
  console.log("App onShow")
})
</script>

<style>
/* 全局样式 */
page {
  background-color: #f5f6fa;
  color: #333;
  font-size: 28rpx;
  font-family: -apple-system, "PingFang SC", "Helvetica Neue", sans-serif;
}

.container {
  padding: 24rpx;
}

.btn-primary {
  background: linear-gradient(135deg, #4a8bff 0%, #3a7afe 100%);
  color: #fff;
  border-radius: 48rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  font-size: 32rpx;
}

.btn-ghost {
  background: #fff;
  color: #3a7afe;
  border: 2rpx solid #3a7afe;
  border-radius: 48rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
}

.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.text-muted {
  color: #999;
  font-size: 24rpx;
}

.text-primary {
  color: #3a7afe;
}

.tag {
  display: inline-block;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  margin-right: 8rpx;
}

.tag-985 {
  background: #fff4e6;
  color: #ff8c00;
}

.tag-211 {
  background: #e6f4ff;
  color: #1890ff;
}

.tag-vip {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  color: #fff;
}

.divider {
  height: 2rpx;
  background: #f0f0f0;
  margin: 16rpx 0;
}
</style>
