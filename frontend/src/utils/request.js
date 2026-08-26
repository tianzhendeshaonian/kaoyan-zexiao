import { API, BASE_URL, API_PREFIX, STORAGE_KEYS, USE_MOCK } from "./config"
import * as storage from "./storage"
import { mockMatch } from "./mock"

let refreshing = false
let waitQueue = []

// 主请求方法
export async function request(options) {
  const {
    url,
    method = "GET",
    data = {},
    header = {},
    needAuth = false,
    rawUrl = false,
  } = options

  // 本地预览 mock 拦截：USE_MOCK 时所有请求都走 mock，绝不发起真实网络请求
  // （避免 H5 预览调 localhost 后端失败，触发 uni 框架"连接服务器超时"错误页）
  if (USE_MOCK) {
    const mockRes = mockMatch(url, method, data)
    if (mockRes !== undefined) return Promise.resolve(mockRes)
    const err = new Error(`mock 未命中: ${method} ${url}`)
    console.warn("[request] mock 未命中", url)
    uni.showToast({ title: `mock 未命中 ${url}`, icon: "none", duration: 3000 })
    return Promise.reject(err)
  }

  const fullUrl = rawUrl ? url : `${BASE_URL}${API_PREFIX}${url}`
  const headers = { "Content-Type": "application/json", ...header }

  if (needAuth) {
    const token = storage.get(STORAGE_KEYS.ACCESS_TOKEN)
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: headers,
      success: async (res) => {
        // 401 → 尝试 refresh
        if (res.statusCode === 401 && needAuth) {
          const ok = await tryRefresh()
          if (ok) {
            // 重发原请求
            const token = storage.get(STORAGE_KEYS.ACCESS_TOKEN)
            headers.Authorization = `Bearer ${token}`
            uni.request({
              url: fullUrl, method, data, header: headers,
              success: (r2) => resolve(r2.data),
              fail: (e) => reject(e),
            })
          } else {
            // refresh 失败 → 跳登录
            storage.remove(STORAGE_KEYS.ACCESS_TOKEN)
            storage.remove(STORAGE_KEYS.REFRESH_TOKEN)
            uni.reLaunch({ url: "/pages/login/index" })
            reject(new Error("未登录"))
          }
          return
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const msg = (res.data && res.data.message) || `请求失败 ${res.statusCode}`
          uni.showToast({ title: msg, icon: "none" })
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        uni.showToast({ title: "网络异常", icon: "none" })
        reject(err)
      },
    })
  })
}

// 自动 refresh 一次
async function tryRefresh() {
  if (refreshing) {
    return new Promise((resolve) => waitQueue.push(resolve))
  }
  refreshing = true
  const refreshToken = storage.get(STORAGE_KEYS.REFRESH_TOKEN)
  if (!refreshToken) {
    refreshing = false
    waitQueue.forEach((r) => r(false))
    waitQueue = []
    return false
  }

  return new Promise((resolve) => {
    uni.request({
      url: `${BASE_URL}${API.REFRESH}`,
      method: "POST",
      data: { refresh_token: refreshToken },
      header: { "Content-Type": "application/json" },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.code === 0) {
          const d = res.data.data
          storage.set(STORAGE_KEYS.ACCESS_TOKEN, d.access_token)
          storage.set(STORAGE_KEYS.REFRESH_TOKEN, d.refresh_token)
          refreshing = false
          waitQueue.forEach((r) => r(true))
          waitQueue = []
          resolve(true)
        } else {
          refreshing = false
          waitQueue.forEach((r) => r(false))
          waitQueue = []
          resolve(false)
        }
      },
      fail: () => {
        refreshing = false
        waitQueue.forEach((r) => r(false))
        waitQueue = []
        resolve(false)
      },
    })
  })
}

// 便捷方法
export const get = (url, data = {}, opts = {}) =>
  request({ url, method: "GET", data, ...opts })

export const post = (url, data = {}, opts = {}) =>
  request({ url, method: "POST", data, ...opts })
