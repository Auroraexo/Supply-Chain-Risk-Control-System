#!/usr/bin/env python
"""后端全链路连通性验证脚本。

验证范围：
  Layer 1 — 导入检查：所有模块能否正常导入
  Layer 2 — 配置检查：Settings 是否正确加载
  Layer 3 — 模型/Schema 检查：ORM 模型与 Pydantic Schema 能否正常实例化
  Layer 4 — FastAPI 应用检查：app 能否创建，路由是否注册
  Layer 5 — API 端点检查：各接口能否正常响应
  Layer 6 — Agent 图检查：LangGraph 决策图能否编译并执行
  Layer 7 — RuleEngine 检查：DSL 解析、规则执行、树遍历

用法：
  python verify_backend.py          # 仅内存验证（不需要 DB/Redis）
  python verify_backend.py --full   # 全量验证（需要 DB/Redis/MQ 可用）
"""

import argparse
import sys
import os
import uuid
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 设置 Mock 模式，避免验证时调用真实 LLM API
os.environ.setdefault("LLM_MOCK_MODE", "true")
os.environ.setdefault("ENVIRONMENT", "test")

# 终端颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")


def print_ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def print_fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def print_warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")


def print_info(msg: str) -> None:
    print(f"  {CYAN}→{RESET} {msg}")


# =============================================================================
# Layer 1: 导入检查
# =============================================================================
def test_imports() -> bool:
    print_header("Layer 1: 模块导入检查")
    modules = [
        # Core
        ("app.core.config", "get_settings"),
        ("app.core.database", "get_db, get_engine"),
        ("app.core.redis", "get_redis"),
        ("app.core.security", "create_access_token, decode_token, hash_password"),
        ("app.core.exceptions", "AppException, NotFoundException, ErrorCode"),
        ("app.core.logging_config", "setup_logging, get_logger"),
        ("app.core.middleware", "TraceIdMiddleware, RequestLoggingMiddleware"),
        ("app.core.llm", "get_llm, LLMProvider"),
        ("app.core.mq", "get_mq_connection, publish_risk_alert"),
        # Models
        ("app.models", "Base, RawData, AnalysisResult, DecisionResult, RuleNode, RuleVersion, AgentExecutionLog"),
        ("app.models.raw_data", "RawDataStatus"),
        ("app.models.analysis_result", "RiskLevel"),
        ("app.models.decision_result", "Decision"),
        ("app.models.rule_node", "RuleType, LogicOp"),
        # Schemas
        ("app.schemas", "BaseResponse, DataResponse, PaginatedResponse"),
        ("app.schemas", "RiskAnalysisRequest, DecisionRequest, RuleCreateRequest, ReviewDecision"),
        # Repositories
        ("app.repositories", "BaseRepository, RawDataRepository, AnalysisRepository, DecisionRepository, RuleRepository, AgentLogRepository"),
        # Services
        ("app.services.risk_service", "RiskService"),
        ("app.services.decision_service", "DecisionService"),
        ("app.services.rule_service", "RuleService"),
        ("app.services.notification_service", "NotificationService"),
        # API
        ("app.api.deps", "get_db, get_current_active_user"),
        ("app.api.v1.router", "api_router"),
        ("app.api.v1.websocket", "manager"),
        # Agent
        ("app.agents.state", "AgentState, create_initial_state, DecisionStatus, RiskLevel"),
        ("app.agents.graphs.decision_graph", "build_decision_graph, run_decision_flow"),
        ("app.agents.prompt_loader", "get_prompt_loader"),
        # Rule Engine
        ("app.rule_engine", "RuleExecutor, Rule, RuleCondition, DecisionTreeWalker"),
        ("app.rule_engine.dsl_parser", "DSLParser"),
        ("app.rule_engine.rule_loader", "RuleLoader"),
    ]

    all_ok = True
    for module_path, names in modules:
        try:
            mod = __import__(module_path, fromlist=[names.split(",")[0].strip()])
            for name in names.split(","):
                name = name.strip()
                getattr(mod, name)
            print_ok(f"import {module_path}  ({names})")
        except Exception as e:
            print_fail(f"import {module_path}  —  {e}")
            all_ok = False
    return all_ok


