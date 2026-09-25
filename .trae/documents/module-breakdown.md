# 供应链风险控制系统分层模块细化说明

## 1. 文档目的

本文档基于当前仓库源码整理，面向以下目标：

- 按 `后端 / 前端 / 数据层 / Agent 层` 细化说明模块职责。
- 说明各层之间的调用关系与主业务链路。
- 给出新成员阅读代码时的推荐入口与顺序。
- 标注源码与历史架构文档之间的差异，避免误读。

说明：

- 本文档以当前仓库源码为准。
- 历史文档如 `TECHNICAL_ARCHITECTURE.md` 可用于理解设计意图，但若与源码不一致，应优先相信源码。

---

## 2. 系统总览

这是一个面向供应链风险识别、分析、决策、审批与处置的前后端分离系统，核心特征包括：

- 后端采用 `FastAPI + SQLAlchemy + Redis + RabbitMQ`。
- 前端采用 `React + TypeScript + Vite + Zustand`。
- 风险分析与决策流程由 `LangGraph` 编排的多 Agent 流程驱动。
- 决策并非只依赖大模型，还结合规则引擎、人工审核和审计事件。
- 系统已具备生产基础能力，包括配置加密、Cookie 会话、通知 outbox、独立 worker、审计追踪与指标监控。

主业务链路可概括为：

`原始数据接入 -> 风险分析 -> Agent 协同决策 -> 结果持久化 -> 人工审核 / 风险处置 -> 通知与审计`

---

## 3. 后端层

后端目录位于 `app/`，是系统的业务中枢。其职责不是简单提供 CRUD，而是负责：

- 认证鉴权
- 风险分析与决策编排
- 规则执行
- 配置加载与运行时安全控制
- 通知、审计、指标与健康检查

### 3.1 后端总体分层

后端内部大致分为：

- `api/`：HTTP 与 WebSocket 接口层
- `services/`：业务编排层
- `repositories/`：数据访问层
- `models/`：数据库实体层
- `core/`：基础设施层
- `rule_engine/`：规则引擎层
- `agents/`：多 Agent 协同层
- `workers/`：异步后台任务层

### 3.2 应用入口与生命周期

核心文件：`app/main.py`

职责：

- 创建 FastAPI 应用实例
- 注册 CORS、中间件、异常处理器
- 挂载 API 路由与 WebSocket 路由
- 暴露 `/metrics`、`/health/live`、`/health/ready`
- 在应用关闭时释放数据库、Redis、RabbitMQ 连接

说明：

- 中间件顺序是显式设计的，包含请求防护、链路追踪、指标采集与请求日志。
- 文档地址只在非生产环境暴露，说明系统已考虑生产环境安全边界。

### 3.3 API 接口层

核心目录：`app/api/v1/`

职责：

- 对外暴露业务能力
- 处理请求参数校验和响应模型封装
- 将业务逻辑委托给 `services/`
- 统一接入登录态依赖

主要接口模块：

- `auth.py`：登录、登出、用户会话
- `risk.py`：风险分析提交、查询、批量分析
- `decision.py`：生成决策、查询结果、查看追踪链路
- `review.py`：人工审核相关操作
- `rule.py`：规则配置与版本管理
- `dashboard.py`：仪表盘数据聚合
- `raw_data_crud.py`：原始数据增删改查
- `settings.py`：系统设置与模型配置
- `automation.py`：AI 自动化相关能力
- `treatment.py`：风险处置流程
- `user_management.py`：用户管理
- `websocket.py`：实时推送

路由聚合文件：`app/api/v1/router.py`

特点：

- `/auth` 路由公开。
- 其余业务路由统一附加 `get_current_active_user` 依赖，默认要求用户已登录。
- 这意味着鉴权策略主要在 API 入口统一收口，而不是散落在业务代码各处。

### 3.4 业务服务层

核心目录：`app/services/`

职责：

- 承接接口层请求
- 编排数据库访问、Agent 调用、规则执行、通知和事务
- 将复杂流程从路由中剥离

关键服务如下。

#### `RiskService`

核心文件：`app/services/risk_service.py`

这是系统最关键的服务之一，负责完整的风险分析主流程：

1. 校验并读取原始数据
2. 使用 Redis 分布式锁避免重复分析
3. 解析载荷并准备 Agent 输入
4. 运行多 Agent 决策图
5. 持久化 `AnalysisResult`
6. 持久化 `DecisionResult`
7. 更新原始数据状态与质量分
8. 在高风险或人工审核场景写入通知 outbox
9. 提交事务并返回结果

