"""人机介入节点。

职责：挂起决策流程，等待人工审核介入。
上游：所有异常路由（数据质量差、重试超限、反思不通过、决策失败）
下游：END
"""
import time
from datetime import datetime

import structlog

from app.agents.state import AgentState, DecisionStatus

logger = structlog.get_logger(__name__)


async def human_review_node(state: AgentState) -> AgentState:
    """人机介入节点：将决策挂起，等待人工审核。"""
    request_id = state.get("request_id")
    node_start = time.monotonic()

    # 汇总触发原因
    reason = state.get("error_message")
    sources = []
    if state.get("status") == DecisionStatus.FAILED:
        sources.append("agent_failure")
    if state.get("data_quality_score", 1.0) < 0.5:
        sources.append("low_quality")
    if state.get("retry_count", 0) > 2:
        sources.append("retry_exhausted")
    if not (state.get("reflection_result") or {}).get("passed", True):
        sources.append("reflection_failed")

    previous_state = {
        "status": state.get("status"),
        "risk_score": state.get("risk_score"),
        "risk_level": state.get("risk_level"),
        "data_quality_score": state.get("data_quality_score"),
        "retry_count": state.get("retry_count"),
        "anomaly_tags": state.get("anomaly_tags"),
    }

    state["status"] = DecisionStatus.HUMAN_REVIEW
    state["updated_at"] = datetime.now().isoformat()
    state["human_review_reason"] = reason or "system_routed"

    logger.warning(
        "human_review.required",
        request_id=request_id,
        reason=reason,
        trigger_sources=sources,
        previous_state=previous_state,
        elapsed_ms=round((time.monotonic() - node_start) * 1000, 1),
    )
    return state