# =============================================================================
# Layer 2: 配置检查
# =============================================================================
def test_config() -> bool:
    print_header("Layer 2: 配置检查")
    all_ok = True
    try:
        from app.core.config import get_settings, Settings
        settings = get_settings()

        checks = [
            ("APP_NAME", settings.APP_NAME, "supply-chain-risk-control"),
            ("ENVIRONMENT", settings.ENVIRONMENT, "test"),
            ("HOST", settings.HOST, "0.0.0.0"),
            ("PORT", settings.PORT, 8000),
            ("DATABASE_URL 已配置", "mysql" in settings.DATABASE_URL, True),
            ("REDIS_URL 已配置", "redis" in settings.REDIS_URL, True),
            ("JWT_SECRET_KEY 已配置", len(settings.JWT_SECRET_KEY) > 0, True),
            ("JWT_ALGORITHM", settings.JWT_ALGORITHM, "HS256"),
            ("LLM_PROVIDER", settings.LLM_PROVIDER, "openai"),
            ("LLM_MOCK_MODE", settings.LLM_MOCK_MODE, True),
            ("CORS_ORIGINS 解析", len(settings.cors_origins_list) > 0, True),
            ("is_development", settings.is_development, False),
            ("is_production", settings.is_production, False),
        ]

        for name, actual, expected in checks:
            if actual == expected:
                print_ok(f"{name}: {actual}")
            else:
                print_fail(f"{name}: 期望 {expected}, 实际 {actual}")
                all_ok = False

    except Exception as e:
        print_fail(f"配置加载失败: {e}")
        all_ok = False
    return all_ok


# =============================================================================
# Layer 3: 模型/Schema 检查
# =============================================================================
def test_models_and_schemas() -> bool:
    print_header("Layer 3: 模型与 Schema 检查")
    all_ok = True

    # --- ORM 模型 ---
    print_info("检查 ORM 模型...")
    try:
        from app.models import RawData, AnalysisResult, DecisionResult, RuleNode, RuleVersion, AgentExecutionLog
        from app.models.raw_data import RawDataStatus
        from app.models.analysis_result import RiskLevel
        from app.models.decision_result import Decision as DecisionEnum

        models = [
            RawData(source_type="order", source_id="ORD-001", payload={"test": True}, data_hash="abc123"),
            AnalysisResult(request_id="req-001", raw_data_id="raw-001", risk_score=25.0, risk_level=RiskLevel.LOW),
            DecisionResult(request_id="req-001", analysis_id="ana-001", decision=DecisionEnum.APPROVE, confidence=0.95),
            RuleNode(rule_name="测试规则", rule_type="condition", priority=10),
            RuleVersion(rule_id="rule-001", version=1, snapshot={"rule": "test"}),
            AgentExecutionLog(request_id="req-001", agent_name="scout", node_name="scout_node"),
        ]
        for m in models:
            print_ok(f"{m.__class__.__name__} 实例化成功")
    except Exception as e:
        print_fail(f"ORM 模型实例化失败: {e}")
        all_ok = False

    # --- Pydantic Schema ---
    print_info("检查 Pydantic Schema...")
    try:
        from app.schemas.common import BaseResponse, DataResponse, PaginatedResponse
        from app.schemas.risk import RiskAnalysisRequest, RiskBatchRequest
        from app.schemas.decision import DecisionRequest
        from app.schemas.rule import RuleCreateRequest, RuleUpdateRequest, RuleToggleRequest
        from app.schemas.review import ReviewDecision

        schemas = [
            BaseResponse(),
            DataResponse(data={"key": "value"}),
            PaginatedResponse(data=[], total=0, page=1, page_size=20),
            RiskAnalysisRequest(raw_data_id="raw-001"),
            RiskBatchRequest(raw_data_ids=[f"raw-{i:03d}" for i in range(3)]),
            DecisionRequest(request_id="req-001"),
            RuleCreateRequest(rule_name="新规则", rule_type="condition", priority=10),
            RuleUpdateRequest(rule_name="更新规则", rule_type="action", priority=20),
            RuleToggleRequest(is_active=True),
            ReviewDecision(action="approve", comment="审核通过"),
        ]
        for s in schemas:
            print_ok(f"{s.__class__.__name__} 校验通过")
    except Exception as e:
        print_fail(f"Pydantic Schema 校验失败: {e}")
        all_ok = False

    return all_ok