它还做了几件很关键的事：

- 记录模型配置快照
- 记录规则版本快照
- 对 Prompt 文件做哈希
- 记录节点耗时和流程阶段耗时

这说明 `RiskService` 不只是“分析服务”，还是系统可追溯性的核心节点。

#### `DecisionService`

核心文件：`app/services/decision_service.py`

职责：

- 优先读取已有决策结果，避免重复推理
- 必要时重新触发 Agent 决策流程
- 生成决策追踪链路
- 返回待审核列表
- 提交人工审核结果
- 将审核动作记录为不可变审计事件

它是“决策结果生命周期管理器”，把自动决策与人工审核接起来。

#### 其他服务

- `auth_service.py`：认证、登录态、权限相关逻辑
- `rule_service.py`：规则树、版本与启停状态管理
- `settings_service.py`：模型与系统配置读写
- `notification_service.py`：通知组装与下发能力
- `automation_service.py`：自动化任务或 AI 辅助能力

### 3.5 基础设施层

核心目录：`app/core/`

职责：

- 统一承载所有跨业务共享的底层能力

重点模块：

- `config.py`：配置中心，使用 `pydantic-settings` 加载 `.env` 与环境变量
- `database.py`：数据库引擎、会话工厂
- `redis.py`：Redis 连接管理
- `mq.py`：RabbitMQ 连接管理
- `security.py`：JWT、认证依赖、权限控制
- `middleware.py`：请求日志、指标、TraceId 等中间件
- `logging_config.py`：结构化日志配置
- `metrics.py`：Prometheus 指标定义
- `health.py`：健康检查与依赖探测
- `request_guard.py`：请求防护，如速率限制或请求体限制
- `llm.py` / `model_selector.py`：模型接入与智能模型选择

其中 `config.py` 的重要性很高：

- 统一收口数据库、Redis、RabbitMQ、JWT、LLM、模型路由等配置
- 对生产环境做强校验
- 提供运行时覆盖的 LLM 配置能力

这意味着“模型配置来自哪里、何时生效、是否加密”都要从这里理解。

### 3.6 后端阅读顺序建议

推荐按以下顺序阅读：

1. `app/main.py`
2. `app/api/v1/router.py`
3. `app/services/risk_service.py`
4. `app/services/decision_service.py`
5. `app/core/config.py`
6. `app/rule_engine/rule_executor.py`
7. `app/agents/graphs/decision_graph.py`

---

## 4. 前端层

前端目录位于 `frontend/`，是面向业务操作和态势展示的 SPA 应用。

它的角色不是单纯展示列表，而是承担：

- 登录态管理
- 风险态势总览
- 原始数据录入与查询
- 分析结果查看
- 决策审批
- 规则管理
- 系统设置

### 4.1 前端总体结构

核心目录：

- `src/pages/`：页面级组件
- `src/components/`：可复用组件
- `src/services/`：接口请求封装
- `src/stores/`：全局状态管理
- `src/types/`：接口与业务类型定义
- `src/lib/` / `src/hooks/`：工具函数与自定义 Hook

### 4.2 应用入口与路由

核心文件：`frontend/src/App.tsx`

职责：

- 定义应用路由
- 统一接入 `ProtectedRoute`
- 使用 `Suspense + lazy` 懒加载页面
- 将登录页与业务页分开

当前主要路由包括：

- `/dashboard`
- `/raw-data`
- `/raw-data/:id`
- `/analysis`
- `/analysis/:id`
- `/decisions`
- `/decisions/:id`
- `/rules`
- `/rules/versions`
- `/settings/*`
- `/login`

说明：

- 路由设计与后端业务域基本一一对应，说明前后端模块边界较清晰。
- `ProtectedRoute` 说明前端不会只依赖本地缓存判断登录，而是将受保护页面统一收口。

### 4.3 页面层

核心目录：`frontend/src/pages/`

页面职责如下。

#### 仪表盘

核心文件：`frontend/src/pages/Dashboard.tsx`

职责：

- 聚合风险总量、重大风险、待审批决策、规则数等关键指标
- 展示近 30 天趋势
- 展示重大风险队列
- 提供从态势页进入核心操作页的快速入口

特点：

- 页面不是简单表格页，而是“风控态势总览页”
- 对部分接口失败有降级显示策略
- 强调“不可用就明确报错”，而不是用零值掩盖真实风险

