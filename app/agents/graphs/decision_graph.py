"""决策图定义。

使用 LangGraph 构建完整的 Agent 决策流程：
scout → analyst → (reflection) → decider → (human_review) → END
"""
import time
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.analyst_node import analyst_node
from app.agents.nodes.decider_node import decider_node
from app.agents.nodes.human_review_node import human_review_node
from app.agents.nodes.reflection_node import reflection_node
from app.agents.nodes.scout_node import scout_node
from app.agents.state import AgentState, DecisionStatus, RiskLevel
from app.core.metrics import (
    AGENT_CALLS_TOTAL,
    AGENT_LATENCY_SECONDS,
    DECISION_CONFIDENCE,
    DECISIONS_TOTAL,
)

logger = structlog.get_logger(__name__)


def _route_elapsed(state: AgentState) -> float:
    """计算路由判定时刻相对流程开始的耗时（毫秒），用于定位决策点时间线。"""
    start = state.get("_flow_start_mono")
    return round((time.monotonic() - start) * 1000, 1) if start else 0.0


def _persist_execution_log(request_id: str, node: str, state: dict, elapsed_ms: float, error: str | None) -> None:
    """把节点执行记录写入 agent_execution_logs（失败仅告警，不影响主流程）。

    独立会话写入：图执行中的会话会 rollback/expire，不能复用。
    """
    try:
        import asyncio

        from app.core.database import get_session_factory
        from app.models.agent_execution_log import AgentExecutionLog

        # token 用量：节点执行期间可能更新 state["token_usage"]
        usage = state.get("token_usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)

        # 摘要输出：取节点最有代表性的产物
        output_summary = (
            state.get("analysis_reasoning")
            or state.get("decision_explanation")
            or state.get("data_quality_notes")
            or state.get("human_review_reason")
            or ""
        )

        async def _write() -> None:
            factory = get_session_factory()
            async with factory() as session:
                session.add(AgentExecutionLog(
                    request_id=request_id,
                    agent_name=node,
                    node_name=node,
                    input_state=None,  # 原始状态含大量中间体，不入库
                    output_state={"summary": str(output_summary)[:2000]} if output_summary else None,
                    llm_model=str(state.get("_llm_model") or "") or None,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=int(elapsed_ms),
                    error_message=error,
                ))
                await session.commit()

        # 图运行在事件循环内，直接调度写入任务
        asyncio.get_running_loop().create_task(_write())
    except Exception as e:  # noqa: BLE001 - 日志埋点失败不影响决策主流程
        logger.warning("graph.execution_log_failed", node=node, error=str(e))


def _timed_node(name: str, node_fn):
    """节点计时包装：记录单节点耗时，写入执行日志，并累积到 state["node_timings"] 供流程结束汇总。"""
    async def wrapper(state):
        node_t0 = time.monotonic()
        request_id = str(state.get("request_id") or "unknown")
        logger.info("graph.node_start", node=name, request_id=request_id)
        try:
            result = await node_fn(state)
        except Exception as e:
            AGENT_CALLS_TOTAL.labels(
                agent_name=name, node_name=name, status="error"
            ).inc()
            elapsed_err = round((time.monotonic() - node_t0) * 1000, 1)
            _persist_execution_log(request_id, name, dict(state), elapsed_err, str(e))
            raise
        elapsed = round((time.monotonic() - node_t0) * 1000, 1)
        AGENT_LATENCY_SECONDS.labels(agent_name=name, node_name=name).observe(elapsed / 1000)
        AGENT_CALLS_TOTAL.labels(agent_name=name, node_name=name, status="success").inc()
        timings = list(result.get("node_timings") or [])
        timings.append({"node": name, "elapsed_ms": elapsed})
        result["node_timings"] = timings
        _persist_execution_log(request_id, name, dict(result), elapsed, None)
        logger.info(
            "graph.node_complete",
            node=name,
            request_id=request_id,
            elapsed_ms=elapsed,
            sequence=len(timings),
        )
        return result
    return wrapper


def should_continue_after_scout(state: AgentState) -> str:
    """侦察兵完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")
    quality = state.get("data_quality_score", 0)
    retry = state.get("retry_count", 0)

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="status_failed", elapsed_ms=_route_elapsed(state))
        return "human_review"
    if quality < 0.5:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="low_quality", quality_score=quality, elapsed_ms=_route_elapsed(state))
        return "human_review"
    if retry > 2:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="retry_exhausted", retry_count=retry, elapsed_ms=_route_elapsed(state))
        return "human_review"

    logger.info("graph.route.scout_to_analyst", request_id=request_id, quality_score=quality, elapsed_ms=_route_elapsed(state))
    return "analyst"


def should_continue_after_analyst(state: AgentState) -> str:
    """分析师完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")
    retry = state.get("retry_count", 0)
    risk_level = state.get("risk_level")

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.analyst_to_human_review", request_id=request_id, reason="status_failed", elapsed_ms=_route_elapsed(state))
        return "human_review"
    if retry > 3:
        logger.warning("graph.route.analyst_to_human_review", request_id=request_id, reason="retry_exhausted", retry_count=retry, elapsed_ms=_route_elapsed(state))
        return "human_review"
    if risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
        logger.info("graph.route.analyst_to_reflection", request_id=request_id, risk_level=risk_level, reason="high_risk", elapsed_ms=_route_elapsed(state))
        return "reflection"

    logger.info("graph.route.analyst_to_decider", request_id=request_id, risk_level=risk_level, elapsed_ms=_route_elapsed(state))
    return "decider"


def should_continue_after_reflection(state: AgentState) -> str:
    """反思完成后路由。"""
    request_id = state.get("request_id", "unknown")
    reflection = state.get("reflection_result") or {}
    passed = reflection.get("passed", True)

    if not passed:
        logger.warning("graph.route.reflection_to_human_review", request_id=request_id, suggestions=reflection.get("suggestions"), elapsed_ms=_route_elapsed(state))
        return "human_review"

    logger.info("graph.route.reflection_to_decider", request_id=request_id, elapsed_ms=_route_elapsed(state))
    return "decider"


def should_continue_after_decider(state: AgentState) -> str:
    """决策官完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.decider_to_human_review", request_id=request_id, reason="status_failed", elapsed_ms=_route_elapsed(state))
        return "human_review"

    logger.info(
        "graph.route.decider_to_end",
        request_id=request_id,
        decision=(state.get("decision_result") or {}).get("action"),
        elapsed_ms=_route_elapsed(state),
    )
    return "complete"


def should_continue_after_human_review(state: AgentState) -> str:
    """人机介入后路由。"""
    request_id = state.get("request_id", "unknown")
    logger.info("graph.route.human_review_to_end", request_id=request_id)
    return "complete"


def build_decision_graph() -> StateGraph:
    """构建决策图。"""
    t0 = time.monotonic()
    # langgraph 1.x 的类型存根（StateLike 不含 dict）与运行时不一致，
    # 但 dict schema 在运行时完全可用（已验证），故此处精准抑制类型告警。
    workflow = StateGraph(dict[str, Any])  # type: ignore[type-var]

    # 添加节点（_timed_node 包装：记录每个节点的执行耗时）
    workflow.add_node("scout", _timed_node("scout", scout_node))
    workflow.add_node("analyst", _timed_node("analyst", analyst_node))
    workflow.add_node("decider", _timed_node("decider", decider_node))
    workflow.add_node("reflection", _timed_node("reflection", reflection_node))
    workflow.add_node("human_review", _timed_node("human_review", human_review_node))

    # 设置入口
    workflow.set_entry_point("scout")

    # 条件边
    workflow.add_conditional_edges("scout", should_continue_after_scout, {
        "analyst": "analyst",
        "human_review": "human_review",
    })
    workflow.add_conditional_edges("analyst", should_continue_after_analyst, {
        "reflection": "reflection",
        "decider": "decider",
        "human_review": "human_review",
    })
    workflow.add_conditional_edges("reflection", should_continue_after_reflection, {
        "decider": "decider",
        "human_review": "human_review",
    })
    workflow.add_conditional_edges("decider", should_continue_after_decider, {
        "complete": END,
        "human_review": "human_review",
    })
    workflow.add_edge("human_review", END)

    logger.info(
        "graph.built",
        nodes=["scout", "analyst", "reflection", "decider", "human_review"],
        entry_point="scout",
        elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
    )
    return workflow


# 编译图（带持久化检查点）
_memory = MemorySaver()
decision_app = build_decision_graph().compile(checkpointer=_memory)
logger.info("graph.compiled", checkpointer="MemorySaver")


async def run_decision_flow(request_id: str, raw_data_id: str, raw_data_payload: dict = None) -> dict:
    """运行完整决策流程。

    Args:
        request_id: 请求ID
        raw_data_id: 原始数据ID
        raw_data_payload: 可选的原始数据载荷（避免 Agent 层重复查询 DB）

    Returns:
        最终 AgentState
    """
    flow_start = time.monotonic()
    from app.agents.state import create_initial_state

    initial_state = create_initial_state(request_id, raw_data_id)
    initial_state["_flow_start_mono"] = time.monotonic()
    if raw_data_payload:
        initial_state["raw_data_payload"] = raw_data_payload
        logger.info(
            "graph.raw_data_injected",
            request_id=request_id,
            payload_keys=list(raw_data_payload.keys()),
        )

    config = {"configurable": {"thread_id": request_id}}

    logger.info(
        "graph.flow_start",
        request_id=request_id,
        raw_data_id=raw_data_id,
        thread_id=request_id,
    )

    final_state = await decision_app.ainvoke(initial_state, config)  # type: ignore[call-overload]  # 同上：langgraph 1.x 存根与运行时不一致

    total_elapsed = round((time.monotonic() - flow_start) * 1000, 1)
    node_timings = final_state.get("node_timings") or []

    # === 决策指标 ===
    decision_result = final_state.get("decision_result") or {}
    confidence = final_state.get("confidence")
    risk_level = final_state.get("risk_level") or "unknown"
    action = decision_result.get("action") or "none"
    if confidence is not None:
        DECISION_CONFIDENCE.labels(decision_type=action).set(confidence)
    if final_state.get("status") == DecisionStatus.COMPLETED:
        DECISIONS_TOTAL.labels(decision_type=action, risk_level=risk_level).inc()

    logger.info(
        "graph.flow_complete",
        request_id=request_id,
        status=final_state.get("status"),
        risk_score=final_state.get("risk_score"),
        risk_level=final_state.get("risk_level"),
        decision=(final_state.get("decision_result") or {}).get("action"),
        confidence=final_state.get("confidence"),
        node_timings=node_timings,
        total_elapsed_ms=total_elapsed,
    )
    return final_state
