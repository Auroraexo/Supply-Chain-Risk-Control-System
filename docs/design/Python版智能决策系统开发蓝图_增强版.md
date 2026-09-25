# Python 版智能决策系统开发蓝图（增强版）

> **基于原文档 `Python版智能决策系统开发清单与多Agent架构设计(1).pdf` 的系统性完善**
> 
> 完善日期：2026-08-05
> 
> 完善说明：本文档在原始12块开发清单与多Agent架构设计基础上，补充了数据库Schema、项目目录结构、Agent实现细节、RuleEngine设计、评估体系、CI/CD流程等关键缺失内容，可直接作为项目开发执行蓝图使用。

---

## 目录

1. [第一部分：十二块开发清单（增强版）](#第一部分十二块开发清单增强版)
2. [第二部分：Java 到 Python 关键变更对照表（增强版）](#第二部分java-到-python-关键变更对照表增强版)
3. [第三部分：多 Agent 协同架构设计（增强版）](#第三部分多-agent-协同架构设计增强版)
4. [第四部分：补充设计——数据库 Schema 详细定义](#第四部分补充设计数据库-schema-详细定义)
5. [第五部分：补充设计——项目目录结构](#第五部分补充设计项目目录结构)
6. [第六部分：补充设计——RuleEngine DSL 设计](#第六部分补充设计ruleengine-dsl-设计)
7. [第七部分：补充设计——Agent 评估体系](#第七部分补充设计agent-评估体系)
8. [第八部分：补充设计——CI/CD 与开发工作流](#第八部分补充设计cicd-与开发工作流)
9. [第九部分：补充设计——LLM Provider 抽象层](#第九部分补充设计llm-provider-抽象层)
10. [第十部分：补充设计——API 接口清单](#第十部分补充设计api-接口清单)

---

## 第一部分：十二块开发清单（增强版）

### 第一块：环境准备（Python 适配）

- ☐ Python 3.12+（推荐 3.12，利用 `PEP 695` 类型参数语法、`PEP 701` f-string 改进）
- ☐ IDE：PyCharm Professional 或 VS Code (Python Extension + Pylance)
- ☐ 包管理：uv（推荐，极速依赖解析）或 Poetry
  - **补充**：根目录提交 `uv.lock` / `poetry.lock`，CI 中使用 `uv sync --frozen` 确保一致性
- ☐ Git & Docker Desktop
- ☐ 数据库：MySQL 8.0（字符集 utf8mb4，排序规则 utf8mb4_unicode_ci）、Redis 7
- ☐ API 调试：Postman 或 Bruno
- ☐ 虚拟环境：`.venv` 隔离，禁止全局安装依赖
- ☐ **补充**：pre-commit hooks 配置（ruff 格式化 + mypy 类型检查 + bandit 安全扫描）
- ☐ **补充**：环境变量管理：`.env.example` 模板文件，禁止提交 `.env`

### 第二块：数据库四张表（ORM 适配）—— 详见第四部分 Schema 定义

- ☐ 原始数据表 (raw_data)：存储供应链原始订单/物流数据
- ☐ 分析结果表 (analysis_results)：存储 Agent 分析中间结果
- ☐ 决策结果表 (decision_results)：存储最终决策与置信度
- ☐ 规则节点表 (rule_nodes)：存储决策树节点，支持递归父子关系
- ☐ **补充**：规则版本表 (rule_versions)：支持规则热更新与回滚
- ☐ **补充**：Agent 执行日志表 (agent_execution_logs)：记录每次 Agent 调用的输入输出与 Token 消耗

> 使用 SQLAlchemy 2.0 Async ORM 定义模型，配合 Alembic 做版本迁移。
> 
> 详见 [第四部分：数据库 Schema 详细定义](#第四部分补充设计数据库-schema-详细定义)

### 第三块：后端四层架构（Python 标准分层）—— 详见第五部分目录结构

- ☐ `api/` (Controller 层)：仅做参数校验(Pydantic)与响应组装，不含业务逻辑
- ☐ `services/` (Service 层)：核心业务规则、事务控制
- ☐ `agents/` (Agent 层)：LangGraph/LangChain 编排、Prompt 模板、工具函数
  - **补充**：`agents/prompts/` 存放 Prompt 模板（YAML/JSON），支持版本化与热更新
  - **补充**：`agents/tools/` 存放各 Agent 专用 Tool 函数
  - **补充**：`agents/graphs/` 存放 LangGraph 图定义
- ☐ `repositories/` (DAO 层)：封装所有 DB/Redis 操作，禁止 SQL 裸写
- ☐ `core/` (Common 包)：配置管理、异常定义、依赖注入、日志、安全中间件
  - **补充**：`core/config.py` 使用 pydantic-settings 管理多环境配置
  - **补充**：`core/di.py` 依赖注入容器（FastAPI Depends）
  - **补充**：`core/llm.py` LLM Provider 抽象层（详见第九部分）

### 第四块：八块基础代码（Python 等价实现）

- ☐ Pydantic Models：替代集合泛型，严格定义输入输出 Schema
  - **补充**：使用 `pydantic v2` 的 `model_validator` 做跨字段校验
  - **补充**：Response Model 统一包含 `trace_id`、`timestamp` 字段
- ☐ FastAPI Router：RESTful 接口定义，自动 OpenAPI 文档
  - **补充**：Router 按领域拆分（`api/v1/risk.py`, `api/v1/decision.py`），统一前缀 `/api/v1`
  - **补充**：CORS 中间件配置（白名单域名）
  - **补充**：请求限流中间件（`slowapi` 基于 Redis）
- ☐ Service 业务逻辑：异步函数 (async def)，依赖注入获取 Session
- ☐ SQLAlchemy Async Mapper：异步数据库访问层
  - **补充**：连接池配置（pool_size=20, max_overflow=40, pool_recycle=3600）
  - **补充**：Repository 基类封装 CRUD 通用操作
- ☐ Redis 缓存：redis.asyncio + 装饰器封装缓存策略
  - **补充**：缓存策略定义：Cache-Aside 模式，TTL 分级（热点数据 5min，规则数据 30min）
  - **补充**：缓存穿透保护（布隆过滤器或空值缓存）
- ☐ 全局异常处理：自定义 AppException + FastAPI Exception Handler
  - **补充**：异常码体系：`ERR_DB_001`（数据库异常）、`ERR_AGENT_001`（Agent 超时）等
  - **补充**：异常响应统一格式：`{"code": "ERR_XXX", "message": "...", "trace_id": "..."}`
- ☐ JWT 认证中间件：python-jose + Security Scheme 依赖
  - **补充**：Token 刷新机制（Refresh Token 存 Redis，Access Token 15min 过期）
- ☐ Loguru/Structlog 配置：结构化日志，替代 Logback，支持 JSON 输出
  - **建议选 Structlog**：原生支持 OpenTelemetry 集成，结构化日志更利于 ELK 检索

### 第五块：三个 Agent（LangGraph 状态机实现）—— 详见第三部分

- ☐ 侦察兵 Agent (Scout)：读取原始数据，调用 get_raw_data Tool，输出结构化事实
- ☐ 分析师 Agent (Analyst)：基于事实计算风险评分，支持 ReAct 推理循环
- ☐ 决策官 Agent (Decider)：递归遍历决策树（LangGraph Conditional Edge），综合打分并生成决策报告
- ☐ **补充**：协调器 (Orchestrator)：状态路由 + 重试 + 人机介入
- ☐ **补充**：自我反思 Agent (Self-Reflection)：高风险决策二次校验

> 使用 LangGraph 构建有向图，避免纯 Chain 的线性局限。详见第三部分多 Agent 架构设计。

### 第六块：业务层（异步消息队列）

- ☐ RuleEngine：Python 实现规则匹配引擎
  - **补充**：采用自研 DSL + 规则优先级队列，支持 AND/OR 逻辑组合
  - **补充**：规则热加载：从 DB 读取规则 → 内存缓存 → 变更通知刷新
  - 详见 [第六部分：RuleEngine DSL 设计](#第六部分补充设计ruleengine-dsl-设计)
- ☐ RabbitMQ 生产者：aio-pika 异步推送预警消息
  - **补充**：Exchange/Queue 拓扑设计：
    - Exchange: `risk_alert.topic`（topic 类型）
    - Queue: `risk_alert.high`（高优先级）、`risk_alert.normal`（普通优先级）
    - Routing Key: `risk.alert.{level}`（level: high/medium/low）
    - Dead Letter Queue: `risk_alert.dlq`（失败消息重试）
- ☐ 任务队列：推荐 **arq**（纯异步，基于 Redis，无 Celery 历史包袱）
  - **补充**：arq 配置：`max_jobs=100`, `job_timeout=600s`, `keep_result=3600s`

### 第七块：前端核心（补充技术选型与结构）

- ☐ **技术选型**：React 18 + TypeScript + Ant Design 5 / Vite
- ☐ 总览大屏：ECharts 雷达图 + 实时风险热力图
- ☐ 详情页：订单 + 物流数据展示
- ☐ 决策回溯页：展示 Agent 决策链路（LangGraph 状态图可视化）
- ☐ WebSocket：对接 FastAPI WebSocket Endpoint 接收实时预警
- ☐ **补充**：前后端 API 契约使用 OpenAPI 3.1 自动生成 TypeScript 类型（`openapi-typescript`）

> 后端提供 SSE/WebSocket 双协议支持流式 Agent 响应。

### 第八块：测试（Python 测试体系）—— 详见第七部分评估体系

- ☐ pytest + pytest-asyncio：每个 Agent 编写单元测试，Mock LLM 调用
- ☐ httpx.AsyncClient：集成测试，跑通完整链路
- ☐ Postman/Bruno：手动验收关键接口
- ☐ 覆盖率：pytest-cov 确保核心逻辑 >80%
- ☐ **补充**：Agent 评估测试（详见 [第七部分：Agent 评估体系](#第七部分补充设计agent-评估体系)）
- ☐ **补充**：性能测试：locust 压测关键 API（QPS > 100）

### 第九块：部署（容器化）

- ☐ Dockerfile：多阶段构建，slim 镜像，非 root 用户
  - **补充**：基础镜像 `python:3.12-slim`，构建阶段安装依赖，运行阶段仅复制 .venv
  - **补充**：健康检查指令 `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`
- ☐ docker-compose.yml：编排 App + MySQL 8.0 + Redis + RabbitMQ + Nginx
- ☐ Nginx 反向代理：HTTPS + WebSocket 升级头配置
  - **补充**：Nginx 限流配置（`limit_req_zone` + `limit_conn`）
- ☐ 备份脚本：mysqldump 全量 + binlog 增量备份，定时任务挂载
- ☐ **补充**：Kubernetes 部署清单（Deployment + Service + Ingress + ConfigMap）

### 第十块：安全（Python 专项）

- ☐ JWT 校验：密钥从环境变量读取，禁止硬编码
- ☐ SQL 注入防护：全程 ORM 参数化查询，禁止 f-string 拼接 SQL
- ☐ 敏感字段脱敏：Pydantic Field Serializer 自动脱敏
- ☐ 容器安全：非 root 运行 + 只读文件系统
- ☐ 依赖扫描：pip-audit 或 safety 检查开源组件漏洞
- ☐ **补充**：API 限流：slowapi + Redis 实现 IP/用户级别限流
- ☐ **补充**：请求体大小限制（FastAPI 默认 1MB，根据业务调整）
- ☐ **补充**：HTTP 安全头（HSTS, X-Content-Type-Options, X-Frame-Options）

### 第十一块：可观测性

- ☐ traceId 贯穿：OpenTelemetry SDK + FastAPI Middleware 自动注入
- ☐ 关键决策点日志：Agent 每一步推理/工具调用记录结构化日志
- ☐ Health Check：`/health` 端点检查 DB/Redis/MQ 连通性
  - **补充**：`/health/ready`（就绪探针）和 `/health/live`（存活探针）分离
- ☐ LangSmith/LangFuse：Agent 调用链追踪与评估（强烈推荐）
- ☐ **补充**：Prometheus Metrics：`/metrics` 端点暴露 QPS、延迟、错误率、Agent Token 消耗
- ☐ **补充**：告警规则：Agent 超时率 > 5%、决策置信度 < 0.6 触发告警

### 第十二块：报价和投标（人天重估）

- ☐ 报价清单：按 Python 全栈 + AI Agent 工程师费率重新核算
  - **补充**：建议人天分配（总计 45-50 人天）：
    | 阶段 | 人天 | 说明 |
    |------|------|------|
    | 环境搭建 + 基础架构 | 5 | 项目初始化、DB Schema、配置管理 |
    | 基础代码（API + Service + Repository） | 8 | 四层架构核心代码 |
    | Agent 开发（3 Agent + 协调器） | 12 | Prompt 调优 + LangGraph 编排 |
    | RuleEngine 开发 | 5 | DSL 设计 + 规则引擎实现 |
    | 前端开发 | 8 | 大屏 + 详情页 + 决策回溯 |
    | 测试 + 评估 | 5 | 单元测试 + Agent 评估 + 集成测试 |
    | 部署 + 文档 | 2 | Docker 化 + 部署文档 |
- ☐ 投标书技术部分：
  - 架构图更新为 FastAPI + LangGraph + MySQL 8.0
  - 甘特图增加"Agent Prompt 调优"与"评估集构建"阶段
  - 团队介绍突出 Python AI 工程化经验

---

## 第二部分：Java 到 Python 关键变更对照表（增强版）

| 原 Java 项 | Python 替代方案 | 增强说明 | 注意事项 |
|-----------|----------------|---------|---------|
| Spring Boot | FastAPI + Uvicorn | 使用 `uvicorn` 多 worker 模式（`--workers 4`） | 异步优先，注意事件循环阻塞 |
| MyBatis | SQLAlchemy 2.0 Async | 封装 Repository 基类简化 CRUD | 学习曲线较陡，务必用 async session |
| Spring Security | python-jose + FastAPI Depends | 手工实现 RBAC 权限矩阵 | 无声明式权限，需手写依赖 |
| Logback | Structlog | 配置 `structlog` + `python-json-logger` 输出 JSON | 配置更简单，但需手动对接 ELK |
| JUnit | pytest + pytest-asyncio | 使用 `pytest fixtures` 替代 `@Before/@After` | fixture 机制不同于 JUnit |
| Maven/Gradle | uv / Poetry | `uv.lock` / `poetry.lock` 必提交 | 锁定文件必提交 |
| LangChain4j | LangChain / LangGraph | LangGraph 0.2+ 推荐使用 `create_react_agent` | Python 版生态更全，但版本迭代快，锁版本 |
| MySQL | MySQL 8.0 | 使用 `aiomysql` 或 `asyncmy`（推荐，性能更优） | 字符集 utf8mb4 |
| RabbitMQ | aio-pika | 推荐 `aio-pika` 7.0+，支持连接池 | 注意 Channel 复用 |
| Spring Scheduler | APScheduler + arq | arq 用于异步任务，APScheduler 用于定时任务 | 定时任务与异步任务分离 |
| Hibernate Validator | Pydantic v2 | 使用 `Field(gt=0, le=100)` 等约束 | 校验逻辑集中在 Model 层 |

---

## 第三部分：多 Agent 协同架构设计（增强版）

### 1. 角色定义与能力边界（遵循最小依赖原则）

| Agent 角色 | 核心职责 | 输入 | 输出 | 对应 LangGraph 节点 | 超时 | 降级策略 |
|-----------|---------|------|------|-------------------|------|---------|
| 侦察兵 (Scout) | 数据采集与清洗 | 原始订单/物流 ID | 结构化事实 JSON | `scout_node` | 30s | 返回"数据不可用"标记 |
| 分析师 (Analyst) | 风险评分与异常检测 | 结构化事实 + 历史规则 | 风险分值 + 异常标签 | `analyst_node` | 60s | 返回默认中风险评分 |
| 决策官 (Decider) | 递归遍历决策树、综合裁决 | 风险分值 + 业务上下文 | 最终决策 + 置信度 + 解释 | `decider_node` | 60s | 返回"需人工审核" |
| 自我反思 (Self-Reflection) | 高风险决策二次校验 | 决策结果 + 原始事实 | 校验结果 + 修正建议 | `reflection_node` | 30s | 不阻塞，标记"未校验" |
| 协调器 (Orchestrator) | 状态路由、重试、人机介入 | 全局 State | 下一跳节点指令 | `router_edge` (条件边) | — | — |

**关键原则**：每个 Agent 只关注自身输入输出，不直接调用其他 Agent。所有交互通过 Shared State（共享状态）完成，避免循环依赖。

### 2. 增强版 LangGraph State 定义

```python
from typing import TypedDict, Annotated, Literal, Optional
from datetime import datetime
from enum import Enum
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DecisionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    HUMAN_REVIEW = "human_review"
    FAILED = "failed"

class AgentState(TypedDict):
    # === 请求标识 ===
    request_id: str                           # 请求唯一 ID（trace_id）
    raw_data_id: str                          # 原始数据 ID
    
    # === 侦察兵输出 ===
    structured_facts: Optional[dict]          # 结构化事实 {"order": {...}, "logistics": {...}}
    data_quality_score: Optional[float]       # 数据质量评分 (0-1)
    data_issues: Optional[list[str]]          # 数据问题列表
    
    # === 分析师输出 ===
    risk_score: Optional[float]               # 风险评分 (0-100)
    risk_level: Optional[RiskLevel]           # 风险等级
    anomaly_tags: Optional[list[str]]         # 异常标签 ["delay", "price_anomaly", ...]
    analysis_reasoning: Optional[str]         # 分析推理过程
    
    # === 决策官输出 ===
    decision_result: Optional[dict]           # 决策结果 {"action": "approve/reject/escalate", ...}
    confidence: Optional[float]               # 置信度 (0-1)
    decision_explanation: Optional[str]       # 决策解释
    decision_path: Optional[list[str]]        # 决策树路径 ["node_1", "node_3", "node_7"]
    
    # === 自我反思输出 ===
    reflection_result: Optional[dict]         # 反思结果 {"passed": bool, "suggestions": [...]}
    
    # === 流程控制 ===
    status: DecisionStatus                    # 当前状态
    retry_count: int                          # 重试次数
    error_message: Optional[str]              # 错误信息
    messages: Annotated[list[BaseMessage], add_messages]  # 对话历史
    
    # === 时间戳 ===
    created_at: str                           # 创建时间
    updated_at: str                           # 更新时间
    completed_at: Optional[str]               # 完成时间
```

### 3. 增强版条件路由（含自反思与人机介入）

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def should_continue(state: AgentState) -> str:
    """协调器：根据状态决定下一步"""
    # 1. 状态检查
    if state["status"] == DecisionStatus.FAILED:
        return "human_review"
    
    # 2. 数据采集阶段
    if state["structured_facts"] is None:
        if state["retry_count"] > 2:
            return "human_review"  # 数据不可用，转人工
        return "scout"
    
    # 3. 数据质量检查
    if state.get("data_quality_score", 0) < 0.5:
        return "human_review"  # 数据质量过低
    
    # 4. 风险分析阶段
    if state["risk_score"] is None:
        if state["retry_count"] > 3:
            return "human_review"  # 超限转人工
        return "analyst"
    
    # 5. 高风险决策需要自我反思
    if state["risk_level"] in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        if state.get("reflection_result") is None:
            return "reflection"  # 先自我反思
    
    # 6. 决策阶段
    if state["decision_result"] is None:
        return "decider"
    
    # 7. 完成
    return "complete"

def should_escalate(state: AgentState) -> str:
    """反思后的路由"""
    reflection = state.get("reflection_result", {})
    if not reflection.get("passed", True):
        return "human_review"  # 反思未通过，转人工
    return "decider"  # 反思通过，继续决策

# 构建增强版图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("scout", scout_agent)
workflow.add_node("analyst", analyst_agent)
workflow.add_node("decider", decider_agent)
workflow.add_node("reflection", reflection_agent)
workflow.add_node("human_review", human_review_handler)

# 设置入口
workflow.set_entry_point("scout")

# 条件边
workflow.add_conditional_edges(
    "scout",
    should_continue,
    {
        "analyst": "analyst",
        "human_review": "human_review",
        "scout": "scout",  # 重试
    }
)

workflow.add_conditional_edges(
    "analyst",
    should_continue,
    {
        "reflection": "reflection",
        "decider": "decider",
        "human_review": "human_review",
        "analyst": "analyst",  # 重试
    }
)

workflow.add_conditional_edges(
    "reflection",
    should_escalate,
    {
        "decider": "decider",
        "human_review": "human_review",
    }
)

workflow.add_conditional_edges(
    "decider",
    should_continue,
    {
        "complete": END,
        "human_review": "human_review",
        "decider": "decider",  # 重试
    }
)

workflow.add_edge("human_review", END)

# 编译（带持久化检查点）
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

### 4. Agent 实现骨架（以分析师 Agent 为例）

```python
# agents/tools/risk_analysis_tools.py
from langchain_core.tools import tool
from typing import Optional

@tool
def calculate_risk_score(
    delay_days: int,
    price_deviation: float,
    supplier_rating: float,
    historical_incidents: int
) -> dict:
    """计算供应链风险评分
    
    Args:
        delay_days: 延迟天数
        price_deviation: 价格偏差百分比
        supplier_rating: 供应商评分 (0-5)
        historical_incidents: 历史事故次数
    """
    score = (
        delay_days * 5.0 +
        price_deviation * 3.0 +
        (5 - supplier_rating) * 4.0 +
        historical_incidents * 10.0
    )
    score = min(score, 100.0)
    
    level = "low"
    if score > 70:
        level = "critical"
    elif score > 50:
        level = "high"
    elif score > 30:
        level = "medium"
    
    return {"score": round(score, 2), "level": level}

@tool
def query_historical_patterns(entity_id: str, pattern_type: str = "risk") -> dict:
    """查询历史风险模式"""
    # 实际实现：查询 DB 中的历史分析结果
    return {"patterns": [], "similarity_score": 0.0}

# agents/nodes/analyst_node.py
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from .prompts import ANALYST_SYSTEM_PROMPT

async def analyst_agent(state: AgentState) -> AgentState:
    """分析师 Agent：计算风险评分"""
    try:
        llm = get_llm(temperature=0.1)  # 低温度，追求一致性
        tools = [calculate_risk_score, query_historical_patterns]
        
        agent = create_react_agent(llm, tools)
        
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=ANALYST_SYSTEM_PROMPT),
                HumanMessage(content=f"""
                请分析以下结构化事实数据，计算风险评分：
                {state["structured_facts"]}
                
                请按以下步骤分析：
                1. 提取延迟天数、价格偏差、供应商评分、历史事故
                2. 调用 calculate_risk_score 工具计算评分
                3. 如需要，调用 query_historical_patterns 对比历史模式
                4. 输出风险等级、异常标签和分析推理
                """)
            ]
        })
        
        # 解析结果更新 State
        state["risk_score"] = result["risk_score"]
        state["risk_level"] = result["risk_level"]
        state["anomaly_tags"] = result["anomaly_tags"]
        state["analysis_reasoning"] = result["analysis_reasoning"]
        state["retry_count"] = 0  # 重置重试计数
        
    except Exception as e:
        state["retry_count"] += 1
        state["error_message"] = str(e)
        if state["retry_count"] > 3:
            state["status"] = DecisionStatus.FAILED
    
    state["updated_at"] = datetime.now().isoformat()
    return state
```

### 5. Prompt 模板管理（版本化）

```yaml
# agents/prompts/analyst_v1.yaml
version: "1.0.0"
agent: analyst
description: "供应链风险分析 Agent 系统提示词"
system_prompt: |
  你是一个供应链风险分析专家。你的任务是基于结构化事实数据，评估供应链风险。

  ## 分析维度
  1. **时效风险**：交付延迟天数、物流异常
  2. **价格风险**：价格偏差是否在合理范围（±15%）
  3. **供应商风险**：供应商历史评分、合作稳定性
  4. **合规风险**：是否符合贸易合规要求

  ## 输出要求
  - 必须调用 calculate_risk_score 工具获取数值评分
  - 风险等级：low (<30), medium (30-50), high (50-70), critical (>70)
  - 每个异常标签必须附带具体数值依据
  - 输出 JSON 格式的结果

  ## 注意事项
  - 如果数据缺失，明确标注"数据不足"
  - 不要编造数据，不确定时标注"置信度低"
  - 对于高风险案例，建议启用自我反思机制

# 使用方式：启动时从 DB/配置文件加载，支持热更新
# agents/prompt_loader.py
class PromptLoader:
    """Prompt 加载器，支持文件/DB 双源，热更新"""
    
    def __init__(self, source: str = "file"):
        self._cache = {}
        self._source = source
    
    async def get_prompt(self, agent_name: str, version: str = "latest") -> str:
        cache_key = f"{agent_name}:{version}"
        if cache_key not in self._cache:
            self._cache[cache_key] = await self._load_from_source(agent_name, version)
        return self._cache[cache_key]
    
    async def refresh(self):
        """热更新：清空缓存，下次请求时重新加载"""
        self._cache.clear()
```

### 6. Human-in-the-Loop 交互协议

```python
# 人机介入处理
async def human_review_handler(state: AgentState) -> AgentState:
    """人机介入节点：将决策挂起，等待人工审核"""
    # 1. 保存当前状态到 DB
    await save_review_task(state)
    
    # 2. 推送通知（WebSocket / 企业微信 / 邮件）
    await notify_reviewer({
        "request_id": state["request_id"],
        "risk_level": state["risk_level"],
        "reason": state.get("error_message") or "高风险决策需人工审核",
        "review_url": f"/review/{state['request_id']}"
    })
    
    # 3. 标记状态
    state["status"] = DecisionStatus.HUMAN_REVIEW
    state["updated_at"] = datetime.now().isoformat()
    
    return state

# 人工审核回调 API
@router.post("/api/v1/review/{request_id}/decision")
async def submit_review_decision(
    request_id: str,
    decision: HumanReviewDecision,
    db: AsyncSession = Depends(get_db)
):
    """人工提交审核结果，恢复 Agent 流程"""
    # 从 DB 恢复 State
    state = await load_state_from_db(request_id, db)
    
    # 合并人工决策
    state["decision_result"] = decision.result
    state["confidence"] = 1.0  # 人工决策置信度为 1
    state["status"] = DecisionStatus.COMPLETED
    
    # 持久化
    await save_state_to_db(state, db)
    
    return {"status": "ok", "request_id": request_id}
```

### 7. 避坑指南（2026 实战经验）—— 增强版

- **不要过度设计**：三个 Agent 足够时，不要强行拆成五个。复杂度应随业务增长渐进式增加。
- **State 要轻量**：不要在 State 中存大对象（如完整日志、图片）。只存 ID 或摘要，需要时通过 Tool 实时查询。
- **Prompt 版本化**：将 Prompt 模板从代码中剥离，存入 DB 或配置文件，支持热更新而不重启服务。
- **设置超时与熔断**：LLM 调用可能卡死。为每个 Agent 节点设置 timeout=30s，失败后走降级路径。
- **评估集先行**：在写 Agent 代码前，先准备 50+ 条标注好的"输入-期望输出"测试用例。没有评估集的 Agent 开发等于盲调。
- **新增：Token 成本控制**：每次 LLM 调用记录 Token 消耗，设置单次调用上限（如 4000 tokens），超出则截断
- **新增：并发控制**：使用 `asyncio.Semaphore(5)` 限制同时进行的 LLM 调用数，避免 API 限流
- **新增：幻觉缓解**：在 Prompt 中强调"不确定时标注不确定性"，对关键数据字段做后校验（如风险评分必须在 0-100 之间）
- **新增：模型版本锁定**：在配置文件中指定 LLM 模型版本（如 `gpt-4o-2024-08-06`），避免自动升级导致行为变化

---

## 第四部分：补充设计——数据库 Schema 详细定义

### 1. raw_data（原始数据表）

```sql
CREATE TABLE raw_data (
    id              VARCHAR(36) PRIMARY KEY,          -- UUID
    source_type     VARCHAR(50) NOT NULL,             -- 数据来源：order/logistics/invoice
    source_id       VARCHAR(100) NOT NULL,            -- 外部系统 ID
    payload         JSON NOT NULL,                    -- 原始数据 JSON
    data_hash       VARCHAR(64) NOT NULL,             -- SHA256 数据指纹（去重）
    status          ENUM('pending','processed','invalid') DEFAULT 'pending',
    quality_score   DECIMAL(3,2) DEFAULT NULL,        -- 数据质量评分 0-1
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at    DATETIME DEFAULT NULL,
    
    INDEX idx_source (source_type, source_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    UNIQUE KEY uk_hash (data_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2. analysis_results（分析结果表）

```sql
CREATE TABLE analysis_results (
    id              VARCHAR(36) PRIMARY KEY,
    request_id      VARCHAR(36) NOT NULL,             -- 关联的请求 ID
    raw_data_id     VARCHAR(36) NOT NULL,             -- 关联原始数据
    risk_score      DECIMAL(5,2) DEFAULT NULL,        -- 风险评分 0-100
    risk_level      ENUM('low','medium','high','critical') DEFAULT NULL,
    anomaly_tags    JSON DEFAULT NULL,                -- 异常标签 ["delay", "price_spike"]
    reasoning       TEXT DEFAULT NULL,                -- 分析推理过程
    facts_summary   JSON DEFAULT NULL,                -- 结构化事实摘要
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_request (request_id),
    INDEX idx_raw_data (raw_data_id),
    INDEX idx_risk_level (risk_level),
    FOREIGN KEY (raw_data_id) REFERENCES raw_data(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3. decision_results（决策结果表）

```sql
CREATE TABLE decision_results (
    id              VARCHAR(36) PRIMARY KEY,
    request_id      VARCHAR(36) NOT NULL,
    analysis_id     VARCHAR(36) NOT NULL,             -- 关联分析结果
    decision        ENUM('approve','reject','escalate','pending_review') NOT NULL,
    confidence      DECIMAL(3,2) DEFAULT NULL,        -- 置信度 0-1
    explanation     TEXT DEFAULT NULL,                 -- 决策解释
    decision_path   JSON DEFAULT NULL,                 -- 决策树路径 ["node_1","node_3"]
    reflection_passed BOOLEAN DEFAULT NULL,            -- 自我反思是否通过
    reviewed_by     VARCHAR(100) DEFAULT NULL,         -- 人工审核人（如有）
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_request (request_id),
    INDEX idx_analysis (analysis_id),
    INDEX idx_decision (decision),
    FOREIGN KEY (analysis_id) REFERENCES analysis_results(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4. rule_nodes（规则节点表）

```sql
CREATE TABLE rule_nodes (
    id              VARCHAR(36) PRIMARY KEY,
    parent_id       VARCHAR(36) DEFAULT NULL,         -- 父节点 ID（NULL 为根节点）
    rule_name       VARCHAR(200) NOT NULL,            -- 规则名称
    rule_type       ENUM('condition','action','group') NOT NULL,
    condition_type  VARCHAR(50) DEFAULT NULL,         -- 条件类型：threshold/range/match/expression
    field_name      VARCHAR(100) DEFAULT NULL,        -- 判断字段名 (risk_score, delay_days)
    operator        VARCHAR(20) DEFAULT NULL,         -- 运算符：gt/gte/lt/lte/eq/neq/in/contains
    threshold_value VARCHAR(200) DEFAULT NULL,        -- 阈值（支持 JSON 复杂值）
    logic_op        ENUM('AND','OR','NOT') DEFAULT 'AND', -- 与子节点的逻辑关系
    weight          DECIMAL(3,2) DEFAULT 1.0,         -- 权重（用于加权决策）
    action          VARCHAR(50) DEFAULT NULL,         -- 动作：approve/reject/escalate/notify
    action_params   JSON DEFAULT NULL,                -- 动作参数
    priority        INT DEFAULT 0,                    -- 优先级（越大越优先）
    is_active       BOOLEAN DEFAULT TRUE,             -- 是否启用
    version         INT DEFAULT 1,                    -- 版本号
    description     VARCHAR(500) DEFAULT NULL,        -- 规则描述
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_parent (parent_id),
    INDEX idx_active (is_active),
    INDEX idx_priority (priority),
    FOREIGN KEY (parent_id) REFERENCES rule_nodes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 5. rule_versions（规则版本表）

```sql
CREATE TABLE rule_versions (
    id              VARCHAR(36) PRIMARY KEY,
    rule_id         VARCHAR(36) NOT NULL,
    version         INT NOT NULL,
    snapshot        JSON NOT NULL,                    -- 该版本规则快照
    changed_by      VARCHAR(100) DEFAULT NULL,
    change_reason   VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_rule_version (rule_id, version),
    FOREIGN KEY (rule_id) REFERENCES rule_nodes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 6. agent_execution_logs（Agent 执行日志表）

```sql
CREATE TABLE agent_execution_logs (
    id              VARCHAR(36) PRIMARY KEY,
    request_id      VARCHAR(36) NOT NULL,
    agent_name      VARCHAR(50) NOT NULL,             -- scout/analyst/decider/reflection
    node_name       VARCHAR(50) NOT NULL,             -- 图节点名称
    input_state     JSON DEFAULT NULL,                -- 输入 State 摘要
    output_state    JSON DEFAULT NULL,                -- 输出 State 摘要
    llm_model       VARCHAR(100) DEFAULT NULL,        -- 使用的 LLM 模型
    prompt_tokens   INT DEFAULT 0,                    -- Prompt Token 数
    completion_tokens INT DEFAULT 0,                   -- 完成 Token 数
    latency_ms      INT DEFAULT NULL,                 -- 执行耗时（毫秒）
    error_message   TEXT DEFAULT NULL,                 -- 错误信息
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_request (request_id),
    INDEX idx_agent (agent_name),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 第五部分：补充设计——项目目录结构

```
supply-chain-risk-control/
├── .env.example                    # 环境变量模板
├── .gitignore
├── .pre-commit-config.yaml         # pre-commit hooks 配置
├── pyproject.toml                  # 项目配置（uv/poetry）
├── uv.lock                         # 依赖锁定文件
├── Dockerfile                      # 多阶段构建
├── docker-compose.yml              # 本地开发编排
├── alembic.ini                     # Alembic 配置
├── Makefile                        # 常用命令快捷方式
│
├── alembic/                        # 数据库迁移
│   ├── versions/
│   └── env.py
│
├── app/                            # 主应用目录
│   ├── __init__.py
│   ├── main.py                     # FastAPI 应用入口
│   │
│   ├── api/                        # Controller 层
│   │   ├── __init__.py
│   │   ├── deps.py                 # 公共依赖（get_db, get_current_user）
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # v1 路由汇总
│   │       ├── risk.py             # 风险评估接口
│   │       ├── decision.py         # 决策接口
│   │       ├── review.py           # 人工审核接口
│   │       ├── rule.py             # 规则管理接口
│   │       └── websocket.py        # WebSocket 实时推送
│   │
│   ├── services/                   # Service 层
│   │   ├── __init__.py
│   │   ├── risk_service.py         # 风险评估业务逻辑
│   │   ├── decision_service.py     # 决策业务逻辑
│   │   ├── rule_service.py         # 规则管理服务
│   │   └── notification_service.py # 通知服务
│   │
│   ├── agents/                     # Agent 层
│   │   ├── __init__.py
│   │   ├── graphs/                 # LangGraph 图定义
│   │   │   ├── __init__.py
│   │   │   ├── state.py            # AgentState 定义
│   │   │   ├── decision_graph.py   # 主决策图（含条件路由）
│   │   │   └── reflection_graph.py # 自我反思子图
│   │   ├── nodes/                  # 各 Agent 节点实现
│   │   │   ├── __init__.py
│   │   │   ├── scout_node.py
│   │   │   ├── analyst_node.py
│   │   │   ├── decider_node.py
│   │   │   ├── reflection_node.py
│   │   │   └── human_review_node.py
│   │   ├── tools/                  # Agent 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── data_tools.py       # 数据查询工具
│   │   │   ├── risk_tools.py       # 风险计算工具
│   │   │   ├── rule_tools.py       # 规则匹配工具
│   │   │   └── notification_tools.py # 通知推送工具
│   │   ├── prompts/                # Prompt 模板（版本化）
│   │   │   ├── scout_v1.yaml
│   │   │   ├── analyst_v1.yaml
│   │   │   ├── decider_v1.yaml
│   │   │   └── reflection_v1.yaml
│   │   └── prompt_loader.py        # Prompt 加载器（热更新）
│   │
│   ├── repositories/               # DAO 层
│   │   ├── __init__.py
│   │   ├── base.py                 # Repository 基类（CRUD 封装）
│   │   ├── raw_data_repo.py
│   │   ├── analysis_repo.py
│   │   ├── decision_repo.py
│   │   ├── rule_repo.py
│   │   └── agent_log_repo.py
│   │
│   ├── models/                     # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── base.py                 # 声明式基类
│   │   ├── raw_data.py
│   │   ├── analysis_result.py
│   │   ├── decision_result.py
│   │   ├── rule_node.py
│   │   ├── rule_version.py
│   │   └── agent_execution_log.py
│   │
│   ├── schemas/                    # Pydantic 请求/响应 Schema
│   │   ├── __init__.py
│   │   ├── common.py               # 公共响应格式
│   │   ├── risk.py                 # 风险评估请求/响应
│   │   ├── decision.py             # 决策请求/响应
│   │   ├── rule.py                 # 规则管理请求/响应
│   │   └── review.py               # 人工审核请求/响应
│   │
│   ├── core/                       # 核心基础设施
│   │   ├── __init__.py
│   │   ├── config.py               # pydantic-settings 配置管理
│   │   ├── security.py             # JWT 认证 + 权限
│   │   ├── exceptions.py           # 全局异常定义
│   │   ├── logging_config.py       # Structlog 配置
│   │   ├── database.py             # 数据库连接 + Session 工厂
│   │   ├── redis.py                # Redis 连接管理
│   │   ├── llm.py                  # LLM Provider 抽象层
│   │   ├── mq.py                   # RabbitMQ 连接管理
│   │   └── middleware.py           # 自定义中间件（traceId 等）
│   │
│   └── rule_engine/                # 规则引擎
│       ├── __init__.py
│       ├── dsl_parser.py           # DSL 解析器
│       ├── rule_executor.py        # 规则执行器
│       ├── tree_walker.py          # 决策树遍历器
│       └── rule_loader.py          # 规则加载器（DB → 内存）
│
├── tests/                          # 测试目录
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures
│   ├── unit/
│   │   ├── test_rule_engine.py
│   │   ├── test_services.py
│   │   └── test_repositories.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_agent_flow.py
│   ├── agent_eval/                 # Agent 评估测试
│   │   ├── eval_cases/
│   │   │   ├── case_001.json
│   │   │   ├── case_002.json
│   │   │   └── ...
│   │   ├── test_scout_eval.py
│   │   ├── test_analyst_eval.py
│   │   └── test_decider_eval.py
│   └── fixtures/                   # 测试数据
│       ├── sample_raw_data.json
│       └── sample_rules.sql
│
├── frontend/                       # 前端项目（React）
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/                    # API 调用封装
│   │   ├── pages/
│   │   │   ├── Dashboard/          # 总览大屏
│   │   │   ├── Detail/             # 详情页
│   │   │   ├── DecisionTrace/      # 决策回溯页
│   │   │   └── RuleManagement/     # 规则管理页
│   │   ├── components/             # 公共组件
│   │   ├── hooks/                  # 自定义 Hooks
│   │   └── types/                  # TypeScript 类型（OpenAPI 生成）
│   └── public/
│
├── deploy/                         # 部署配置
│   ├── nginx/
│   │   └── nginx.conf
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   └── configmap.yaml
│   └── scripts/
│       ├── backup.sh
│       └── healthcheck.sh
│
└── docs/                           # 文档
    ├── architecture.md             # 架构文档
    ├── api_spec.md                 # API 接口文档
    └── adr/                        # 架构决策记录
        ├── 001-use-fastapi.md
        ├── 002-use-langgraph.md
        └── 003-use-arq-over-celery.md
```

---

## 第六部分：补充设计——RuleEngine DSL 设计

### 1. DSL 设计原则

- **可读性优先**：规则配置应能让业务人员理解
- **JSON/YAML 格式**：便于存储和前端编辑
- **支持组合逻辑**：AND/OR/NOT 逻辑运算
- **支持优先级**：规则冲突时按优先级裁决

### 2. DSL 语法定义

```yaml
# 规则示例：高风险订单自动拒绝规则
rule_id: "rule_high_risk_reject"
rule_name: "高风险订单自动拒绝"
description: "当风险评分 > 70 且 供应商评级 < 3 时，自动拒绝订单"
version: 1
priority: 100
enabled: true

# 条件组合（AND 逻辑）
conditions:
  logic: AND
  items:
    - field: risk_score
      operator: gt              # greater than
      value: 70
    - field: supplier_rating
      operator: lt              # less than
      value: 3
    - field: order_amount
      operator: gt
      value: 100000
      unit: CNY

# 动作
action:
  type: reject
  reason: "高风险订单：评分 {risk_score}，供应商评级 {supplier_rating}"
  notify: ["risk_manager", "supply_chain_lead"]
```

```yaml
# 复杂规则示例：OR + AND 组合
rule_id: "rule_complex_escalation"
rule_name: "复杂决策升级规则"
conditions:
  logic: OR
  items:
    - logic: AND
      items:
        - field: risk_level
          operator: eq
          value: "critical"
        - field: order_amount
          operator: gt
          value: 500000
    - field: anomaly_tags
      operator: contains_any
      value: ["fraud_suspected", "sanctions_violation"]

action:
  type: escalate
  target: "executive_review"
  priority: "urgent"
```

### 3. 规则引擎核心实现

```python
# app/rule_engine/rule_executor.py
import operator
from typing import Any, Optional
from dataclasses import dataclass, field

@dataclass
class RuleCondition:
    field: str
    op: str
    value: Any
    logic: str = "AND"
    items: list["RuleCondition"] = field(default_factory=list)

@dataclass
class Rule:
    rule_id: str
    rule_name: str
    priority: int
    enabled: bool
    conditions: RuleCondition
    action: dict

class RuleExecutor:
    """规则执行器"""
    
    OPERATORS = {
        "gt": operator.gt,
        "gte": operator.ge,
        "lt": operator.lt,
        "lte": operator.le,
        "eq": operator.eq,
        "neq": operator.ne,
        "in": lambda a, b: a in b,
        "contains": lambda a, b: b in a,
        "contains_any": lambda a, b: any(x in a for x in b) if isinstance(a, list) else False,
    }
    
    def evaluate(self, rule: Rule, context: dict) -> Optional[dict]:
        """评估单条规则，返回 action 或 None"""
        if not rule.enabled:
            return None
        
        if self._evaluate_condition(rule.conditions, context):
            return self._interpolate_action(rule.action, context)
        return None
    
    def _evaluate_condition(self, condition: RuleCondition, context: dict) -> bool:
        """递归评估条件树"""
        if condition.items:
            results = [self._evaluate_condition(item, context) for item in condition.items]
            if condition.logic == "AND":
                return all(results)
            elif condition.logic == "OR":
                return any(results)
            elif condition.logic == "NOT":
                return not results[0]
        
        field_value = self._get_nested_field(context, condition.field)
        op_func = self.OPERATORS.get(condition.op)
        if op_func is None:
            raise ValueError(f"Unknown operator: {condition.op}")
        
        try:
            return op_func(field_value, condition.value)
        except (TypeError, ValueError):
            return False
    
    def _get_nested_field(self, context: dict, field_path: str) -> Any:
        """支持嵌套字段访问，如 'order.amount'"""
        keys = field_path.split(".")
        value = context
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _interpolate_action(self, action: dict, context: dict) -> dict:
        """模板变量替换"""
        import re
        result = action.copy()
        reason = action.get("reason", "")
        # 替换 {field_name} 模板变量
        for match in re.finditer(r"\{(\w+)\}", reason):
            var_name = match.group(1)
            value = self._get_nested_field(context, var_name)
            reason = reason.replace(match.group(0), str(value) if value is not None else "N/A")
        result["reason"] = reason
        return result


class RulePrioritizer:
    """规则优先级排序器：按优先级从高到低执行，首个匹配即返回"""
    
    def __init__(self, rules: list[Rule]):
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def execute(self, context: dict) -> Optional[dict]:
        executor = RuleExecutor()
        for rule in self._rules:
            result = executor.evaluate(rule, context)
            if result is not None:
                return result
        return None  # 无规则匹配
```

### 4. 决策树遍历器

```python
# app/rule_engine/tree_walker.py
class DecisionTreeWalker:
    """决策树遍历器：递归遍历 rule_nodes 表构建的决策树"""
    
    def __init__(self, rule_repo):
        self.rule_repo = rule_repo
    
    async def walk(self, root_node_id: str, context: dict) -> list[str]:
        """遍历决策树，返回决策路径"""
        path = []
        current_node = await self.rule_repo.get_by_id(root_node_id)
        
        while current_node:
            path.append(current_node.id)
            
            if current_node.rule_type == "action":
                # 叶子节点：执行动作
                context["decision_action"] = current_node.action
                break
            
            if current_node.rule_type == "condition":
                # 条件节点：评估条件，选择子节点
                matched = self._evaluate_node(current_node, context)
                children = await self.rule_repo.get_children(current_node.id)
                
                if current_node.logic_op == "AND":
                    current_node = children[0] if all(matched) else children[1] if len(children) > 1 else None
                elif current_node.logic_op == "OR":
                    current_node = children[0] if any(matched) else children[1] if len(children) > 1 else None
                else:
                    current_node = children[0] if matched else None
            
            elif current_node.rule_type == "group":
                # 分组节点：遍历所有子节点
                children = await self.rule_repo.get_children(current_node.id)
                results = [self._evaluate_node(child, context) for child in children]
                # 加权计算
                weighted_score = sum(
                    r * child.weight for r, child in zip(results, children)
                )
                context["weighted_score"] = weighted_score
                current_node = children[0] if children else None  # 继续遍历
        
        return path
```

---

## 第七部分：补充设计——Agent 评估体系

### 1. 评估维度

| 维度 | 指标 | 目标值 | 评估方法 |
|------|------|--------|---------|
| 准确性 | 风险等级准确率 | > 85% | 与人工标注对比 |
| 一致性 | 相同输入重复执行结果一致率 | > 90% | 温度=0 重复执行 |
| 鲁棒性 | 缺失数据场景下正确降级率 | > 80% | 故意删除部分字段 |
| 效率 | 端到端响应时间 (P95) | < 30s | 性能测试 |
| 安全性 | 幻觉率（编造数据比例） | < 5% | 人工抽检 |
| 可解释性 | 决策原因可理解率 | > 90% | 人工评估 |

### 2. 评估用例格式

```json
{
  "case_id": "eval_001",
  "description": "正常订单-低风险场景",
  "input": {
    "raw_data": {
      "order_id": "ORD-2024-001",
      "supplier_id": "SUP-088",
      "order_amount": 50000,
      "expected_delivery": "2024-03-15",
      "actual_delivery": "2024-03-14",
      "supplier_rating": 4.5,
      "historical_incidents": 0
    }
  },
  "expected_output": {
    "risk_level": "low",
    "risk_score_range": [0, 30],
    "decision": "approve",
    "must_have_tags": [],
    "must_not_have_tags": ["fraud_suspected"]
  }
}
```

### 3. 评估执行器

```python
# tests/agent_eval/evaluator.py
class AgentEvaluator:
    """Agent 评估器"""
    
    def __init__(self, eval_cases_path: str):
        self.cases = self._load_cases(eval_cases_path)
        self.results = []
    
    async def evaluate_scout(self, scout_agent) -> dict:
        """评估侦察兵 Agent"""
        passed = 0
        for case in self.cases:
            state = {"raw_data_id": case["input"]["raw_data"]["order_id"]}
            result_state = await scout_agent(state)
            
            # 检查结构化事实是否完整
            facts = result_state.get("structured_facts", {})
            expected_fields = case.get("expected_output", {}).get("must_have_fields", [])
            missing = [f for f in expected_fields if f not in facts]
            
            case_result = {
                "case_id": case["case_id"],
                "passed": len(missing) == 0,
                "missing_fields": missing,
                "data_quality": result_state.get("data_quality_score", 0)
            }
            self.results.append(case_result)
            if case_result["passed"]:
                passed += 1
        
        return {
            "total": len(self.cases),
            "passed": passed,
            "accuracy": passed / len(self.cases) if self.cases else 0,
            "details": self.results
        }
    
    async def evaluate_analyst(self, analyst_agent) -> dict:
        """评估分析师 Agent"""
        passed = 0
        for case in self.cases:
            state = {
                "structured_facts": case["input"]["raw_data"],
                "retry_count": 0
            }
            result_state = await analyst_agent(state)
            expected = case["expected_output"]
            
            # 检查风险等级
            level_match = result_state.get("risk_level") == expected["risk_level"]
            # 检查风险评分范围
            score = result_state.get("risk_score", -1)
            score_range = expected.get("risk_score_range", [0, 100])
            score_in_range = score_range[0] <= score <= score_range[1]
            # 检查异常标签
            tags = result_state.get("anomaly_tags", [])
            must_have = all(t in tags for t in expected.get("must_have_tags", []))
            must_not = all(t not in tags for t in expected.get("must_not_have_tags", []))
            
            passed_case = level_match and score_in_range and must_have and must_not
            self.results.append({
                "case_id": case["case_id"],
                "passed": passed_case,
                "level_match": level_match,
                "score_in_range": score_in_range,
                "actual_score": score,
                "expected_level": expected["risk_level"],
                "actual_level": result_state.get("risk_level")
            })
            if passed_case:
                passed += 1
        
        return {
            "total": len(self.cases),
            "passed": passed,
            "accuracy": passed / len(self.cases) if self.cases else 0,
            "details": self.results
        }
```

---

## 第八部分：补充设计——CI/CD 与开发工作流

### 1. 分支策略

```
main            ← 生产分支，仅通过 PR 合并
├── develop     ← 开发分支
│   ├── feature/xxx    ← 功能分支
│   ├── fix/xxx        ← 修复分支
│   └── agent/xxx      ← Agent 调优分支
└── release/x.x.x      ← 发布分支
```

### 2. CI/CD 流水线（GitHub Actions / GitLab CI）

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [develop, 'feature/**']
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run mypy app/
      - run: uv run bandit -r app/ -ll

  test:
    needs: lint
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test
          MYSQL_DATABASE: test_db
        ports: [3306]
      redis:
        image: redis:7
        ports: [6379]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - run: uv sync --frozen
      - run: uv run pytest tests/unit/ -v --cov=app --cov-report=xml
      - run: uv run pytest tests/integration/ -v
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  agent-eval:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - run: uv sync --frozen
      - run: uv run pytest tests/agent_eval/ -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt
```

### 3. pre-commit 配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, sqlalchemy]
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: [-ll]
```

---

## 第九部分：补充设计——LLM Provider 抽象层

```python
# app/core/llm.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"  # vLLM / Ollama 等本地模型

class LLMConfig:
    """LLM 配置，从环境变量/配置文件加载"""
    provider: LLMProvider
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 30
    max_retries: int = 2

def get_llm(
    provider: Optional[LLMProvider] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """获取 LLM 实例（工厂方法）
    
    支持多 Provider 切换，方便在开发/测试/生产环境使用不同模型。
    测试环境可注入 Mock LLM，避免真实 API 调用。
    """
    config = _load_llm_config(provider)
    
    if temperature is not None:
        config.temperature = temperature
    if max_tokens is not None:
        config.max_tokens = max_tokens
    
    if config.provider == LLMProvider.OPENAI:
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(
            model=config.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == LLMProvider.AZURE_OPENAI:
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == LLMProvider.LOCAL:
        return ChatOpenAI(
            model=config.model,
            api_key="not-needed",
            base_url=config.base_url or "http://localhost:8000/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
```

---

## 第十部分：补充设计——API 接口清单

### 1. 风险评估接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/risk/analyze` | 提交风险评估请求（异步） |
| GET | `/api/v1/risk/analyze/{request_id}` | 查询评估结果 |
| GET | `/api/v1/risk/analyze/{request_id}/stream` | SSE 流式获取评估过程 |

### 2. 决策接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/decision/make` | 提交决策请求 |
| GET | `/api/v1/decision/{request_id}` | 查询决策结果 |
| GET | `/api/v1/decision/{request_id}/trace` | 获取决策链路追踪 |

### 3. 人工审核接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/review/pending` | 获取待审核列表 |
| POST | `/api/v1/review/{request_id}/approve` | 审核通过 |
| POST | `/api/v1/review/{request_id}/reject` | 审核驳回 |
| POST | `/api/v1/review/{request_id}/override` | 人工覆盖决策 |

### 4. 规则管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/rules` | 获取规则列表 |
| POST | `/api/v1/rules` | 创建规则 |
| PUT | `/api/v1/rules/{rule_id}` | 更新规则 |
| DELETE | `/api/v1/rules/{rule_id}` | 删除规则（软删除） |
| POST | `/api/v1/rules/{rule_id}/toggle` | 启用/禁用规则 |
| GET | `/api/v1/rules/{rule_id}/versions` | 获取规则版本历史 |
| POST | `/api/v1/rules/{rule_id}/rollback` | 回滚到指定版本 |

### 5. 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针 |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/api/v1/docs` | OpenAPI 文档 |
| WS | `/ws/alerts` | 实时预警 WebSocket |

---

## 附录：架构决策记录 (ADR)

### ADR-001: 选择 FastAPI 而非 Django Ninja

**决策**：使用 FastAPI 作为 Web 框架

**理由**：
- FastAPI 生态更成熟，社区活跃度远超 Django Ninja
- 原生异步支持，与 LangGraph 异步调用天然契合
- 自动 OpenAPI 文档生成，减少前后端契约维护成本
- Pydantic v2 集成，类型安全贯穿全栈

### ADR-002: 选择 LangGraph 而非纯 LangChain

**决策**：使用 LangGraph 构建 Agent 工作流

**理由**：
- LangGraph 的有向图模型更适合多步骤决策流程
- 原生支持条件路由（Conditional Edge），符合决策树需求
- 内置持久化检查点（Checkpointer），支持状态恢复和人机介入
- 避免 LangChain 纯 Chain 的线性局限

### ADR-003: 选择 arq 而非 Celery

**决策**：使用 arq 作为异步任务队列

**理由**：
- 纯 Python 异步实现，无 Celery 的历史包袱
- 基于 Redis，无需额外部署 RabbitMQ 仅用于任务队列
- 更简单的配置和调试体验
- 适合中小规模任务（< 10000 tasks/day）

---

> **本文档整合了原始12块开发清单、Java到Python技术栈变更、多Agent协同架构设计，并补充了数据库Schema、项目目录结构、RuleEngine DSL、Agent评估体系、CI/CD流程、LLM Provider抽象层、API接口清单等关键缺失内容，可直接作为供应链智能决策系统的完整开发执行蓝图使用。**
>
> **数据库统一使用 MySQL 8.0，后端使用 Python 3.12 + FastAPI + LangGraph 技术栈。**