#### 业务页面

- `RawData/*`：原始数据列表与详情
- `Analysis/*`：分析结果列表与详情
- `Decisions/*`：决策列表与审批页
- `Rules/*`：规则编辑与版本对比
- `Settings/*`：系统设置与用户管理
- `Login.tsx`：登录页
- `NotFound.tsx`：路由兜底页

这些页面基本覆盖了供应链风险流程的完整操作面。

### 4.4 组件层

核心目录：`frontend/src/components/`

按职责可分为：

- `ui/`：按钮、卡片、抽屉、表格、骨架屏、Toast 等基础组件
- `layout/`：`AppLayout`、`Header`、`Sidebar`
- `business/`：`AuditPanel`、`AutomationModal`、`NewAnalysisModal`、`RiskLevelBadge`、`TreatmentPanel`
- `auth/`：`ProtectedRoute`

说明：

- 基础 UI 组件和业务组件是分开的，便于后续复用和替换。
- `business/` 目录反映了前端已经进入业务语义组件阶段，而不是停留在通用后台模板阶段。

### 4.5 请求与状态管理

#### 请求层

核心文件：`frontend/src/services/api.ts`

职责：

- 创建 Axios 实例
- 统一设置 `withCredentials`
- 为每个请求维护全局进度条
- 对 `401` 自动触发 `/auth/refresh`
- 刷新失败后清理本地会话并跳转登录页

这说明当前前端认证模式是：

- 以 `HttpOnly Cookie` 为主
- 本地 `auth_user` 仅作为显示缓存
- 真正登录态仍以服务端会话为准

#### 状态层

核心目录：`frontend/src/stores/`

当前主要状态包括：

- `authStore.ts`：当前用户与登录状态
- `progressStore.ts`：顶部进度条
- `sidebarStore.ts`：侧边栏展开收起
- `toastStore.ts`：消息提示

其中 `authStore.ts` 的设计重点是：

- 清除历史 token 残留
- 本地缓存只保存用户展示信息
- 登录态必须由 Cookie 会话和接口校验确认

这比“仅靠 localStorage 判断登录”的做法更安全。

### 4.6 前端阅读顺序建议

推荐按以下顺序阅读：

1. `frontend/src/App.tsx`
2. `frontend/src/components/auth/ProtectedRoute.tsx`
3. `frontend/src/services/api.ts`
4. `frontend/src/stores/authStore.ts`
5. `frontend/src/pages/Dashboard.tsx`
6. 再按业务域阅读 `RawData / Analysis / Decisions / Rules / Settings`

---

## 5. 数据层

数据层既包含数据库实体，也包含 Repository、迁移脚本、缓存和消息队列模型，是系统状态持久化与异步通信的基础。

### 5.1 数据层组成

相关目录：

- `app/models/`：数据库实体模型
- `app/repositories/`：数据访问封装
- `alembic/`：数据库迁移
- `deploy/mysql/`：数据库初始化脚本
- `app/core/database.py`：数据库连接
- `app/core/redis.py`：缓存连接
- `app/core/mq.py`：消息队列连接

### 5.2 核心实体模型

#### `RawData`

核心文件：`app/models/raw_data.py`

职责：

- 表示系统入口数据
- 记录数据来源类型、来源 ID、原始载荷、哈希、处理状态和质量分

关键字段：

- `source_type`
- `source_id`
- `payload`
- `data_hash`
- `status`
- `quality_score`
- `processed_at`

系统通过它承接外部供应链数据，是后续分析流程的起点。

#### `AnalysisResult`

职责：

- 保存风险分析结果
- 记录风险分、风险等级、异常标签、推理说明与事实摘要

它是“分析层产物”的持久化载体。

#### `DecisionResult`

职责：

- 保存最终决策
- 记录决策动作、置信度、解释、决策路径、审核人、案件状态、到期时间、处置结果等

它是“决策层产物”的持久化载体，也是人工审核的主对象。

#### `RuleNode` 与 `RuleVersion`

职责：

- 存储规则树结构与规则版本快照
- 支撑规则管理、回溯与变更对比

#### `AgentExecutionLog`

职责：

- 记录每个 Agent 节点执行日志
- 记录节点名、耗时、模型、Token 用量和错误信息

这是决策链路追踪的基础数据源。

#### `AuditEvent`

职责：

- 记录人工审核、覆盖等重要动作
- 保留前后状态对比与评论

它承担“不可变审计”职责。

