import { API, STORAGE_KEYS } from "./config"
import * as storage from "./storage"
import { post, get } from "./request"

// 微信登录：code → 后端换 token
export async function wechatLogin() {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: "weixin",
      success: async (res) => {
        if (!res.code) {
          reject(new Error("未获取到 code"))
          return
        }
        try {
          const r = await post(API.LOGIN, { code: res.code })
          if (r && r.code === 0) {
            const d = r.data
            storage.set(STORAGE_KEYS.ACCESS_TOKEN, d.access_token)
            storage.set(STORAGE_KEYS.REFRESH_TOKEN, d.refresh_token)
            if (d.user) storage.set(STORAGE_KEYS.USER_INFO, d.user)
            if (d.vip) storage.set(STORAGE_KEYS.VIP_INFO, d.vip)
            resolve(d)
          } else {
            reject(new Error((r && r.message) || "登录失败"))
          }
        } catch (e) {
          reject(e)
        }
      },
      fail: (err) => reject(err),
    })
  })
}

// 启动时调用：未登录则静默登录（小程序 wx.login 可直接调用）
export async function ensureLogin() {
  const token = storage.get(STORAGE_KEYS.ACCESS_TOKEN)
  if (token) return true
  try {
    await wechatLogin()
    return true
  } catch (e) {
    console.warn("ensureLogin failed", e)
    return false
  }
}

// 需登录的页面 onShow 调用：未登录跳登录页
export async function requireAuth() {
  const token = storage.get(STORAGE_KEYS.ACCESS_TOKEN)
  if (token) return true
  return new Promise((resolve) => {
    uni.showModal({
      title: "提示",
      content: "该功能需要登录后使用，是否现在登录？",
      success: async (r) => {
        if (r.confirm) {
          const ok = await ensureLogin()
          resolve(ok)
        } else {
          resolve(false)
        }
      },
    })
  })
}

export async function logout() {
  try {
    await post(API.LOGOUT, {}, { needAuth: true })
  } catch (e) {
    // 忽略网络失败
  }
  storage.remove(STORAGE_KEYS.ACCESS_TOKEN)
  storage.remove(STORAGE_KEYS.REFRESH_TOKEN)
  storage.remove(STORAGE_KEYS.USER_INFO)
  storage.remove(STORAGE_KEYS.VIP_INFO)
}

export async function fetchProfile() {
  const r = await get(API.PROFILE, {}, { needAuth: true })
  if (r && r.code === 0) {
    storage.set(STORAGE_KEYS.USER_INFO, r.data.user)
    storage.set(STORAGE_KEYS.VIP_INFO, r.data.vip)
    return r.data
  }
  return null
}

export function getUserInfo() {
  return storage.get(STORAGE_KEYS.USER_INFO) || {}
}

export function getVipInfo() {
  return storage.get(STORAGE_KEYS.VIP_INFO) || null
}

export function isVip() {
  const v = getVipInfo()
  return !!(v && v.is_active)
}