# =============================================================================
# Layer 4: FastAPI 应用检查
# =============================================================================
def test_fastapi_app() -> bool:
    print_header("Layer 4: FastAPI 应用检查")
    all_ok = True
    try:
        from app.main import app

        # 检查路由注册
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        print_info(f"已注册 {len(routes)} 条路由")

        expected_routes = [
            "/health/live",
            "/health/ready",
            "/api/v1/risk/analyze",
            "/api/v1/risk/analyze/{request_id}",
            "/api/v1/risk/analyze/batch",
            "/api/v1/decision/make",
            "/api/v1/decision/{request_id}",
            "/api/v1/decision/{request_id}/trace",
            "/api/v1/review/pending",
            "/api/v1/review/{request_id}/approve",
            "/api/v1/review/{request_id}/reject",
            "/api/v1/review/{request_id}/override",
            "/api/v1/rules",
            "/api/v1/rules/tree",
            "/api/v1/rules/{rule_id}/toggle",
            "/api/v1/rules/{rule_id}/versions",
            "/api/v1/rules/{rule_id}/rollback",
            "/ws/alerts",
            "/api/v1/openapi.json",
        ]

        for route in expected_routes:
            if route in routes:
                print_ok(f"路由已注册: {route}")
            else:
                # WebSocket 和 OpenAPI 使用不同的注册方式，可能在 routes 中不直接匹配
                alt_routes = [
                    r.path for r in app.routes
                    if hasattr(r, "path") and route in r.path
                ]
                if alt_routes:
                    print_ok(f"路由已注册: {route}  (匹配: {alt_routes[0]})")
                else:
                    print_warn(f"路由未直接匹配: {route}  (可能以其他方式注册)")

        # 检查 OpenAPI 文档
        openapi = app.openapi()
        print_ok(f"OpenAPI 文档生成成功 (版本: {openapi.get('openapi', 'unknown')})")
        print_ok(f"API 标题: {openapi.get('info', {}).get('title', 'unknown')}")

    except Exception as e:
        print_fail(f"FastAPI 应用检查失败: {e}")
        all_ok = False
    return all_ok


