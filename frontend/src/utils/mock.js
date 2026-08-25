// 本地预览 mock 数据层（仅 USE_MOCK=true 时启用，对接后端时关闭）
import { API, STORAGE_KEYS, USE_MOCK } from "./config"
import * as storage from "./storage"

const MOCK_TOKEN = "mock-access-token"
const MOCK_USER = { id: 1, nickname: "研途同学" }
// 1796169600 ≈ 2027-01-01
const MOCK_VIP = { is_active: true, plan: "yearly", expire_at: 1796169600 }

// 启动时预置登录态，使 ensureLogin / requireAuth 直接通过
export function initMockStorage() {
  if (!USE_MOCK) return
  if (!storage.get(STORAGE_KEYS.ACCESS_TOKEN)) {
    storage.set(STORAGE_KEYS.ACCESS_TOKEN, MOCK_TOKEN)
    storage.set(STORAGE_KEYS.REFRESH_TOKEN, "mock-refresh-token")
    storage.set(STORAGE_KEYS.USER_INFO, MOCK_USER)
    storage.set(STORAGE_KEYS.VIP_INFO, MOCK_VIP)
  }
}

const ok = (data) => ({ code: 0, data })

// ===== 院校 =====
const schools = [
  { id: 1, name: "清华大学", level: "985", is_self_line: true, province: "北京", city: "北京", school_type: "综合", official_url: "https://www.tsinghua.edu.cn/yjsy/" },
  { id: 2, name: "北京大学", level: "985", is_self_line: true, province: "北京", city: "北京", school_type: "综合", official_url: "https://grs.pku.edu.cn/" },
  { id: 3, name: "中国人民大学", level: "985", is_self_line: true, province: "北京", city: "北京", school_type: "文法", official_url: "http://grs.ruc.edu.cn/" },
  { id: 4, name: "北京航空航天大学", level: "985", is_self_line: true, province: "北京", city: "北京", school_type: "工科", official_url: "http://graduate.buaa.edu.cn/" },
  { id: 5, name: "复旦大学", level: "985", is_self_line: true, province: "上海", city: "上海", school_type: "综合", official_url: "https://gsao.fudan.edu.cn/" },
  { id: 6, name: "上海交通大学", level: "985", is_self_line: true, province: "上海", city: "上海", school_type: "工科", official_url: "https://www.gs.sjtu.edu.cn/" },
  { id: 7, name: "南京大学", level: "985", is_self_line: false, province: "江苏", city: "南京", school_type: "综合", official_url: "https://grawww.nju.edu.cn/" },
  { id: 8, name: "浙江大学", level: "985", is_self_line: false, province: "浙江", city: "杭州", school_type: "综合", official_url: "http://grs.zju.edu.cn/" },
  { id: 9, name: "中央财经大学", level: "211", is_self_line: false, province: "北京", city: "北京", school_type: "财经", official_url: "http://sgy.cufe.edu.cn/" },
  { id: 10, name: "对外经济贸易大学", level: "211", is_self_line: false, province: "北京", city: "北京", school_type: "财经", official_url: "http://yjsy.uibe.edu.cn/" },
]

const schoolMajors = {
  1: [
    { id: 101, major_name: "计算机科学与技术", major_code: "081200", degree_type: "学硕", college_name: "计算机系" },
    { id: 102, major_name: "软件工程", major_code: "083500", degree_type: "学硕", college_name: "软件学院" },
    { id: 103, major_name: "计算机技术", major_code: "085404", degree_type: "专硕", college_name: "计算机系" },
  ],
  4: [
    { id: 401, major_name: "计算机科学与技术", major_code: "081200", degree_type: "学硕", college_name: "计算机学院" },
    { id: 402, major_name: "电子信息", major_code: "085400", degree_type: "专硕", college_name: "电子信息工程学院" },
  ],
}

