"""决策官 Agent 节点。

职责：综合风险评分与置信度，做出最终决策（approve/reject/escalate）。
上游：analyst 或 reflection
下游：END 或 human_review
"""
import time
from datetime import datetime
from app.agents.state import AgentState, DecisionStatus, RiskLevel
import structlog

logger = structlog.get_logger(__name__)

# 决策阈值矩阵：(risk_score 上限, decision, confidence)
DECISION_MATRIX = [
    (30, "approve", 0.95),
    (50, "approve", 0.80),
    (70, "escalate", 0.60),
    (float("inf"), "reject", 0.90),
]


async def decider_node(state: AgentState) -> AgentState:
    """决策官节点：综合决策与报告生成。"""
    node_start = time.monotonic()
    request_id = state["request_id"]
    retry_count = state.get("retry_count", 0)

    logger.info(
        "decider.enter",
        request_id=request_id,
        retry_count=retry_count,
        risk_score=state.get("risk_score"),
        risk_level=state.get("risk_level"),
        reflection_passed=(state.get("reflection_result") or {}).get("passed"),
    )

    try:
        risk_score = state.get("risk_score", 0)
        risk_level = state.get("risk_level")

        # ── 阶段 1：决策匹配 ──
        decision = None
        confidence = None
        for threshold, dec, conf in DECISION_MATRIX:
            if risk_score < threshold:
                decision = dec
                confidence = conf
                break

        if decision is None:
            decision = "reject"
            confidence = 0.90

        # ── 阶段 2：反思结果加权 ──
        reflection = state.get("reflection_result") or {}
        if reflection.get("passed") is False:
            confidence = max(0.0, confidence - 0.15)
            logger.info(
                "decider.confidence_penalized",
                request_id=request_id,
                original_confidence=confidence + 0.15,
                penalized_confidence=confidence,
                reason="reflection_not_passed",
            )

        # ── 阶段 3：写入结果 ──
        state["decision_result"] = {"action": decision, "risk_score": risk_score, "risk_level": risk_level}
        state["confidence"] = confidence
        state["decision_explanation"] = (
            f"风险评分 {risk_score}，等级 {risk_level}，"
            f"置信度 {confidence:.2f}，决策为 {decision}"
        )
        state["decision_path"] = ["root", "risk_assessment", decision]
        state["status"] = DecisionStatus.COMPLETED
        state["completed_at"] = datetime.now().isoformat()
        state["retry_count"] = 0

        if decision in ("reject", "escalate"):
            logger.warning(
                "decider.negative_decision",
                request_id=request_id,
                decision=decision,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                decision_path=state["decision_path"],
            )
        else:
            logger.info(
                "decider.decision_made",
                request_id=request_id,
                decision=decision,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                decision_path=state["decision_path"],
            )

    except Exception as e:
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["error_message"] = str(e)
        new_retry = state["retry_count"]

        if new_retry > 3:
            state["status"] = DecisionStatus.FAILED
            logger.error(
                "decider.exhausted_retries",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
                exc_info=True,
            )
        else:
            logger.warning(
                "decider.retry",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
            )

    state["updated_at"] = datetime.now().isoformat()
    total_elapsed = round((time.monotonic() - node_start) * 1000, 1)
    logger.info(
        "decider.exit",
        request_id=request_id,
        status=state.get("status", DecisionStatus.PENDING),
        decision=state.get("decision_result", {}).get("action"),
        confidence=state.get("confidence"),
        elapsed_ms=total_elapsed,
    )
    return state