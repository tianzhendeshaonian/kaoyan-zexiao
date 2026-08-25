// uni storage 封装
export function get(key) {
  try {
    return uni.getStorageSync(key)
  } catch (e) {
    return null
  }
}

export function set(key, value) {
  try {
    uni.setStorageSync(key, value)
  } catch (e) {
    console.warn("storage set failed", key, e)
  }
}

export function remove(key) {
  try {
    uni.removeStorageSync(key)
  } catch (e) {
    console.warn("storage remove failed", key, e)
  }
}

export function clearAll() {
  try {
    uni.clearStorageSync()
  } catch (e) {
    console.warn("storage clear failed", e)
  }
}