// ===== 专业检索 =====
const majors = [
  { id: 101, name: "计算机科学与技术", code: "081200", discipline_name: "工学", degree_type: "学硕" },
  { id: 102, name: "软件工程", code: "083500", discipline_name: "工学", degree_type: "学硕" },
  { id: 103, name: "计算机技术", code: "085404", discipline_name: "工学", degree_type: "专硕" },
  { id: 201, name: "金融学", code: "020204", discipline_name: "经济学", degree_type: "学硕" },
  { id: 202, name: "金融", code: "025100", discipline_name: "经济学", degree_type: "专硕" },
  { id: 301, name: "法学", code: "030100", discipline_name: "法学", degree_type: "学硕" },
  { id: 302, name: "法律（非法学）", code: "035101", discipline_name: "法学", degree_type: "专硕" },
  { id: 401, name: "会计学", code: "120201", discipline_name: "管理学", degree_type: "学硕" },
  { id: 402, name: "会计", code: "125300", discipline_name: "管理学", degree_type: "专硕" },
]

// ===== 历年复试线 =====
const scoreLines = [
  { id: 1, school_id: 1, year: 2025, score: 385, subject: "工学", major_direction: "计算机科学与技术", school_name: "清华大学" },
  { id: 2, school_id: 1, year: 2024, score: 382, subject: "工学", major_direction: "计算机科学与技术", school_name: "清华大学" },
  { id: 3, school_id: 1, year: 2023, score: 378, subject: "工学", major_direction: "计算机科学与技术", school_name: "清华大学" },
  { id: 4, school_id: 1, year: 2022, score: 375, subject: "工学", major_direction: "计算机科学与技术", school_name: "清华大学" },
  { id: 5, school_id: 1, year: 2021, score: 370, subject: "工学", major_direction: "计算机科学与技术", school_name: "清华大学" },
  { id: 6, school_id: 4, year: 2025, score: 360, subject: "工学", major_direction: "计算机科学与技术", school_name: "北京航空航天大学" },
  { id: 7, school_id: 4, year: 2024, score: 355, subject: "工学", major_direction: "计算机科学与技术", school_name: "北京航空航天大学" },
  { id: 8, school_id: 4, year: 2023, score: 350, subject: "工学", major_direction: "计算机科学与技术", school_name: "北京航空航天大学" },
  { id: 9, school_id: 9, year: 2025, score: 360, subject: "管理学", major_direction: "会计学", school_name: "中央财经大学" },
  { id: 10, school_id: 9, year: 2024, score: 355, subject: "管理学", major_direction: "会计学", school_name: "中央财经大学" },
]

// ===== 招生目录 =====
const catalogs = [
  { id: 1, school_id: 1, year: 2025, direction: "计算机科学与技术", planned_number: 5, push_number: 2, reference_books: "《数据结构》严蔚敏；《计算机组成原理》唐朔飞" },
  { id: 2, school_id: 1, year: 2024, direction: "计算机科学与技术", planned_number: 6, push_number: 3, reference_books: "《数据结构》严蔚敏；《计算机组成原理》唐朔飞" },
  { id: 3, school_id: 4, year: 2025, direction: "计算机科学与技术", planned_number: 12, push_number: 5, reference_books: "《数据结构》严蔚敏" },
  { id: 4, school_id: 4, year: 2024, direction: "电子信息", planned_number: 20, push_number: 8, reference_books: "《信号与系统》郑君里" },
]

