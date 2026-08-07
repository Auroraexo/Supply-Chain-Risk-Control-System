"""决策图定义。

使用 LangGraph 构建完整的 Agent 决策流程：
scout → analyst → (reflection) → decider → (human_review) → END
"""
import time
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState, DecisionStatus, RiskLevel
from app.agents.nodes.scout_node import scout_node
from app.agents.nodes.analyst_node import analyst_node
from app.agents.nodes.decider_node import decider_node
from app.agents.nodes.reflection_node import reflection_node
from app.agents.nodes.human_review_node import human_review_node
import structlog

logger = structlog.get_logger(__name__)


def should_continue_after_scout(state: AgentState) -> str:
    """侦察兵完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")
    quality = state.get("data_quality_score", 0)
    retry = state.get("retry_count", 0)

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="status_failed")
        return "human_review"
    if quality < 0.5:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="low_quality", quality_score=quality)
        return "human_review"
    if retry > 2:
        logger.warning("graph.route.scout_to_human_review", request_id=request_id, reason="retry_exhausted", retry_count=retry)
        return "human_review"

    logger.info("graph.route.scout_to_analyst", request_id=request_id, quality_score=quality)
    return "analyst"


def should_continue_after_analyst(state: AgentState) -> str:
    """分析师完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")
    retry = state.get("retry_count", 0)
    risk_level = state.get("risk_level")

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.analyst_to_human_review", request_id=request_id, reason="status_failed")
        return "human_review"
    if retry > 3:
        logger.warning("graph.route.analyst_to_human_review", request_id=request_id, reason="retry_exhausted", retry_count=retry)
        return "human_review"
    if risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
        logger.info("graph.route.analyst_to_reflection", request_id=request_id, risk_level=risk_level, reason="high_risk")
        return "reflection"

    logger.info("graph.route.analyst_to_decider", request_id=request_id, risk_level=risk_level)
    return "decider"


def should_continue_after_reflection(state: AgentState) -> str:
    """反思完成后路由。"""
    request_id = state.get("request_id", "unknown")
    reflection = state.get("reflection_result") or {}
    passed = reflection.get("passed", True)

    if not passed:
        logger.warning("graph.route.reflection_to_human_review", request_id=request_id, suggestions=reflection.get("suggestions"))
        return "human_review"

    logger.info("graph.route.reflection_to_decider", request_id=request_id)
    return "decider"


def should_continue_after_decider(state: AgentState) -> str:
    """决策官完成后路由。"""
    request_id = state.get("request_id", "unknown")
    status = state.get("status")

    if status == DecisionStatus.FAILED:
        logger.warning("graph.route.decider_to_human_review", request_id=request_id, reason="status_failed")
        return "human_review"

    logger.info("graph.route.decider_to_end", request_id=request_id, decision=state.get("decision_result", {}).get("action"))
    return "complete"


def should_continue_after_human_review(state: AgentState) -> str:
    """人机介入后路由。"""
    request_id = state.get("request_id", "unknown")
    logger.info("graph.route.human_review_to_end", request_id=request_id)
    return "complete"


def build_decision_graph() -> StateGraph:
    """构建决策图。"""
    t0 = time.monotonic()
    workflow = StateGraph(dict)

    # 添加节点
    workflow.add_node("scout", scout_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("decider", decider_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("human_review", human_review_node)

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

    final_state = await decision_app.ainvoke(initial_state, config)

    total_elapsed = round((time.monotonic() - flow_start) * 1000, 1)
    logger.info(
        "graph.flow_complete",
        request_id=request_id,
        status=final_state.get("status"),
        risk_score=final_state.get("risk_score"),
        risk_level=final_state.get("risk_level"),
        decision=final_state.get("decision_result", {}).get("action"),
        confidence=final_state.get("confidence"),
        total_elapsed_ms=total_elapsed,
    )
    return final_state