# 数据库表结构 DATABASE_SCHEMA v1.0

引擎：MySQL 8 / utf8mb4 / utf8mb4_unicode_ci。命名：蛇形小写，复数表名。所有表带 `created_at` / `updated_at`。外键级联策略：UPDATE CASCADE, DELETE RESTRICT（避免误删）。

## ER 概览

```
schools 1──N school_majors N──1 majors N──1 disciplines
school_majors 1──N admission_catalogs / score_lines / admission_stats
users 1──N wechat_accounts / vip_memberships / vip_orders / user_score_reports
users N──N schools(收藏, via favorites)
schools 1──N pdf_sources ; 全局 crawl_logs / audit_logs
```

## 建表 SQL

```sql
SET NAMES utf8mb4;

-- 院校
CREATE TABLE schools (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code        VARCHAR(16)  NOT NULL COMMENT '院校代码',
  name        VARCHAR(128) NOT NULL,
  province    VARCHAR(32)  NOT NULL,
  city        VARCHAR(32),
  level       VARCHAR(16)  NOT NULL COMMENT '985/211/双一流/普通',
  school_type VARCHAR(32)  NOT NULL COMMENT '综合/理工/师范...',
  logo_url    VARCHAR(255),
  official_site   VARCHAR(255),
  graduate_site   VARCHAR(255) COMMENT '研究生院官网',
  is_self_line    TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否自划线院校',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_code (code),
  KEY idx_level_province (level, province),
  KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学科门类
CREATE TABLE disciplines (
  id    INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code  VARCHAR(8)  NOT NULL COMMENT '门类代码 01哲学...',
  name  VARCHAR(32) NOT NULL,
  UNIQUE KEY uk_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 专业
CREATE TABLE majors (
  id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code         VARCHAR(16) NOT NULL COMMENT '专业代码',
  name         VARCHAR(128) NOT NULL,
  discipline_id INT UNSIGNED NOT NULL,
  degree_type  VARCHAR(8) NOT NULL COMMENT '学硕/专硕',
  created_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_code (code),
  KEY idx_discipline (discipline_id),
  KEY idx_name (name),
  CONSTRAINT fk_major_discipline FOREIGN KEY (discipline_id) REFERENCES disciplines(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 院校开设专业
CREATE TABLE school_majors (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  school_id     BIGINT UNSIGNED NOT NULL,
  major_id      BIGINT UNSIGNED NOT NULL,
  college_name  VARCHAR(128) NOT NULL COMMENT '学院名',
  created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_school_major_college (school_id, major_id, college_name),
  KEY idx_major (major_id),
  CONSTRAINT fk_sm_school FOREIGN KEY (school_id) REFERENCES schools(id),
  CONSTRAINT fk_sm_major  FOREIGN KEY (major_id)  REFERENCES majors(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 招生目录（年度）
CREATE TABLE admission_catalogs (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  school_major_id BIGINT UNSIGNED NOT NULL,
  year            SMALLINT UNSIGNED NOT NULL,
  direction       VARCHAR(255) COMMENT '研究方向',
  exam_subjects   JSON NOT NULL COMMENT '["政治","英语一","数学二","专业课"]',
  planned_number  SMALLINT UNSIGNED DEFAULT 0 COMMENT '拟招生(含推免)',
  push_number     SMALLINT UNSIGNED DEFAULT 0 COMMENT '推免占用',
  reference_books TEXT,
  source_url      VARCHAR(255) NOT NULL,
  created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  KEY idx_sm_year (school_major_id, year),
  CONSTRAINT fk_ac_sm FOREIGN KEY (school_major_id) REFERENCES school_majors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 历年复试线
CREATE TABLE score_lines (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  school_major_id BIGINT UNSIGNED NOT NULL,
  year            SMALLINT UNSIGNED NOT NULL,
  line_type       VARCHAR(16) NOT NULL COMMENT 'national/self/college 国家线/自划线/院线',
  total_score     SMALLINT UNSIGNED NOT NULL,
  politics_score  SMALLINT UNSIGNED,
  foreign_lang_score SMALLINT UNSIGNED,
  business1_score SMALLINT UNSIGNED,
  business2_score SMALLINT UNSIGNED,
  source_url      VARCHAR(255) NOT NULL,
  created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_sm_year_type (school_major_id, year, line_type),
  CONSTRAINT fk_sl_sm FOREIGN KEY (school_major_id) REFERENCES school_majors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 复录比统计（脱敏：仅分数与人数，无姓名）
CREATE TABLE admission_stats (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  school_major_id BIGINT UNSIGNED NOT NULL,
  year            SMALLINT UNSIGNED NOT NULL,
  retest_count    SMALLINT UNSIGNED DEFAULT 0 COMMENT '复试人数',
  admit_count     SMALLINT UNSIGNED DEFAULT 0 COMMENT '录取人数',
  max_score       SMALLINT UNSIGNED,
  min_score       SMALLINT UNSIGNED,
  avg_score       DECIMAL(5,1),
  score_segments  JSON COMMENT '分数段分布(脱敏聚合)',
  source_url      VARCHAR(255) NOT NULL,
  created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_sm_year (school_major_id, year),
  CONSTRAINT fk_as_sm FOREIGN KEY (school_major_id) REFERENCES school_majors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户（不存身份证/真实姓名强校验；nickname 来自微信昵称）
CREATE TABLE users (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  nickname      VARCHAR(64),
  avatar_url    VARCHAR(255),
  phone         VARCHAR(20) COMMENT '仅VIP订单需要时采集,加密存储',
  status        TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1正常 0封禁',
  created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 微信绑定
CREATE TABLE wechat_accounts (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id     BIGINT UNSIGNED NOT NULL,
  openid      VARCHAR(64)  NOT NULL,
  unionid     VARCHAR(64),
  session_key VARCHAR(128) COMMENT '不入库或短期,见安全清单',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_openid (openid),
  KEY idx_user (user_id),
  CONSTRAINT fk_wa_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户上岸分数填报（脱敏：无姓名/证件号/联系方式）
CREATE TABLE user_score_reports (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          BIGINT UNSIGNED NULL COMMENT '登录用户可关联,对外不返回',
  school_major_id  BIGINT UNSIGNED NOT NULL,
  year             SMALLINT UNSIGNED NOT NULL,
  total_score      SMALLINT UNSIGNED NOT NULL,
  subject_scores   JSON COMMENT '各科分数',
  origin_type      VARCHAR(8) NOT NULL COMMENT '一志愿/调剂',
  result           VARCHAR(16) NOT NULL COMMENT '录取/复试未录/未进复试',
  undergrad_level  VARCHAR(32) COMMENT '本科层次(可选)',
  origin_province  VARCHAR(32) COMMENT '生源省份(可选,脱敏)',
  is_anonymous     TINYINT(1) NOT NULL DEFAULT 1,
  audit_status     VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected',
  created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  KEY idx_sm_year (school_major_id, year),
  KEY idx_user (user_id),
  KEY idx_audit (audit_status),
  CONSTRAINT fk_usr_sm FOREIGN KEY (school_major_id) REFERENCES school_majors(id),
  CONSTRAINT fk_usr_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VIP 会员
CREATE TABLE vip_memberships (
  id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  level      VARCHAR(8) NOT NULL COMMENT 'basic/vip/svip',
  start_at   DATETIME(3) NOT NULL,
  expire_at  DATETIME(3) NOT NULL,
  status     VARCHAR(16) NOT NULL COMMENT 'active/expired/canceled',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  KEY idx_user_expire (user_id, expire_at),
  CONSTRAINT fk_vm_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 订单
CREATE TABLE vip_orders (
  id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  order_no   VARCHAR(32) NOT NULL,
  plan       VARCHAR(32) NOT NULL COMMENT '月卡/季卡/年卡',
  amount     DECIMAL(8,2) NOT NULL,
  paid_at    DATETIME(3),
  status     VARCHAR(16) NOT NULL COMMENT 'pending/paid/refunded',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_order_no (order_no),
  KEY idx_user (user_id),
  CONSTRAINT fk_vo_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PDF 来源（爬虫/解析追踪）
CREATE TABLE pdf_sources (
  id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  school_id  BIGINT UNSIGNED NOT NULL,
  year       SMALLINT UNSIGNED NOT NULL,
  pdf_url    VARCHAR(255) NOT NULL,
  file_path  VARCHAR(255) COMMENT '本地缓存路径',
  doc_type   VARCHAR(32) NOT NULL COMMENT 'admission_list/retest_list/score_line',
  status     VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/parsed/failed',
  parsed_at  DATETIME(3),
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  KEY idx_school_year (school_id, year),
  KEY idx_status (status),
  CONSTRAINT fk_ps_school FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 爬虫日志（审计）
CREATE TABLE crawl_logs (
  id             BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  target_url    VARCHAR(255) NOT NULL,
  source_type    VARCHAR(32) NOT NULL,
  http_code      SMALLINT,
  duration_ms    INT UNSIGNED,
  delay_seconds  DECIMAL(4,1) NOT NULL COMMENT '本次访问延时(审计)',
  status         VARCHAR(16) NOT NULL COMMENT 'ok/retry/failed/skipped',
  message        VARCHAR(255),
  created_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_created (created_at),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 收藏
CREATE TABLE favorites (
  id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  school_id  BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uk_user_school (user_id, school_id),
  CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_fav_school FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 审计日志（VIP/异常）
CREATE TABLE audit_logs (
  id         BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED,
  endpoint   VARCHAR(128) NOT NULL,
  ip         VARCHAR(45),
  result     VARCHAR(16) NOT NULL COMMENT 'allow/deny/error',
  detail     VARCHAR(255),
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_user_created (user_id, created_at),
  KEY idx_result (result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 关键设计说明

1. **隐私脱敏**：`user_score_reports` 不含姓名/证件号/联系方式；`is_anonymous` 默认 1；`user_id` 仅后台关联，对外接口不返回。
2. **可溯源**：score_lines / admission_stats / admission_catalogs / pdf_sources 均带 `source_url`。
3. **复录比聚合**：`score_segments` 为脱敏聚合分布（如 `[{"min":350,"max":360,"count":12}]`），非个人数据。
4. **session_key 风险**：建议不持久化或加密短期存储（见安全清单），降低泄露后伪造风险。
5. **删除策略**：业务表 RESTRICT，关联子表 CASCADE，避免误删院校导致孤儿数据。
6. **索引**：检索路径 (level,province)、(school_id,major_id,year) 覆盖热点查询。