// ===== 复录比（按 school_major_id）=====
const admissionStats = {
  101: [
    { year: 2025, ratio: "1.5:1", max_score: 410, min_score: 385, avg_score: 392, retest_count: 15, admit_count: 10, score_segments: [{ min: 380, max: 399, count: 6 }, { min: 400, max: 419, count: 7 }, { min: 420, max: 439, count: 2 }] },
    { year: 2024, ratio: "1.4:1", max_score: 405, min_score: 382, avg_score: 390, retest_count: 14, admit_count: 10, score_segments: [{ min: 380, max: 399, count: 8 }, { min: 400, max: 419, count: 6 }] },
    { year: 2023, ratio: "1.6:1", max_score: 408, min_score: 378, avg_score: 388, retest_count: 16, admit_count: 10, score_segments: [{ min: 380, max: 399, count: 9 }, { min: 400, max: 419, count: 7 }] },
  ],
  401: [
    { year: 2025, ratio: "1.3:1", max_score: 390, min_score: 360, avg_score: 370, retest_count: 26, admit_count: 20, score_segments: [{ min: 360, max: 379, count: 12 }, { min: 380, max: 399, count: 10 }, { min: 400, max: 419, count: 4 }] },
    { year: 2024, ratio: "1.4:1", max_score: 388, min_score: 355, avg_score: 368, retest_count: 28, admit_count: 20, score_segments: [{ min: 360, max: 379, count: 14 }, { min: 380, max: 399, count: 11 }] },
  ],
}

// ===== 我的填报 =====
const myReports = [
  { id: 1, total_score: 372, year: 2025, origin_type: "一志愿", result: "拟录取", undergrad_level: "985", origin_province: "山东", audit_status: "approved", created_at: 1717200000 },
  { id: 2, total_score: 358, year: 2024, origin_type: "调剂", result: "复试未录取", undergrad_level: "211", origin_province: "河南", audit_status: "approved", created_at: 1684665600 },
  { id: 3, total_score: 340, year: 2025, origin_type: "一志愿", result: "待复试", undergrad_level: "双非", origin_province: "河北", audit_status: "pending", created_at: 1717800000 },
]

// ===== 冲稳保推荐池 =====
const recommendPool = [
  { school_major_id: 101, school_name: "清华大学", major_name: "计算机科学与技术", major_code: "081200", recent_min: 375, recent_max: 390, recent_avg: 382, ratio: "1.5:1" },
  { school_major_id: 102, school_name: "北京大学", major_name: "软件工程", major_code: "083500", recent_min: 370, recent_max: 385, recent_avg: 376, ratio: "1.4:1" },
  { school_major_id: 201, school_name: "复旦大学", major_name: "金融学", major_code: "020204", recent_min: 365, recent_max: 380, recent_avg: 372, ratio: "1.6:1" },
  { school_major_id: 401, school_name: "北京航空航天大学", major_name: "计算机科学与技术", major_code: "081200", recent_min: 350, recent_max: 365, recent_avg: 358, ratio: "1.3:1" },
  { school_major_id: 301, school_name: "中国人民大学", major_name: "法学", major_code: "030100", recent_min: 345, recent_max: 360, recent_avg: 352, ratio: "1.2:1" },
  { school_major_id: 402, school_name: "南京大学", major_name: "会计", major_code: "125300", recent_min: 340, recent_max: 355, recent_avg: 347, ratio: "1.3:1" },
  { school_major_id: 501, school_name: "浙江大学", major_name: "软件工程", major_code: "083500", recent_min: 335, recent_max: 350, recent_avg: 342, ratio: "1.4:1" },
  { school_major_id: 601, school_name: "中央财经大学", major_name: "会计学", major_code: "120201", recent_min: 330, recent_max: 345, recent_avg: 337, ratio: "1.5:1" },
]

function genRecommend(score, riskPref) {
  const offsets = {
    conservative: { c: 15, w: 5 },
    balance: { c: 10, w: 10 },
    aggressive: { c: 5, w: 15 },
  }
  const o = offsets[riskPref] || offsets.balance
  const chong = [], wen = [], bao = []
  for (const it of recommendPool) {
    const avg = it.recent_avg
    if (avg > score + o.c) chong.push(it)
    else if (avg >= score - o.w) wen.push(it)
    else bao.push(it)
  }
  return { chong, wen, bao }
}