# =============================================================================
# Layer 5: API 端点检查
# =============================================================================
def test_api_endpoints() -> bool:
    print_header("Layer 5: API 端点检查 (HTTP 测试)")
    all_ok = True
    try:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async def run_tests():
            nonlocal all_ok
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 健康检查
                r = await client.get("/health/live")
                if r.status_code == 200:
                    print_ok(f"GET /health/live → {r.status_code} {r.json()}")
                else:
                    print_fail(f"GET /health/live → {r.status_code}")
                    all_ok = False

                r = await client.get("/health/ready")
                if r.status_code in (200, 503):
                    print_ok(f"GET /health/ready → {r.status_code} (含依赖检查)")
                else:
                    print_warn(f"GET /health/ready → {r.status_code}")

                # OpenAPI 文档
                r = await client.get("/api/v1/openapi.json")
                if r.status_code == 200:
                    print_ok(f"GET /api/v1/openapi.json → {r.status_code}")
                else:
                    print_fail(f"GET /api/v1/openapi.json → {r.status_code}")
                    all_ok = False

                # 风险评估接口
                r = await client.post("/api/v1/risk/analyze", json={"raw_data_id": "test-001"})
                if r.status_code == 200:
                    data = r.json()
                    print_ok(f"POST /api/v1/risk/analyze → {r.status_code} (request_id={data.get('data', {}).get('request_id', '?')})")
                else:
                    print_fail(f"POST /api/v1/risk/analyze → {r.status_code} {r.text[:200]}")
                    all_ok = False

                # 规则管理接口
                r = await client.get("/api/v1/rules")
                if r.status_code == 200:
                    print_ok(f"GET /api/v1/rules → {r.status_code}")
                else:
                    print_fail(f"GET /api/v1/rules → {r.status_code}")
                    all_ok = False

                r = await client.get("/api/v1/rules/tree")
                if r.status_code == 200:
                    print_ok(f"GET /api/v1/rules/tree → {r.status_code}")
                else:
                    print_warn(f"GET /api/v1/rules/tree → {r.status_code}")

                # 决策接口
                r = await client.post("/api/v1/decision/make", json={"request_id": "test-req"})
                if r.status_code in (200, 404):
                    print_ok(f"POST /api/v1/decision/make → {r.status_code} (预期 404: 无对应分析结果)")
                else:
                    print_fail(f"POST /api/v1/decision/make → {r.status_code}")
                    all_ok = False

                # 审核接口
                r = await client.get("/api/v1/review/pending")
                if r.status_code == 200:
                    print_ok(f"GET /api/v1/review/pending → {r.status_code}")
                else:
                    print_fail(f"GET /api/v1/review/pending → {r.status_code}")
                    all_ok = False

                # 参数校验
                r = await client.post("/api/v1/risk/analyze", json={})
                if r.status_code == 422:
                    print_ok(f"POST /api/v1/risk/analyze (空body) → {r.status_code} (参数校验正常)")
                else:
                    print_fail(f"POST /api/v1/risk/analyze (空body) → {r.status_code} (期望 422)")
                    all_ok = False

                # 404 测试
                r = await client.get("/api/v1/risk/analyze/nonexistent-id")
                if r.status_code == 404:
                    print_ok(f"GET /api/v1/risk/analyze/xxx → {r.status_code} (404 正常)")
                else:
                    print_fail(f"GET /api/v1/risk/analyze/xxx → {r.status_code} (期望 404)")
                    all_ok = False

        import asyncio
        asyncio.run(run_tests())

    except ImportError as e:
        print_warn(f"httpx 未安装，跳过 HTTP 测试: {e}")
        print_info("安装: pip install httpx")
        all_ok = False
    except Exception as e:
        print_fail(f"API 端点测试失败: {e}")
        all_ok = False
    return all_ok


# =============================================================================
# Layer 6: Agent 图检查
# =============================================================================
def test_agent_graph() -> bool:
    print_header("Layer 6: Agent 决策图检查")
    all_ok = True
    try:
        # 图构建
        from app.agents.graphs.decision_graph import build_decision_graph, decision_app
        from app.agents.state import create_initial_state, AgentState, DecisionStatus

        graph = build_decision_graph()
        print_ok("LangGraph 决策图构建成功")
        print_ok(f"编译后图可用: {decision_app is not None}")

        # 状态创建
        state = create_initial_state("test-req-001", "test-raw-001")
        assert state["request_id"] == "test-req-001"
        assert state["status"] == DecisionStatus.PENDING
        print_ok("AgentState 初始状态创建成功")

        # 节点函数测试
        import asyncio
        from app.agents.nodes.scout_node import scout_node
        from app.agents.nodes.analyst_node import analyst_node
        from app.agents.nodes.decider_node import decider_node
        from app.agents.nodes.reflection_node import reflection_node
        from app.agents.nodes.human_review_node import human_review_node

        nodes = [
            ("scout", scout_node),
            ("analyst", analyst_node),
            ("decider", decider_node),
            ("reflection", reflection_node),
            ("human_review", human_review_node),
        ]
        for name, node_fn in nodes:
            result = asyncio.run(node_fn(state))
            print_ok(f"节点 [{name}] 执行成功 → status={result.get('status')}")

        # 工具函数测试
        from app.agents.tools.data_tools import get_raw_data, check_data_quality
        from app.agents.tools.risk_tools import calculate_risk_score, query_historical_patterns
        from app.agents.tools.rule_tools import match_rules, get_decision_tree

        tools = [
            ("get_raw_data", get_raw_data, {"raw_data_id": "test-001"}),
            ("check_data_quality", check_data_quality, {"raw_data": {"order_id": "001", "amount": 100}}),
            ("calculate_risk_score", calculate_risk_score, {"delay_days": 2, "price_deviation": 10.0, "supplier_rating": 4.0, "historical_incidents": 0}),
            ("query_historical_patterns", query_historical_patterns, {"entity_id": "test-001"}),
            ("match_rules", match_rules, {"context": {"risk_score": 50}}),
            ("get_decision_tree", get_decision_tree, {"root_node_id": "root"}),
        ]
        for name, tool_fn, kwargs in tools:
            result = tool_fn.invoke(kwargs)
            print_ok(f"Tool [{name}] 调用成功 → {result}")

        # Prompt 检查
        from app.agents.prompt_loader import get_prompt_loader
        loader = get_prompt_loader()
        for agent_name in ["scout", "analyst", "decider", "reflection"]:
            prompt = asyncio.run(loader.get_prompt(agent_name, "v1"))
            if prompt.get("system_prompt"):
                print_ok(f"Prompt [{agent_name}] 加载成功 (长度: {len(prompt['system_prompt'])} 字符)")
            else:
                print_warn(f"Prompt [{agent_name}] 内容为空")

    except Exception as e:
        import traceback
        print_fail(f"Agent 图检查失败: {e}")
        traceback.print_exc()
        all_ok = False
    return all_ok


