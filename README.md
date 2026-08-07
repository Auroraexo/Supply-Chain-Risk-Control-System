# 供应链智能决策系统

<p align="center">
  <strong>Supply Chain Risk Control System</strong> — 基于多 Agent 协同架构的智能供应链风险管控平台
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/typescript-5.8-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [API 概览](#api-概览)
- [配置说明](#配置说明)
- [智能模型选择](#智能模型选择)
- [部署指南](#部署指南)
- [开发指南](#开发指南)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目概述

供应链智能决策系统是一个基于 **多 Agent 协同架构** 的智能风险管控平台，通过 AI Agent 协作完成供应链风险的识别、评估、决策与追溯。系统支持从原始数据接入到最终决策输出的全链路自动化处理，并提供实时监控面板。

### 核心流程

```
原始数据 → 风险评估(Agent) → 决策(Agent) → 人工审核 → 执行
    │            │              │              │
    └────────────┴──────────────┴──────────────┘
                 全链路追踪 (request_id)
```

---

## 核心特性

### 多 Agent 协同
- **Scout Agent**：数据采集与预处理
- **Analyst Agent**：供应链风险智能分析
- **Decider Agent**：基于规则引擎的智能决策
- 支持 Agent 执行日志追踪与性能监控

### 智能模型选择
- 自动检测本地 Ollama 模型，按参数规模分类（小模型 / 大模型）
- 基于查询复杂度评分（长度、关键词、结构、技术指标）动态路由
- 简单查询路由至小模型，复杂查询路由至大模型，优化 Token 成本

### 规则引擎
- 可配置的决策规则树 (`RuleNode`)
- 规则版本管理 (`RuleVersion`)，支持变更追溯
- 支持多种逻辑运算符（AND / OR / NOT）

### 认证与权限
- JWT Token 认证（Access Token + Refresh Token）
- 基于角色的访问控制：`admin` / `decider` / `analyst`
- 接口级别的权限校验

### 全链路可观测性
- 结构化日志（structlog）
- OpenTelemetry 分布式追踪
- LangSmith Agent 调用链追踪
- 企业微信 / 邮件通知集成

### 现代化前端
- 工业精密风 UI 设计
- 响应式布局（Desktop / Tablet / Mobile）
- 实时数据监控面板
- 风险等级可视化

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                     Nginx (反向代理)                   │
├─────────────────────────────────────────────────────┤
│                  Frontend (React 18)                  │
│            Vite + TypeScript + Tailwind CSS           │
├─────────────────────────────────────────────────────┤
│                  Backend (FastAPI)                    │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │ 认证模块  │ 风险评估 │ 决策模块  │ 规则管理      │  │
│  ├──────────┼──────────┼──────────┼──────────────┤  │
│  │  Agent 协同层 (LangGraph)                      │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │  │
│  │  │ Scout   │  │ Analyst  │  │  Decider    │  │  │
│  │  └─────────┘  └──────────┘  └─────────────┘  │  │
│  ├───────────────────────────────────────────────┤  │
│  │  智能模型选择器 (Model Selector)                │  │
│  │  ┌──────────────┐  ┌───────────────────────┐  │  │
│  │  │ Ollama Detector│  │ Query Complexity      │  │  │
│  │  │              │  │ Analyzer              │  │  │
│  │  └──────────────┘  └───────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│                    数据层                             │
│  ┌─────────┐  ┌─────────┐  ┌───────────────────┐   │
│  │ MySQL   │  │ Redis   │  │ RabbitMQ          │   │
│  │ 8.0     │  │ 7       │  │ (消息队列)         │   │
│  └─────────┘  └─────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 数据模型

| 模型 | 说明 | 所属层级 |
|------|------|----------|
| `RawData` | 原始业务数据，系统入口 | 输入层 |
| `AnalysisResult` | Agent 风险分析结果 | 分析决策层 |
| `DecisionResult` | 决策结果 | 分析决策层 |
| `RuleNode` | 树形决策规则配置 | 规则管理层 |
| `RuleVersion` | 规则变更快照 | 规则管理层 |
| `AgentExecutionLog` | Agent 执行日志 | 审计层 |
| `User` | 用户与权限管理 | 基础层 |

---

## 技术栈

### 后端

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | ≥0.115 |
| ASGI 服务器 | Uvicorn | ≥0.30 |
| 数据验证 | Pydantic v2 | ≥2.8 |
| ORM | SQLAlchemy (async) | ≥2.0 |
| 数据库 | MySQL 8.0 | — |
| 缓存 | Redis | ≥5.0 |
| 消息队列 | RabbitMQ (aio-pika) | ≥9.4 |
| 认证 | python-jose + passlib | — |
| AI 框架 | LangChain + LangGraph | ≥0.3 |
| LLM 支持 | OpenAI / Anthropic / Azure OpenAI / Ollama | — |
| 可观测性 | structlog + OpenTelemetry + LangSmith | — |

### 前端

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | React | 18.3 |
| 语言 | TypeScript | 5.8 |
| 构建工具 | Vite | 6.3 |
| 样式 | Tailwind CSS | 3.4 |
| 状态管理 | Zustand | 5.0 |
| 路由 | React Router | 7.3 |
| 图标 | Lucide React | 0.511 |

### 基础设施

| 类别 | 技术 |
|------|------|
| 容器化 | Docker + Docker Compose |
| 反向代理 | Nginx |
| CI/CD | GitHub Actions |
| 代码质量 | Ruff + MyPy + Bandit + pytest |

---

## 快速开始

### 环境要求

- **Python** ≥ 3.12
- **Node.js** ≥ 18
- **Docker** & **Docker Compose**（可选，用于容器化部署）
- **MySQL** 8.0 / **Redis** 7（本地开发需自行安装）

### 1. 克隆项目

```bash
git clone git@github.com:Auroraexo/Supply-Chain-Risk-Control-System.git
cd Supply-Chain-Risk-Control-System
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入必要配置（数据库连接、JWT 密钥等）
```

### 3. Docker 一键启动（推荐）

```bash
docker compose up -d
```

启动后访问：
- 后端 API 文档：`http://localhost:8000/api/v1/docs`
- 前端界面：`http://localhost:5173`
- RabbitMQ 管理面板：`http://localhost:15672`（guest/guest）

### 4. 本地开发启动

**后端：**

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -e ".[dev]"

# 启动后端服务
python -m app.main
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

---

## 项目结构

```
Supply-Chain-Risk-Control-System/
├── app/                        # 后端应用
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/                    # API 层
│   │   ├── deps.py             # 依赖注入
│   │   └── v1/                 # API v1 路由
│   │       ├── router.py       # 路由聚合
│   │       ├── auth.py         # 认证接口
│   │       ├── risk.py         # 风险评估接口
│   │       ├── decision.py     # 决策接口
│   │       ├── review.py       # 人工审核接口
│   │       ├── rule.py         # 规则管理接口
│   │       └── websocket.py    # WebSocket 接口
│   ├── models/                 # 数据模型 (SQLAlchemy)
│   │   ├── base.py             # 基础模型
│   │   ├── raw_data.py         # 原始数据
│   │   ├── analysis_result.py  # 分析结果
│   │   ├── decision_result.py  # 决策结果
│   │   ├── rule_node.py        # 规则节点
│   │   ├── rule_version.py     # 规则版本
│   │   ├── agent_execution_log.py # Agent 日志
│   │   └── user.py             # 用户模型
│   ├── schemas/                # Pydantic 数据校验
│   │   ├── common.py           # 通用响应模型
│   │   ├── auth.py             # 认证请求/响应
│   │   └── risk.py             # 风险评估请求/响应
│   ├── services/               # 业务逻辑层
│   │   ├── auth_service.py     # 认证服务
│   │   └── risk_service.py     # 风险评估服务
│   ├── repositories/           # 数据访问层
│   │   ├── base.py             # 基础 CRUD Repository
│   │   └── user_repo.py        # 用户 Repository
│   ├── agents/                 # Agent 协同层
│   │   └── nodes/              # Agent 节点
│   ├── rule_engine/            # 规则引擎
│   ├── core/                   # 核心基础设施
│   │   ├── config.py           # 全局配置
│   │   ├── database.py         # 数据库连接
│   │   ├── redis.py            # Redis 连接
│   │   ├── mq.py               # 消息队列连接
│   │   ├── security.py         # JWT 安全模块
│   │   ├── llm.py              # LLM 调用封装
│   │   ├── model_selector.py   # 智能模型选择
│   │   ├── logging_config.py   # 日志配置
│   │   ├── middleware.py       # 中间件
│   │   └── exceptions.py       # 异常定义
│   └── migrations/             # 数据库迁移
├── frontend/                   # 前端应用
│   └── src/
│       ├── pages/              # 页面组件
│       ├── components/         # 通用组件
│       ├── stores/             # 状态管理
│       └── api/                # API 调用
├── tests/                      # 测试
├── docs/                       # 文档
├── deploy/                     # 部署配置
│   ├── mysql/                  # MySQL 初始化脚本
│   └── nginx/                  # Nginx 配置
├── docker-compose.yml          # Docker Compose 编排
├── Dockerfile                  # 应用镜像构建
├── pyproject.toml              # Python 项目配置
└── .env.example                # 环境变量模板
```

---

## API 概览

所有 API 均以 `/api/v1` 为前缀。

### 认证

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/register` | 用户注册 | 公开 |
| POST | `/auth/login` | 用户登录 | 公开 |
| GET | `/auth/me` | 获取当前用户信息 | 登录用户 |

### 风险评估

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/risk/analyze` | 提交风险评估 | 登录用户 |
| GET | `/risk/analyze/{request_id}` | 查询评估结果 | 登录用户 |
| POST | `/risk/analyze/batch` | 批量风险评估 | 登录用户 |

### 决策

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/decision/{request_id}` | 执行决策 | decider / admin |
| GET | `/decision/{request_id}` | 查询决策结果 | 登录用户 |

### 规则管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/rule` | 创建规则 | admin |
| GET | `/rule` | 规则列表 | 登录用户 |
| GET | `/rule/{rule_id}` | 规则详情 | 登录用户 |
| PUT | `/rule/{rule_id}` | 更新规则 | admin |
| DELETE | `/rule/{rule_id}` | 删除规则 | admin |

### 人工审核

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/review/{request_id}` | 提交审核 | decider / admin |
| GET | `/review/{request_id}` | 查询审核状态 | 登录用户 |

### 角色权限

| 角色 | 权限范围 |
|------|----------|
| `admin` | read, write, admin, agent |
| `decider` | read, write, agent |
| `analyst` | read, agent |

---

## 配置说明

### 核心配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ENVIRONMENT` | 运行环境 | `development` |
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+asyncmy://root:password@localhost:3306/supply_chain_risk` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | RabbitMQ 连接字符串 | `amqp://guest:guest@localhost:5672/` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | —（**生产环境必须修改**） |
| `LLM_PROVIDER` | LLM 提供商 | `openai` |
| `LLM_MODEL` | LLM 模型名称 | `gpt-4o-mini` |
| `LLM_API_KEY` | LLM API 密钥 | — |
| `LLM_MOCK_MODE` | Mock 模式（不调用真实 API） | `false` |

### LLM 提供商

支持 4 种 LLM 提供商：

| 提供商 | `LLM_PROVIDER` 值 | 说明 |
|--------|-------------------|------|
| OpenAI | `openai` | 默认，需配置 `LLM_API_KEY` |
| Azure OpenAI | `azure_openai` | 需配置 `LLM_BASE_URL` + `LLM_API_KEY` |
| Anthropic | `anthropic` | 需配置 `LLM_API_KEY` |
| 本地模型 | `local` | 通过 Ollama 运行，使用智能模型选择 |

---

## 智能模型选择

系统内置了智能模型选择器，可自动检测本地 Ollama 模型并根据查询复杂度动态路由：

- **小模型**（≤8B 参数）：处理简单查询，如数据查询、状态检查
- **大模型**（>8B 参数）：处理复杂查询，如多 Agent 架构设计、风险分析

### 使用方式

```python
from app.core.llm import get_smart_llm

# 一行代码完成智能路由
llm = get_smart_llm(query="如何设计多Agent分布式架构并实现异步并发优化")
response = llm.invoke(query)
```

### 相关配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |
| `MODEL_SELECTOR_ENABLED` | 是否启用智能选择 | `true` |
| `MODEL_SELECTOR_SMALL_THRESHOLD` | 小模型参数上限 (B) | `8.0` |
| `MODEL_SELECTOR_COMPLEXITY_THRESHOLD` | 复杂度阈值 (0-1) | `0.5` |

---

## 部署指南

### Docker Compose 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 JWT_SECRET_KEY、LLM_API_KEY 等

# 2. 构建并启动
docker compose up -d --build

# 3. 查看服务状态
docker compose ps

# 4. 查看日志
docker compose logs -f app
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| App API | 8000 | 后端 API 服务 |
| Frontend Dev | 5173 | 前端开发服务器 |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| RabbitMQ | 5672 / 15672 | 消息队列 / 管理面板 |
| Nginx | 80 / 443 | 反向代理 |

### 生产环境部署

生产环境部署请参考 [GitHub Secrets 配置指南](docs/github-secrets-configuration-guide.md)，关键步骤：

1. 配置 GitHub Environments 的 `production` 环境 Secrets
2. 为 `production` 环境设置 Required reviewers 保护规则
3. 确保 `JWT_SECRET_KEY`、`DATABASE_URL` 等使用强随机值
4. 关闭 DEBUG 模式：`ENVIRONMENT=production`

---

## 开发指南

### 代码质量

```bash
# 代码格式化
ruff format .

# 代码检查
ruff check .

# 类型检查
mypy app/

# 安全扫描
bandit -r app/ -c pyproject.toml
```

### 运行测试

```bash
# 运行所有测试
pytest

# 仅运行单元测试
pytest -m unit

# 带覆盖率报告
pytest --cov=app --cov-report=html
```

### 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### Git 提交规范

遵循 Conventional Commits 规范：

- `feat:` 新功能
- `fix:` 修复 Bug
- `docs:` 文档变更
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具变更

---

## 贡献指南

欢迎贡献代码！请遵循以下流程：

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feat/your-feature`
3. 编写代码并通过测试：`pytest && ruff check .`
4. 提交变更：`git commit -m "feat: 添加新功能"`
5. 推送分支：`git push origin feat/your-feature`
6. 提交 **Pull Request**

### 开发规范

- Python 代码遵循 `ruff` 格式规范，行宽 100 字符
- 所有新功能需包含测试
- 核心模块使用 `TYPE_CHECKING` 懒加载以支持独立运行
- API 变更需同步更新 OpenAPI 文档

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。