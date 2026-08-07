"""自我反思 Agent 节点。

职责：高风险决策二次校验，复核异常检测是否合理。
上游：analyst（仅当 risk_level 为 high/critical 时触发）
下游：decider 或 human_review
"""
import time
from datetime import datetime
from app.agents.state import AgentState, RiskLevel
import structlog

logger = structlog.get_logger(__name__)


async def reflection_node(state: AgentState) -> AgentState:
    """自我反思节点：高风险决策二次校验。"""
    node_start = time.monotonic()
    request_id = state["request_id"]

    risk_score = state.get("risk_score", 0)
    confidence = state.get("confidence", 0)
    facts = state.get("structured_facts", {})
    anomaly_tags = state.get("anomaly_tags", [])

    logger.info(
        "reflection.enter",
        request_id=request_id,
        risk_score=risk_score,
        confidence=confidence,
        anomaly_tags=anomaly_tags,
        fact_count=len(facts),
    )

    try:
        # ── 阶段 1：风险评分合理性校验 ──
        passed = True
        suggestions = []
        check_results = {}

        # 校验 1：高风险低置信度组合
        if risk_score > 80 and confidence < 0.7:
            passed = False
            suggestions.append("高风险低置信度，建议人工审核")
            check_results["high_risk_low_confidence"] = "failed"
            logger.warning(
                "reflection.check_failed",
                request_id=request_id,
                check="high_risk_low_confidence",
                risk_score=risk_score,
                confidence=confidence,
            )
        else:
            check_results["high_risk_low_confidence"] = "passed"

        # 校验 2：事实数据完整性
        if not facts:
            passed = False
            suggestions.append("缺少结构化事实数据")
            check_results["facts_integrity"] = "failed"
            logger.warning(
                "reflection.check_failed",
                request_id=request_id,
                check="facts_integrity",
                reason="empty_facts",
            )
        else:
            check_results["facts_integrity"] = "passed"

        # 校验 3：异常标签一致性
        if "delay" in anomaly_tags and facts.get("delay_days", 0) <= 0:
            suggestions.append("延迟标签与实际数据不一致")
            check_results["tag_consistency"] = "inconsistent"
            logger.warning(
                "reflection.tag_inconsistency",
                request_id=request_id,
                tag="delay",
                actual_delay_days=facts.get("delay_days"),
            )
        else:
            check_results["tag_consistency"] = "consistent"

        # ── 阶段 2：汇总结果 ──
        state["reflection_result"] = {
            "passed": passed,
            "suggestions": suggestions,
            "review_notes": f"风险评分 {risk_score}，校验{'通过' if passed else '未通过'}",
            "checks": check_results,
        }

        if passed:
            logger.info(
                "reflection.passed",
                request_id=request_id,
                checks=check_results,
                elapsed_ms=round((time.monotonic() - node_start) * 1000, 1),
            )
        else:
            logger.warning(
                "reflection.not_passed",
                request_id=request_id,
                suggestions=suggestions,
                checks=check_results,
            )

    except Exception as e:
        state["reflection_result"] = {
            "passed": False,
            "suggestions": [f"反思过程异常: {e}"],
            "review_notes": "反思过程异常",
            "checks": {"error": str(e)},
        }
        logger.error(
            "reflection.exception",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )

    state["updated_at"] = datetime.now().isoformat()
    total_elapsed = round((time.monotonic() - node_start) * 1000, 1)
    logger.info(
        "reflection.exit",
        request_id=request_id,
        passed=state["reflection_result"].get("passed"),
        suggestion_count=len(state["reflection_result"].get("suggestions", [])),
        elapsed_ms=total_elapsed,
    )
    return state