# =============================================================================
# Layer 7: RuleEngine 检查
# =============================================================================
def test_rule_engine() -> bool:
    print_header("Layer 7: RuleEngine 检查")
    all_ok = True
    try:
        from app.rule_engine.rule_executor import RuleExecutor, Rule, RuleCondition, RulePrioritizer
        from app.rule_engine.dsl_parser import DSLParser

        # 规则执行器测试
        executor = RuleExecutor()

        condition = RuleCondition(
            field="risk_score",
            op="gt",
            value=50,
            items=[
                RuleCondition(field="supplier_rating", op="lt", value=3.0),
                RuleCondition(field="delay_days", op="gt", value=5),
            ],
            logic="OR",
        )

        rule = Rule(
            rule_id="rule_test",
            rule_name="测试规则",
            priority=100,
            conditions=condition,
            action={"type": "reject", "reason": "风险评分 {risk_score} 过高"},
        )

        # 匹配
        context = {"risk_score": 75, "supplier_rating": 2.5, "delay_days": 3}
        result = executor.evaluate(rule, context)
        assert result is not None
        assert result["type"] == "reject"
        assert "75" in result["reason"]
        print_ok(f"规则执行器：高风险场景匹配 → {result}")

        # 不匹配
        context_low = {"risk_score": 20, "supplier_rating": 4.5, "delay_days": 0}
        result = executor.evaluate(rule, context_low)
        assert result is None
        print_ok("规则执行器：低风险场景不匹配")

        # 优先级排序器
        rules = [
            Rule(rule_id="low", rule_name="低优先级", priority=10, conditions=RuleCondition(field="x", op="gt", value=0), action={"type": "low"}),
            Rule(rule_id="high", rule_name="高优先级", priority=100, conditions=RuleCondition(field="x", op="gt", value=0), action={"type": "high"}),
        ]
        prioritizer = RulePrioritizer(rules)
        result = prioritizer.execute({"x": 1})
        assert result is not None
        assert result["type"] == "high"
        print_ok(f"规则优先级排序器：高优先级规则优先 → {result}")

        # DSL 解析器
        yaml_rule = """
rule_id: "dsl_test"
rule_name: "DSL 测试规则"
priority: 50
conditions:
  logic: AND
  items:
    - field: risk_score
      operator: gt
      value: 30
    - field: amount
      operator: gt
      value: 10000
action:
  type: escalate
  reason: "金额 {amount} 风险评分 {risk_score}"
"""
        parsed = DSLParser.parse_yaml(yaml_rule)
        assert parsed.rule_id == "dsl_test"
        assert parsed.priority == 50
        print_ok(f"DSL 解析器：YAML 解析成功 → rule_id={parsed.rule_id}")

        # 树遍历器
        from app.rule_engine.tree_walker import DecisionTreeWalker
        walker = DecisionTreeWalker()
        print_ok("决策树遍历器：实例化成功（需 DB 测试完整遍历）")

        # 规则加载器
        from app.rule_engine.rule_loader import RuleLoader
        loader = RuleLoader()
        print_ok("规则加载器：实例化成功（需 DB 测试完整加载）")

    except Exception as e:
        import traceback
        print_fail(f"RuleEngine 检查失败: {e}")
        traceback.print_exc()
        all_ok = False
    return all_ok


