-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建用户和权限（如果需要）
-- CREATE USER ccpm_app WITH PASSWORD 'ccpm_app_password';
-- GRANT ALL PRIVILEGES ON DATABASE ccpm_db TO ccpm_app;
-- GRANT ALL ON SCHEMA public TO ccpm_app;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO ccpm_app;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ccpm_app;

-- 设置时区
SET TIME ZONE 'UTC';

-- 创建基础配置表
CREATE TABLE IF NOT EXISTS app_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入基础配置
INSERT INTO app_config (key, value, description) VALUES
('app_version', '1.0.0', '应用程序版本'),
('max_agents', '10', '最大Agent数量'),
('max_tasks_per_agent', '100', '每个Agent最大任务数')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- 创建索引优化
CREATE INDEX IF NOT EXISTS idx_app_config_key ON app_config(key);

-- 授权
-- GRANT SELECT, INSERT, UPDATE, DELETE ON app_config TO ccpm_app;
-- GRANT USAGE, SELECT ON SEQUENCE app_config_id_seq TO ccpm_app;