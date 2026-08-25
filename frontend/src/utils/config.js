// 全局配置
// 后端基础地址（dev 用本地，生产替换为线上 HTTPS 域名）
export const BASE_URL = "http://localhost:8000"

// API 版本前缀（request.js 已自动拼接，业务代码不需要带前缀）
export const API_PREFIX = "/api/v1"

// 是否测试环境（控制打印与模拟支付按钮）
export const IS_DEV = true

// 是否使用本地 mock 数据（H5 预览时打开；对接真实后端时改为 false）
export const USE_MOCK = true

// 存储键
export const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  REFRESH_TOKEN: "refresh_token",
  USER_INFO: "user_info",
  VIP_INFO: "vip_info",
}

// 桶颜色
export const BUCKET_COLORS = {
  chong: "#ff6b6b",
  wen: "#4a8bff",
  bao: "#52c41a",
  none: "#999",
}

export const BUCKET_LABELS = {
  chong: "冲",
  wen: "稳",
  bao: "保",
}

// API 路径常量（与后端路由对齐；不带 API_PREFIX，request 会自动加）
const P = ""
export const API = {
  // 鉴权
  LOGIN: `${P}/users/login`,
  REFRESH: `${P}/users/refresh`,
  LOGOUT: `${P}/users/logout`,
  PROFILE: `${P}/users/profile`,

  // 院校
  SCHOOLS: `${P}/schools`,
  schoolDetail: (id) => `${P}/schools/${id}`,
  schoolMajors: (id) => `${P}/schools/${id}/majors`,

  // 专业
  MAJORS: `${P}/majors`,

  // 复试线
  SCORE_LINES: `${P}/score-lines`,

  // 招生目录 / 复录比
  ADMISSION_CATALOGS: `${P}/admission-catalogs`,
  ADMISSION_STATS: `${P}/admission-stats`,

  // 上岸填报
  REPORTS: `${P}/reports`,
  REPORTS_MINE: `${P}/reports/mine`,
  reportDetail: (id) => `${P}/reports/mine/${id}`,

  // 冲稳保
  RECOMMEND: `${P}/recommend`,

  // VIP
  VIP_PLANS: `${P}/vip/plans`,
  VIP_ORDERS: `${P}/vip/orders`,
  VIP_ORDERS_MINE: `${P}/vip/orders/mine`,
  vipOrderDetail: (no) => `${P}/vip/orders/${no}`,
  vipSimulatePay: (no) => `${P}/vip/orders/${no}/simulate-pay`,
  VIP_ADVANCED: `${P}/vip/advanced-example`,
}