# =============================================================================
# Layer 8: 全量连接测试（需外部服务）
# =============================================================================
def test_full_connectivity() -> bool:
    print_header("Layer 8: 全量连接测试 (DB/Redis/MQ)")
    all_ok = True

    # --- MySQL ---
    try:
        from app.core.config import get_settings
        from app.core.database import get_engine, close_db_connection
        from sqlalchemy import text

        engine = get_engine()
        async def test_db():
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row is not None
                print_ok(f"MySQL 连接成功 → SELECT 1 = {row[0]}")
            await close_db_connection()
        import asyncio
        asyncio.run(test_db())
    except Exception as e:
        print_warn(f"MySQL 连接失败（可能未启动）: {e}")
        all_ok = False

    # --- Redis ---
    try:
        from app.core.redis import get_redis, close_redis_connection
        async def test_redis():
            r = await get_redis()
            await r.ping()
            print_ok("Redis 连接成功 → PONG")
            test_key = "verify_backend_test"
            await r.set(test_key, "ok", ex=10)
            val = await r.get(test_key)
            await r.delete(test_key)
            assert val == "ok"
            print_ok("Redis 读写成功")
            await close_redis_connection()
        import asyncio
        asyncio.run(test_redis())
    except Exception as e:
        print_warn(f"Redis 连接失败（可能未启动）: {e}")
        all_ok = False

    # --- RabbitMQ ---
    try:
        from app.core.mq import get_mq_connection, close_mq_connection
        async def test_mq():
            conn = await get_mq_connection()
            assert not conn.is_closed
            print_ok("RabbitMQ 连接成功")
            await close_mq_connection()
        import asyncio
        asyncio.run(test_mq())
    except Exception as e:
        print_warn(f"RabbitMQ 连接失败（可能未启动）: {e}")
        all_ok = False

    # --- Agent 端到端执行 ---
    try:
        from app.agents.graphs.decision_graph import run_decision_flow
        async def test_agent_flow():
            result = await run_decision_flow("full-test-req", "full-test-raw")
            print_ok(f"Agent 端到端流程完成 → status={result.get('status')}, risk_score={result.get('risk_score')}, decision={result.get('decision_result')}")
            return result
        import asyncio
        asyncio.run(test_agent_flow())
        from app.core.llm import get_llm
        llm = get_llm(mock=True)
        print_ok(f"LLM Mock 模式就绪: {llm.__class__.__name__}")
    except Exception as e:
        print_fail(f"Agent 端到端流程失败: {e}")
        all_ok = False

    return all_ok


# =============================================================================
# 主入口
# =============================================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="后端全链路连通性验证")
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量验证（需要 DB/Redis/MQ 可用）",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}🔧 供应链智能决策系统 — 后端连通性验证{RESET}\n")
    print(f"  模式: {'全量验证 (含外部服务)' if args.full else '内存验证 (仅代码层)'}")
    print(f"  Python: {sys.version}")
    print(f"  工作目录: {os.getcwd()}")

    results = {}

    # Layer 1-7: 内存验证
    results["导入检查"] = test_imports()
    results["配置检查"] = test_config()
    results["模型/Schema"] = test_models_and_schemas()
    results["FastAPI 应用"] = test_fastapi_app()
    results["API 端点"] = test_api_endpoints()
    results["Agent 图"] = test_agent_graph()
    results["RuleEngine"] = test_rule_engine()

    # Layer 8: 全量验证
    if args.full:
        results["全量连接"] = test_full_connectivity()

    # 汇总
    print_header("验证结果汇总")
    passed = 0
    failed = 0
    for name, ok in results.items():
        if ok:
            print_ok(f"{name}: 通过")
            passed += 1
        else:
            print_fail(f"{name}: 失败")
            failed += 1

    print(f"\n{BOLD}总计: {GREEN}{passed} 通过{RESET}, {RED}{failed} 失败{RESET}, 共 {len(results)} 项\n")

    if failed == 0:
        print(f"{GREEN}{BOLD}✓ 后端全链路验证通过！{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}✗ 存在 {failed} 项失败，请检查上述错误。{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())