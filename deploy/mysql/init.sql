-- 供应链智能决策系统 - 数据库初始化脚本
-- 字符集: utf8mb4, 排序规则: utf8mb4_unicode_ci

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS supply_chain_risk
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE supply_chain_risk;

-- 创建应用用户（最小权限）
-- CREATE USER IF NOT EXISTS 'supply_chain_app'@'%' IDENTIFIED BY 'change_me_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON supply_chain_risk.* TO 'supply_chain_app'@'%';
-- FLUSH PRIVILEGES;