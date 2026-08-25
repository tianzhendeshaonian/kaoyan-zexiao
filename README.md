# 考研择校小程序（对标「呱呱研选」）

聚合高校研究生院公开招生信息，辅助考研生科学择校的微信小程序。前端 uni-app，后端 FastAPI，MySQL + Redis，pdfplumber 解析拟录取 PDF。

> ⚠️ 本仓库内 `backend/scripts/local_crawler_test.py` 等爬虫脚本**仅供本地测试**，禁止用于商业抓取。详见 [docs/CRAWLER_COMPLIANCE.md](docs/CRAWLER_COMPLIANCE.md)。

## 文档导航

| 文档 | 说明 |
|------|------|
| [docs/PRD.md](docs/PRD.md) | 产品需求文档 |
| [docs/TECH_DESIGN.md](docs/TECH_DESIGN.md) | 技术方案（架构/选型/API/部署/安全） |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | 数据库表结构 + 建表 SQL |
| [docs/CRAWLER_COMPLIANCE.md](docs/CRAWLER_COMPLIANCE.md) | 爬虫合规提醒 + 安全漏洞清单 |

## 技术栈

- 前端：uni-app（Vue3 + Vite）→ 编译微信小程序，Pinia，uni-ui
- 后端：FastAPI + Uvicorn，Pydantic v2，SQLAlchemy 2.0(async)，Alembic
- 存储：MySQL 8（utf8mb4）+ Redis（缓存/限流/会话）
- PDF 解析：pdfplumber
- 鉴权：微信登录换 openid + JWT（access/refresh）
- 部署：Docker Compose + Nginx + HTTPS

## 项目目录

```
kaoyan-zexiao/
├── docs/                          # 方案文档
│   ├── PRD.md                     # 产品需求
│   ├── TECH_DESIGN.md             # 技术方案
│   ├── DATABASE_SCHEMA.md         # 数据库表结构
│   └── CRAWLER_COMPLIANCE.md      # 爬虫合规 + 安全清单
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── main.py                # FastAPI 入口
│   │   ├── config.py              # 配置（环境变量）
│   │   ├── database.py            # MySQL 异步连接
│   │   ├── redis_client.py        # Redis 客户端
│   │   ├── deps.py                # 依赖注入（当前用户/VIP校验）
│   │   ├── models/                # SQLAlchemy ORM 模型
│   │   ├── schemas/               # Pydantic 入参/出参
│   │   ├── api/v1/                # 路由
│   │   │   ├── schools.py         # 院校检索
│   │   │   ├── majors.py          # 专业/招生目录
│   │   │   ├── scores.py          # 复试线
│   │   │   ├── admissions.py      # 复录比
│   │   │   ├── reports.py         # 用户上岸分数填报
│   │   │   ├── recommend.py       # 冲稳保
│   │   │   ├── users.py           # 微信登录
│   │   │   └── vip.py             # VIP 会员/订单
│   │   ├── core/                  # 鉴权/限流/微信SDK
│   │   │   ├── security.py        # JWT
│   │   │   ├── wechat.py          # code2session
│   │   │   └── ratelimit.py
│   │   ├── services/              # 业务层
│   │   │   ├── crawler.py         # 爬虫（本地测试）
│   │   │   ├── pdf_parser.py      # pdfplumber 解析
│   │   │   ├── stats.py           # 复录比/冲稳保算法
│   │   │   └── search.py          # 检索/筛选
│   │   └── utils/
│   ├── scripts/
│   │   ├── init_db.py             # 建表/种子
│   │   └── local_crawler_test.py  # 爬虫本地测试
│   ├── tests/                     # 测试用例
│   │   ├── test_pdf_parser.py
│   │   ├── test_stats.py
│   │   ├── test_api.py
│   │   └── test_security.py
│   ├── alembic/                   # 迁移
│   ├── requirements.txt
│   └── .env.example
├── frontend/                      # uni-app 小程序
│   ├── pages/
│   │   ├── index/                 # 首页
│   │   ├── search/                # 院校专业检索
│   │   ├── school-detail/         # 院校详情
│   │   ├── score-line/            # 历年复试线
│   │   ├── admission-dir/         # 招生目录
│   │   ├── stats/                 # 复录比
│   │   ├── report/                # 上岸分数填报
│   │   ├── recommend/             # 冲稳保
│   │   ├── vip/                   # 会员中心
│   │   ├── profile/               # 个人中心
│   │   └── login/
│   ├── components/
│   ├── api/                       # 请求封装
│   ├── store/                     # Pinia
│   ├── utils/
│   ├── static/
│   ├── App.vue
│   ├── main.js
│   ├── pages.json
│   ├── manifest.json
│   └── uni.scss
└── deploy/
    ├── docker-compose.yml         # mysql+redis+backend+nginx
    ├── nginx.conf
    └── mysql_init.sql             # 初始化脚本
```

## 开发流程

1. 复核 `docs/` 四份方案文档 → 确认范围
2. 后端：建表 → 鉴权/微信登录 → 检索/复试线 → 招生目录/复录比 → 分数填报/冲稳保 → VIP
3. 前端：uni-app 骨架 → 检索/详情 → 数据模块 → 个人中心/会员
4. 爬虫/PDF 解析：仅本地测试脚本
5. 测试与安全复核

## 合规声明

本产品仅聚合高校研究生院**公开发布**的招生信息，对用户自愿填报数据**默认匿名且不采集姓名/证件号/联系方式**等隐私字段。商业化部署前须完成数据来源授权、个保法评估与 ICP 备案。