#### `NotificationOutbox`

职责：

- 作为高风险告警的持久化消息出口
- 将通知发送与主事务解耦

这说明通知不是直接在请求内同步完成，而是采用 outbox 模式增强可靠性。

### 5.3 Repository 层

核心目录：`app/repositories/`

职责：

- 为 Service 层提供统一的数据访问接口
- 隔离复杂查询细节
- 避免把 ORM 查询散落在业务服务中

主要仓库包括：

- `raw_data_repo.py`
- `analysis_repo.py`
- `decision_repo.py`
- `rule_repo.py`
- `agent_log_repo.py`
- `user_repo.py`

说明：

- 当前代码风格是“Service 编排业务，Repository 封装数据访问”，分层较清晰。
- Service 层仍保留了少量直接查询，这通常出现在流程编排需要复杂控制的地方。

### 5.4 迁移与部署

核心目录：`alembic/` 与 `deploy/`

特点：

- Alembic 维护数据库模式演进
- 已存在多条迁移脚本，说明系统已经历结构变更与生产能力增强
- `deploy/k8s/` 与 `docker-compose.yml` 表明系统兼容本地和生产部署

当前源码显示实际数据库是 `MySQL`，这一点比部分旧文档更可信。

### 5.5 数据层阅读顺序建议

推荐按以下顺序阅读：

1. `app/models/raw_data.py`
2. `app/models/analysis_result.py`
3. `app/models/decision_result.py`
4. `app/models/agent_execution_log.py`
5. `app/models/audit_event.py`
6. `app/repositories/*.py`
7. `alembic/versions/*.py`

---

## 6. Agent 层

Agent 层是本系统区别于传统风控后台的关键，也是“智能决策系统”能力最集中的部分。

它的职责不是单次调用某个模型接口，而是：

- 组织多角色 Agent 分工
- 在节点之间传递共享状态
- 根据风险程度和执行结果动态路由
- 记录执行日志、耗时与指标
- 在必要时转入人工审核

### 6.1 Agent 层目录结构

核心目录：`app/agents/`

包含：

- `graphs/`：LangGraph 图定义
- `nodes/`：各个 Agent 节点
- `prompts/`：Prompt 模板
- `tools/`：Agent 可调用工具
- `state.py`：共享状态定义
- `prompt_loader.py`：Prompt 加载工具

### 6.2 Agent 共享状态

核心文件：`app/agents/state.py`

职责：

- 定义 LangGraph 中各节点共享的状态结构
- 约定请求标识、数据质量、风险评分、决策结果、反思结果和流程状态等字段

核心状态字段包括：

- 请求标识：`request_id`、`raw_data_id`
- 数据理解：`structured_facts`、`data_quality_score`、`data_issues`
- 分析结果：`risk_score`、`risk_level`、`anomaly_tags`、`analysis_reasoning`
- 决策结果：`decision_result`、`confidence`、`decision_explanation`、`decision_path`
- 质量控制：`reflection_result`
- 流程控制：`status`、`retry_count`、`error_message`

这意味着 Agent 之间不是靠自由文本随意协作，而是通过结构化状态通信。

### 6.3 决策图

核心文件：`app/agents/graphs/decision_graph.py`

当前图的主路径为：

`scout -> analyst -> reflection/decider -> human_review/end`

各阶段职责：

- `scout`：抽取事实、做数据质量检查
- `analyst`：给出风险评分、风险等级、异常标签和分析说明
- `reflection`：对高风险分析结果进行二次审视
- `decider`：输出决策动作、解释与路径
- `human_review`：在失败、质量差、反思不通过等场景下进入人工介入

这个图的关键特征：

- 每个节点都有耗时统计
- 会异步写入 `AgentExecutionLog`
- 根据质量分、重试次数、风险等级、反思结果动态路由
- 产出会同步更新 Prometheus 指标

因此它不是简单的“串行调用 3 次模型”，而是一条可观测、可路由、可人工兜底的图流程。

### 6.4 Agent 节点层

核心目录：`app/agents/nodes/`

主要节点：

- `scout_node.py`
- `analyst_node.py`
- `reflection_node.py`
- `decider_node.py`
- `human_review_node.py`

按角色理解：

- Scout 更像“侦察和数据清洗”
- Analyst 更像“风险分析师”
- Reflection 更像“质量复核员”
- Decider 更像“决策官”
- Human Review 更像“人工兜底节点”

这种角色拆分使 Prompt、工具和输出结构更容易独立演进。