// ===== VIP =====
const vipPlans = [
  { plan: "monthly", title: "月度", amount: 18, days: 30 },
  { plan: "quarterly", title: "季度", amount: 48, days: 90 },
  { plan: "yearly", title: "年度", amount: 168, days: 365 },
]

const myOrders = [
  { order_no: "MOCK202501001", plan: "年度 VIP", amount: 168, status: "paid", created_at: 1717200000, paid_at: 1717200600 },
  { order_no: "MOCK202501002", plan: "月度 VIP", amount: 18, status: "pending", created_at: 1718000000, paid_at: null },
]

// ===== 路由匹配 =====
export function mockMatch(url, method = "GET", data = {}) {
  // 鉴权
  if (url === API.LOGIN && method === "POST") {
    return ok({ access_token: MOCK_TOKEN, refresh_token: "mock-refresh-token", user: MOCK_USER, vip: MOCK_VIP })
  }
  if (url === API.REFRESH) return ok({ access_token: MOCK_TOKEN, refresh_token: "mock-refresh-token" })
  if (url === API.PROFILE) return ok({ user: MOCK_USER, vip: MOCK_VIP })
  if (url === API.LOGOUT) return ok({})

  // 院校列表
  if (url === API.SCHOOLS && method === "GET") {
    let items = schools.slice()
    if (data.keyword) items = items.filter((s) => s.name.includes(data.keyword))
    if (data.province) items = items.filter((s) => s.province === data.province)
    if (data.level) items = items.filter((s) => s.level === data.level)
    return ok({ items: items.slice(0, data.limit || 20), page: { next_cursor: null } })
  }
  // 院校详情
  let m = url.match(/^\/schools\/(\d+)$/)
  if (m) {
    const s = schools.find((x) => x.id === Number(m[1])) || schools[0]
    return ok(s)
  }
  // 院校开设专业
  m = url.match(/^\/schools\/(\d+)\/majors$/)
  if (m) {
    const items = schoolMajors[Number(m[1])] || schoolMajors[1]
    return ok({ items })
  }
  // 专业检索
  if (url === API.MAJORS) {
    let items = majors.slice()
    if (data.keyword) {
      const kw = data.keyword
      items = items.filter((x) => x.name.includes(kw) || x.code.includes(kw))
    }
    if (data.degree_type) items = items.filter((x) => x.degree_type === data.degree_type)
    return ok({ items: items.slice(0, data.limit || 30) })
  }
  // 历年复试线
  if (url === API.SCORE_LINES) {
    let items = scoreLines.slice()
    if (data.school_id) items = items.filter((x) => x.school_id === Number(data.school_id))
    return ok({ items })
  }
  // 招生目录
  if (url === API.ADMISSION_CATALOGS) {
    let items = catalogs.slice()
    if (data.school_id) items = items.filter((x) => x.school_id === Number(data.school_id))
    return ok({ items })
  }
  // 复录比
  if (url === API.ADMISSION_STATS) {
    const items = admissionStats[data.school_major_id] || admissionStats[101]
    return ok({ items })
  }
  // 上岸填报
  if (url === API.REPORTS_MINE) return ok({ items: myReports })
  if (url === API.REPORTS && method === "POST") return ok({ id: Date.now() })
  // 冲稳保
  if (url === API.RECOMMEND && method === "POST") {
    return ok(genRecommend(Number(data.score), data.risk_pref))
  }
  // VIP
  if (url === API.VIP_PLANS) return ok(vipPlans)
  if (url === API.VIP_ORDERS && method === "POST") {
    return ok({ order_no: "MOCK" + Date.now(), payment_params: { _demo: true } })
  }
  if (url === API.VIP_ORDERS_MINE) return ok({ items: myOrders })
  m = url.match(/^\/vip\/orders\/([^/]+)\/simulate-pay$/)
  if (m) return ok({})

  return undefined // 未命中，交给真实网络请求
}
