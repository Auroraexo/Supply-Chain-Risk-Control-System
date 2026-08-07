# GitHub Secrets 配置指南

> 适用项目：供应链智能决策系统 (Supply Chain Risk Control System)
>
> 更新日期：2026-08-05

---

## 目录

1. [概述](#概述)
2. [Secrets 配置位置速查](#secrets-配置位置速查)
3. [CI 流水线 Secrets](#ci-流水线-secrets)
4. [Docker 构建 Secrets](#docker-构建-secrets)
5. [部署流水线 Secrets](#部署流水线-secrets)
6. [应用运行时 Secrets](#应用运行时-secrets)
7. [可观测性 Secrets](#可观测性-secrets)
8. [安全存储最佳实践](#安全存储最佳实践)
9. [Secrets 轮换策略](#secrets-轮换策略)
10. [故障排查](#故障排查)

---

## 概述

本项目 CI/CD 流水线涉及 **3 类 Secrets 配置位置**：

| 配置位置 | 访问路径 | 适用场景 |
|---------|---------|---------|
| **Repository Secrets** | `Settings → Secrets and variables → Actions → Repository secrets` | 当前仓库所有流水线可用 |
| **Environment Secrets** | `Settings → Environments → {env_name} → Environment secrets` | 特定环境（staging/production）专用 |
| **Organization Secrets** | 组织级 `Settings → Secrets and variables → Actions` | 跨仓库共享（需管理员权限） |

> **优先级规则**：Environment Secrets > Repository Secrets > Organization Secrets

---

## Secrets 配置位置速查

```
Settings → Secrets and variables → Actions
│
├── Repository secrets（仓库级）
│   ├── CODECOV_TOKEN              ← CI 覆盖率
│   ├── DOCKERHUB_USERNAME         ← Docker 推送
│   ├── DOCKERHUB_TOKEN            ← Docker 推送
│   ├── OPENAI_API_KEY             ← Agent 评估（可选）
│   └── SLACK_WEBHOOK_URL          ← 通知（可选）
│
├── Environments
│   ├── staging（Environment secrets）
│   │   ├── STAGING_HOST
│   │   ├── STAGING_USER
│   │   ├── STAGING_SSH_KEY
│   │   ├── DATABASE_URL           ← 应用配置
│   │   ├── REDIS_URL              ← 应用配置
│   │   ├── JWT_SECRET_KEY         ← 应用配置
│   │   ├── RABBITMQ_URL           ← 应用配置
│   │   └── LANGSMITH_API_KEY      ← 可观测性
│   │
│   └── production（Environment secrets）
│       ├── PRODUCTION_HOST
│       ├── PRODUCTION_USER
│       ├── PRODUCTION_SSH_KEY
│       ├── DATABASE_URL
│       ├── REDIS_URL
│       ├── JWT_SECRET_KEY
│       ├── RABBITMQ_URL
│       └── LANGSMITH_API_KEY
```

---

## CI 流水线 Secrets

### 1. CODECOV_TOKEN

用于上传测试覆盖率报告到 Codecov。

#### 获取方式

1. 访问 [Codecov.io](https://about.codecov.io/) 并使用 GitHub 账号登录
2. 点击 **"Add repository"**，搜索并选择当前仓库
3. 进入仓库设置页面：`Settings → General`
4. 复制 **Repository Upload Token**

   ```
   格式: codecov-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

#### 配置

| 字段 | 值 |
|------|-----|
| Name | `CODECOV_TOKEN` |
| Value | 从 Codecov 复制的 token |
| 配置位置 | Repository secrets |

#### 安全建议

- 不同仓库使用不同的 token
- 在 Codecov 设置中启用 **"Enforce team membership"** 限制上传权限

---

### 2. OPENAI_API_KEY（可选）

用于 Agent 评估测试中调用真实 LLM API。日常 CI 使用 `LLM_MOCK_MODE=true` 不需要此密钥，仅在进行完整 Agent 回归测试时需要。

#### 获取方式

1. 访问 [OpenAI API Keys](https://platform.openai.com/api-keys)
2. 点击 **"+ Create new secret key"**
3. 命名：`supply-chain-risk-ci`（便于审计）
4. 选择权限：仅勾选 **"Model capabilities"**，不勾选计费类权限
5. 复制生成的 key（仅显示一次）

   ```
   格式: sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### 配置

| 字段 | 值 |
|------|-----|
| Name | `OPENAI_API_KEY` |
| Value | 从 OpenAI 复制的 key |
| 配置位置 | Repository secrets |

#### 费用控制

- 在 OpenAI 平台设置 **Monthly budget** 上限（建议 $50/月）
- 设置 **Usage limits** 中的 Hard limit
- CI 中优先使用 `LLM_MOCK_MODE=true`，仅在手动触发 Agent 评估时使用真实 API

---

## Docker 构建 Secrets

### 3. DOCKERHUB_USERNAME / DOCKERHUB_TOKEN（可选）

用于将 Docker 镜像推送到 Docker Hub（默认推送至 GitHub Container Registry，此配置为可选）。

#### 获取方式

**Docker Hub Access Token 创建**：

1. 访问 [Docker Hub Security](https://hub.docker.com/settings/security)
2. 点击 **"New Access Token"**
3. 命名：`github-actions-supply-chain`
4. 权限选择：**"Read, Write, Delete"** (推送镜像需要)
5. 复制生成的 token

   ```
   格式: dckr_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### 配置

| 字段 | 值 |
|------|-----|
| Name | `DOCKERHUB_USERNAME` |
| Value | 你的 Docker Hub 用户名 |
| Name | `DOCKERHUB_TOKEN` |
| Value | 上面生成的 Access Token |

> **注意**：使用 Access Token 而非密码，遵循最小权限原则。

#### 安全建议

- 使用 Access Token 而非 Docker Hub 密码
- 定期轮换 token（建议每 90 天）
- 如果只用 GHCR，可完全跳过此配置，Docker Hub 推送步骤会自动跳过（`continue-on-error: true`）

---

## 部署流水线 Secrets

### 4. STAGING_HOST / STAGING_USER / STAGING_SSH_KEY

用于 Staging 环境的 SSH 远程部署。

#### 获取方式

**SSH Key 生成**：

```bash
# 在本地生成专用的部署密钥对
ssh-keygen -t ed25519 -C "github-actions-staging-deploy" -f ~/.ssh/staging_deploy_key

# 输出示例：
# ~/.ssh/staging_deploy_key       ← 私钥（存入 GitHub Secrets）
# ~/.ssh/staging_deploy_key.pub   ← 公钥（部署到服务器）
```

**服务器配置**：

```bash
# 将公钥追加到服务器的 authorized_keys
ssh-copy-id -i ~/.ssh/staging_deploy_key.pub user@staging-server

# 或手动操作：
# 1. 登录 staging 服务器
# 2. 编辑 ~/.ssh/authorized_keys
# 3. 追加公钥内容
```

**SSH Key 内容提取**：

```bash
# 获取私钥内容（含换行符）
cat ~/.ssh/staging_deploy_key
```

#### 配置

| 字段 | 值 | 配置位置 |
|------|-----|---------|
| Name | `STAGING_HOST` | Environment: staging |
| Value | staging 服务器 IP 或域名（如 `10.0.1.50`） | |
| Name | `STAGING_USER` | Environment: staging |
| Value | 部署用户（如 `deploy`） | |
| Name | `STAGING_SSH_KEY` | Environment: staging |
| Value | 完整私钥内容（含 `-----BEGIN OPENSSH PRIVATE KEY-----` 头尾） | |

> **注意**：私钥内容必须完整粘贴，包括开头和结尾的标记行及所有换行符。

#### 安全建议

- 使用 **ed25519** 算法（非 RSA），更安全且性能更好
- 为 CI/CD 创建专用系统用户 `deploy`，而非使用 root
- 限制 deploy 用户权限：仅允许 `docker` 组和必要的目录访问
- `SSH_SSH_KEY` 应存储在 **Environment secrets** 而非 Repository secrets，利用 Environment 的保护规则

---

### 5. PRODUCTION_HOST / PRODUCTION_USER / PRODUCTION_SSH_KEY

用于 Production 环境的 SSH 远程部署。

#### 获取方式

与 Staging 完全相同，但使用 **独立的密钥对**：

```bash
# 生成生产环境专用的部署密钥对
ssh-keygen -t ed25519 -C "github-actions-production-deploy" -f ~/.ssh/production_deploy_key
```

> **严禁** Production 和 Staging 共用同一密钥对。

#### 配置

| 字段 | 值 | 配置位置 |
|------|-----|---------|
| Name | `PRODUCTION_HOST` | Environment: production |
| Value | production 服务器 IP 或域名 | |
| Name | `PRODUCTION_USER` | Environment: production |
| Value | 部署用户 | |
| Name | `PRODUCTION_SSH_KEY` | Environment: production |
| Value | 完整私钥内容 | |
| Name | `PRODUCTION_PORT` | Environment: production |
| Value | SSH 端口号（默认 22，非标准端口需填写） | |

#### Environment 保护规则（强烈建议）

在 `Settings → Environments → production` 中配置：

| 保护规则 | 建议值 | 说明 |
|---------|--------|------|
| Required reviewers | 至少 1 人 | Production 部署前必须有人审批 |
| Wait timer | 0-5 minutes | 部署前等待时间，给团队反应窗口 |
| Deployment branches | `main` | 仅 main 分支可触发部署 |
| Allowed branches | `main` | 限制部署来源 |

---

## 应用运行时 Secrets

以下 Secrets 用于应用运行时配置，通过 Docker Compose 或 K8s 的环境变量注入。

### 6. DATABASE_URL

MySQL 数据库连接字符串。

#### 格式

```
mysql+asyncmy://{username}:{password}@{host}:{port}/{database}
```

#### 示例

```
mysql+asyncmy://supply_chain_user:StrongP@ssw0rd!2024@10.0.1.100:3306/supply_chain_risk
```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `DATABASE_URL` |
| Value | 完整连接字符串 |
| 配置位置 | Environment secrets (staging / production) |

#### 安全建议

- **不同环境使用不同数据库用户和密码**
- 数据库用户遵循最小权限原则：
  - 应用用户：仅 `SELECT, INSERT, UPDATE, DELETE` 权限
  - 迁移用户：额外 `CREATE, ALTER, DROP` 权限（仅 CI 使用）
- 密码使用强随机生成：`openssl rand -base64 32`

---

### 7. REDIS_URL

Redis 连接字符串。

#### 格式

```
redis://[:password@]{host}:{port}[/{db}]
```

#### 示例

```
redis://:RedisP@ssw0rd!2024@10.0.1.101:6379/0
```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `REDIS_URL` |
| Value | 完整连接字符串 |
| 配置位置 | Environment secrets (staging / production) |

---

### 8. JWT_SECRET_KEY

JWT Token 签名密钥。

#### 生成方式

```bash
# 方式 1：使用 openssl（推荐）
openssl rand -base64 64

# 方式 2：使用 Python
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 输出示例：
# m8xQ7pR2vK9wL3nB6yF1dH5jA0sG4tZ8cV2bN6mX9qW3eR7uI1oP5aD8fJ2kL4
```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `JWT_SECRET_KEY` |
| Value | 生成的 64+ 字符随机字符串 |
| 配置位置 | Environment secrets (staging / production) |

> **绝对禁止**：hardcode 密钥、使用弱密码、staging 和 production 共用密钥。

---

### 9. RABBITMQ_URL（可选）

RabbitMQ 消息队列连接字符串。

#### 格式

```
amqp://{username}:{password}@{host}:{port}/{vhost}
```

#### 示例

```
amqp://supply_chain_mq:MQP@ssw0rd!2024@10.0.1.102:5672/supply_chain
```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `RABBITMQ_URL` |
| Value | 完整连接字符串 |
| 配置位置 | Environment secrets (staging / production) |

---

## 可观测性 Secrets

### 10. LANGSMITH_API_KEY

用于 Agent 调用链追踪与评估。

#### 获取方式

1. 访问 [LangSmith](https://smith.langchain.com/) 并登录
2. 进入 `Settings → API Keys`
3. 点击 **"Create API Key"**
4. 命名：`supply-chain-risk`
5. 复制生成的 key

   ```
   格式: lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `LANGSMITH_API_KEY` | 
| Value | 从 LangSmith 复制的 key |
| 配置位置 | Environment secrets (staging / production) |

#### 额外环境变量

在应用的 `.env` 中还需配置：

```bash
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=supply-chain-risk-{environment}
```

---

### 11. SLACK_WEBHOOK_URL（可选）

用于部署通知发送到 Slack 频道。

#### 获取方式

1. 访问 [Slack API Apps](https://api.slack.com/apps)
2. 创建新 App 或使用已有 App
3. 进入 **"Incoming Webhooks"**
4. 激活并点击 **"Add New Webhook to Workspace"**
5. 选择目标频道
6. 复制 Webhook URL

   ```
   格式: https://hooks.slack.com/services/{TEAM_ID}/{CHANNEL_ID}/{TOKEN}
   ```

#### 配置

| 字段 | 配置位置 |
|------|---------|
| Name | `SLACK_WEBHOOK_URL` |
| Value | 从 Slack 复制的 Webhook URL |
| 配置位置 | Repository secrets |

---

## 安全存储最佳实践

### 分级管理

```
┌─────────────────────────────────────────────┐
│            安全等级金字塔                      │
├─────────────────────────────────────────────┤
│  高敏感  │ JWT_SECRET_KEY, SSH_KEY, API_KEY  │
│          │ → Environment secrets + 轮换策略   │
├─────────────────────────────────────────────┤
│  中敏感  │ DATABASE_URL, REDIS_URL            │
│          │ → Environment secrets             │
├─────────────────────────────────────────────┤
│  低敏感  │ CODECOV_TOKEN, SLACK_WEBHOOK_URL  │
│          │ → Repository secrets              │
└─────────────────────────────────────────────┘
```

### 操作规范

| 规范 | 说明 |
|------|------|
| **禁止硬编码** | 任何密钥不得出现在代码、配置文件中 |
| **禁止日志打印** | 确保异常信息不会泄露密钥 |
| **禁止分支共享** | 不同环境使用不同密钥 |
| **禁止 git 提交** | `.env` 文件已在 `.gitignore` 中 |
| **使用 .env.example** | 提供模板文件，不包含真实值 |
| **最小权限** | 每个密钥仅授予所需的最小权限 |
| **审计日志** | 在 GitHub 审计日志中监控 Secrets 的访问和修改 |

### GitHub 安全设置

1. **启用 Actions 权限限制**：

   `Settings → Actions → General → Actions permissions`
   - 选择 **"Allow owner, and select non-owner, actions and reusable workflows"**
   - 仅允许 GitHub 官方和经过验证的 Actions

2. **限制 Secrets 访问范围**：

   `Settings → Secrets and variables → Actions → Secrets`
   - 点击每个 Secret 旁的 **"Manage access"**
   - 移除非必要的仓库访问权限

3. **启用强制代码审查**：

   `Settings → Branches → Add branch protection rule`
   - 对 `main` 分支启用：`Require pull request reviews before merging`
   - 启用：`Require status checks to pass before merging`

---

## Secrets 轮换策略

| Secret 类型 | 轮换周期 | 轮换方式 |
|------------|---------|---------|
| SSH Keys | 每 180 天 | 生成新密钥对 → 更新服务器 authorized_keys → 更新 GitHub Secret → 删除旧密钥 |
| JWT_SECRET_KEY | 每 90 天 | 生成新密钥 → 更新 Secret → 重启服务（旧 token 立即失效） |
| API Keys (OpenAI/LangSmith) | 每 90 天 | 在平台创建新 key → 更新 Secret → 删除旧 key |
| 数据库密码 | 每 90 天 | 创建新用户 → 更新 Secret → 灰度切换 → 删除旧用户 |
| DOCKERHUB_TOKEN | 每 90 天 | 创建新 token → 更新 Secret → 删除旧 token |

### 轮换检查清单

```bash
# 检查当前 Secrets 创建时间
# 在 GitHub Actions 中可查看每个 Secret 的 "Updated" 时间

# 手动轮换 JWT Secret（示例）
NEW_SECRET=$(openssl rand -base64 64)
echo "New JWT Secret: $NEW_SECRET"
# 将此值更新到 GitHub Environment Secrets 中
# 触发重新部署使新密钥生效
```

---

## 故障排查

### 常见错误

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `SSH Connection refused` | SSH 端口错误或防火墙阻止 | 检查 `PRODUCTION_PORT`，确认防火墙规则 |
| `Permission denied (publickey)` | SSH Key 未正确配置 | 确认公钥已追加到 `authorized_keys`，权限为 600 |
| `docker login: unauthorized` | Docker Hub Token 过期 | 轮换 `DOCKERHUB_TOKEN` |
| `Codecov: token not found` | Token 未配置或错误 | 检查 `CODECOV_TOKEN` 是否正确 |
| `Alembic: Access denied` | 数据库用户无迁移权限 | 检查数据库用户权限配置 |
| `OpenAI: invalid_api_key` | Key 过期或余额不足 | 检查 OpenAI 平台 key 状态和余额 |

### 验证 Secrets 是否生效

```bash
# 在 CI 中使用 Mask 验证（不打印真实值）
- name: Verify Secrets
  run: |
    if [ -z "${{ secrets.JWT_SECRET_KEY }}" ]; then
      echo "❌ JWT_SECRET_KEY 未配置"
      exit 1
    fi
    echo "✅ JWT_SECRET_KEY 已配置 (长度: ${#JWT_SECRET_KEY})"
```

---

## 快速配置命令（一键生成）

```bash
#!/bin/bash
# 一键生成所有需要的密钥（仅用于本地生成，生成后需手动配置到 GitHub）

echo "=== 生成 JWT Secret ==="
openssl rand -base64 64
echo ""

echo "=== 生成数据库密码 ==="
openssl rand -base64 32
echo ""

echo "=== 生成 Redis 密码 ==="
openssl rand -base64 24
echo ""

echo "=== 生成部署 SSH Key ==="
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./deploy_key -N ""
echo "私钥内容（存入 GitHub Secrets）："
cat ./deploy_key
echo "公钥内容（部署到服务器）："
cat ./deploy_key.pub
rm -f ./deploy_key ./deploy_key.pub
echo ""

echo "=== 请将以上生成的值配置到对应的 GitHub Secrets 中 ==="
```

---

> **最终提醒**：所有 Secrets 配置完成后，建议在非生产分支执行一次完整的 CI/CD 流水线以验证配置正确性，避免首次部署时才发现配置问题。