### 6.5 Prompt 与工具

核心目录：

- `app/agents/prompts/`
- `app/agents/tools/`

作用：

- Prompt 文件把角色指令外置化，便于版本管理与更新
- 工具模块把规则、风险与数据访问能力封装给 Agent 使用

`RiskService` 会对 Prompt 文件计算哈希并记录到结果中，这一点非常重要，因为它让“这次分析到底使用了哪个 Prompt 版本”变得可追溯。

### 6.6 Agent 层阅读顺序建议

推荐按以下顺序阅读：

1. `app/agents/state.py`
2. `app/agents/graphs/decision_graph.py`
3. `app/agents/nodes/scout_node.py`
4. `app/agents/nodes/analyst_node.py`
5. `app/agents/nodes/reflection_node.py`
6. `app/agents/nodes/decider_node.py`
7. `app/agents/nodes/human_review_node.py`
8. `app/agents/prompts/*.yaml`
9. `app/agents/tools/*.py`

---

## 7. 跨层调用关系

为了更好地理解系统，可以把四层之间的关系概括为：

### 7.1 请求进入系统时

`前端页面 -> 前端 services -> 后端 api -> 后端 services -> repositories / agents / rule_engine / core -> models / db / redis / mq`

### 7.2 风险分析主链路

1. 前端在分析页或原始数据页发起分析请求
2. 后端 `risk.py` 接收请求
3. `RiskService` 读取 `RawData`
4. `RiskService` 触发 `decision_graph`
5. Agent 图写回分析、决策、日志等结果
6. 高风险结果写入 `NotificationOutbox`
7. 前端查询分析结果并展示

### 7.3 决策与人工审核链路

1. 前端打开决策列表或审批页
2. 后端 `decision.py` 读取 `DecisionResult`
3. `DecisionService` 聚合 Agent 日志构建 trace
4. 审批动作写入 `AuditEvent`
5. 风险处置状态继续由相关接口推进

---

## 8. 源码与旧文档差异

基于当前扫描，建议特别注意以下差异：

- 旧技术架构文档提到 `PostgreSQL`，但当前源码、配置、部署清单与依赖都指向 `MySQL`。
- 前端技术文档中的部分组件目录与当前实际目录不完全一致，源码已进行过演化。
- 当前认证方式已演进为以 Cookie 会话为主，而不是单纯依赖前端 token。
- 当前系统已经具备 outbox、审计事件、设置加密等生产基础能力，强于早期设计稿。

结论：

- 阅读设计文档时应把它视为“架构意图参考”。
- 做实现判断、排错、扩展开发时应以源码为准。

---

## 9. 新成员上手建议

如果是第一次接手本项目，建议按下面顺序建立认知：

1. 阅读 `README.md`，了解业务背景和整体流程
2. 阅读 `app/main.py`，理解应用如何启动
3. 阅读 `app/api/v1/router.py`，理解后端业务域划分
4. 阅读 `app/services/risk_service.py`，掌握核心主流程
5. 阅读 `app/agents/graphs/decision_graph.py` 与 `app/agents/state.py`
6. 阅读 `app/rule_engine/rule_executor.py`
7. 阅读 `frontend/src/App.tsx` 与 `frontend/src/services/api.ts`
8. 按页面域阅读前端 `Dashboard -> Analysis -> Decisions -> Rules`
9. 最后阅读 `models / repositories / alembic` 完整理解数据持久化

---

## 10. 总结

从当前源码看，项目已经形成清晰的四层结构：

- 后端层：负责接口、鉴权、业务编排、基础设施与运维能力
- 前端层：负责业务操作界面、态势展示、审批与配置管理
- 数据层：负责实体建模、持久化、迁移、缓存和消息队列
- Agent 层：负责多角色智能分析、决策路由、可观测性与人工兜底

其中最值得优先理解的关键模块是：

- `app/services/risk_service.py`
- `app/services/decision_service.py`
- `app/agents/graphs/decision_graph.py`
- `app/rule_engine/rule_executor.py`
- `app/core/config.py`
- `frontend/src/services/api.ts`
- `frontend/src/App.tsx`

如果后续要继续扩展本项目，建议优先保持以下边界稳定：

- API 层只负责协议，不承担复杂业务
- Service 层继续承担流程编排中心
- Agent 层保持角色化与状态结构化
- 数据层继续通过 Repository 与业务解耦
- 前端页面继续按业务域拆分，而不是堆积到公共组件中
