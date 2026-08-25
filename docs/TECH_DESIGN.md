# 技术方案 TECH_DESIGN v1.0

## 1. 总体架构

```
┌──────────────┐      HTTPS/JSON       ┌────────────────────────────┐
│ 微信小程序    │  ←─────────────────►  │  Nginx (TLS, 限流, 反代)   │
│ uni-app       │                       └────────────┬───────────────┘
└──────────────┘                                    │
                                                    ▼
                                         ┌────────────────────┐
                                         │  FastAPI (Uvicorn) │
                                         │  api/v1 路由        │
                                         │  services 业务层    │
                                         └───┬──────────┬─────┘
                              ┌──────────────┴──┐   ┌───┴──────────┐
                              ▼                 ▼   ▼              ▼
                      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                      │  MySQL 8     │  │   Redis      │  │ 本地文件/PDF │
                      │ (ORM 异步)   │  │ 缓存/限流/会话│  │ (pdfplumber) │
                      └──────────────┘  └──────────────┘  └──────────────┘
                                                                ▲
                              ┌─────────────────────────────────┴──────────┐
                              │ 离线爬虫脚本（仅本地测试，单线程+延时）       │
                              │  → 下载公开 PDF → pdfplumber 解析 → 写库     │
                              └────────────────────────────────────────────┘
```

- 在线请求链路：小程序 ⇄ Nginx ⇄ FastAPI ⇄ MySQL/Redis。
- 数据采集为**离线**流程，不阻塞在线服务，受 crawl_logs 审计。

## 2. 技术选型理由

| 层 | 选型 | 理由 |
|----|------|------|
| 前端 | uni-app(Vue3+Vite) | 一套代码编译微信小程序，生态成熟；Pinia 状态管理；uni-ui 组件 |
| 后端 | FastAPI + Uvicorn | 异步高性能、自动 OpenAPI 文档、Pydantic 强校验 |
| ORM | SQLAlchemy 2.0(async) + Alembic | 类型友好、迁移可控 |
| DB | MySQL 8 utf8mb4 | 关系型结构稳定，支持 JSON 字段存考试科目 |
| 缓存 | Redis 6 | 热点查询缓存、分布式限流、会话/refresh token |
| PDF | pdfplumber | 表格抽取能力强，适合结构化名单 |
| 鉴权 | JWT(access+refresh) + 微信 code2session | 无状态、易扩展 |
| 部署 | Docker Compose + Nginx + HTTPS | 单机 MVP 足够；小程序强制 HTTPS |

## 3. 后端模块划分

```
api/v1/          路由层（薄）：参数校验、鉴权、调用 service
services/         业务层：检索/统计/解析/爬虫
core/             横切：security(JWT)/wechat/ratelimit/vip_guard
models/           ORM 实体
schemas/          Pydantic 入参/出参 DTO
deps/             依赖注入：get_db / get_current_user / require_vip
```

### 路由清单

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | /api/v1/auth/login | 微信 code 登录 | 公开 |
| POST | /api/v1/auth/refresh | 刷新 token | refresh |
| GET  | /api/v1/schools | 院校检索（分页+筛选） | 公开 |
| GET  | /api/v1/schools/{id} | 院校详情 | 公开 |
| GET  | /api/v1/majors | 专业检索 | 公开 |
| GET  | /api/v1/admission-catalogs | 招生目录 | 公开(当前年)/VIP(历年) |
| GET  | /api/v1/score-lines | 历年复试线 | 公开(近1年)/VIP(近5年) |
| GET  | /api/v1/admission-stats | 复录比 | 免费(概览)/VIP(明细) |
| POST | /api/v1/reports | 上岸分数填报 | 登录 |
| GET  | /api/v1/reports/mine | 我的填报 | 登录 |
| POST | /api/v1/recommend | 冲稳保（每日3次/无限） | 登录 |
| GET/POST | /api/v1/vip/* | 会员/订单 | 登录 |

## 4. API 设计规范

- 统一响应体：`{ "code": 0, "msg": "ok", "data": {...} }`；错误 code 非 0。
- 分页：`?cursor=&limit=20`，返回 `next_cursor`。
- 鉴权头：`Authorization: Bearer <access_token>`。
- 时间：ISO8601 UTC。
- 版本前缀 `/api/v1`。
- 错误码：401 未登录、403 无权限（VIP 不足）、429 限流、422 参数错误。

## 5. 鉴权流程

1. 小程序 `wx.login()` → code。
2. 后端 `code2session`（带 AppID/Secret）→ openid + session_key。
3. openid 命中 wechat_accounts 则取 user_id，否则建 user + 绑定。
4. 签发 access(2h) + refresh(7d, 存 Redis 可吊销)。
5. 后续请求带 access；`deps.get_current_user` 解析。
6. VIP 路由额外 `require_vip` 校验 vip_memberships 有效期。

## 6. 数据采集与 PDF 解析设计

### 爬虫（仅本地测试）
- **单线程**，访问延时随机 2~5s，遵守 robots.txt。
- User-Agent 标识 `KaoYanZexiaoBot/0.1 (local-test; contact: xxx)`。
- 失败退避：429/503 退避指数增长，最多 3 次。
- **仅下载公开发布的拟录取/复试名单 PDF**，不抓取考生姓名/证件号/联系方式。
- 抓取记录写 crawl_logs（URL、状态、耗时、延时）。

### PDF 解析
- pdfplumber 按页抽表格，识别"拟录取名单/复试名单"。
- 提取结构化字段：分数、人数、专业方向（**不抽取姓名行**，遇姓名列跳过或脱敏）。
- 解析结果写 admission_stats / score_lines；原始 URL 写 source_url 供溯源。
- 失败 PDF 入 pdf_sources(status=failed) 人工复核。

## 7. 检索与缓存策略

- 院校/专业检索结果按查询指纹缓存 5min（Redis）。
- 复试线/复录比按 (school_id, major_id, year) 缓存 1h。
- 冲稳保结果按 (user_id, score, prefs) 缓存 10min。
- 写操作主动失效相关 key。

## 8. 限流策略

- 全局：IP 60 req/min。
- 冲稳保：登录用户 3 次/日（免费）/无限制（VIP）。
- 上岸分数填报：用户 5 次/日。
- 登录：IP 10 次/min 防爆破。

## 9. 部署架构

docker-compose 服务：
- `mysql:8` 持久卷 + 初始化脚本
- `redis:7-alpine` 持久化
- `backend`（Uvicorn + workers=2）依赖 mysql/redis
- `nginx` 反代 + TLS（小程序要求域名+备案+HTTPS）

生产前补充：负载均衡、日志聚合、健康检查、备份。

## 10. 安全设计（详见 CRAWLER_COMPLIANCE.md 安全清单）

- 输入校验：Pydantic 严格校验 + 长度/范围。
- SQL：全程参数化/ORM，禁拼接。
- SSRF：爬虫 URL 白名单（仅高校官网域名）+ 禁内网 IP。
- JWT：短 access + refresh 存 Redis 可吊销；密钥环境变量。
- IDOR：填报/订单查询带 user_id 过滤。
- 脱敏：用户填报记录对外不返回 user_id/身份。
- 限流：防爆破与爬取滥用。
- XSS：昵称/参考书目输出转义。
- 审计：VIP 调用与异常入 audit_logs。

## 11. 进度里程碑

- M1 骨架+微信登录+建表
- M2 检索+复试线
- M3 招生目录+复录比+PDF 解析
- M4 上岸分数填报+冲稳保
- M5 VIP+部署+测试/安全复核
