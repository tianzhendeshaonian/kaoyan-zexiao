-- 初始化脚本由 docker-compose 在首次启动时挂载到 /docker-entrypoint-initdb.d
-- 主要用于设置字符集与基础权限；表结构由 alembic 或 init_db.py 建立。

SET NAMES utf8mb4;
ALTER DATABASE kaoyan_zexiao CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
