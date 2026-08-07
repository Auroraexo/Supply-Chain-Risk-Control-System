"""分析师 Agent 节点。

职责：计算风险评分、检测异常、生成分析推理。
上游：scout
下游：reflection（高风险）或 decider（低风险）或 human_review（失败）
"""
import time
from datetime import datetime
from app.agents.state import AgentState, DecisionStatus, RiskLevel
from app.agents.tools.risk_tools import calculate_risk_score, query_historical_patterns
import structlog

logger = structlog.get_logger(__name__)


async def analyst_node(state: AgentState) -> AgentState:
    """分析师节点：计算风险评分。"""
    node_start = time.monotonic()
    request_id = state["request_id"]
    retry_count = state.get("retry_count", 0)

    logger.info(
        "analyst.enter",
        request_id=request_id,
        retry_count=retry_count,
        data_quality_score=state.get("data_quality_score"),
    )

    try:
        facts = state.get("structured_facts", {})

        # ── 阶段 1：提取分析参数 ──
        delay_days = facts.get("delay_days", 0)
        price_deviation = abs(facts.get("price_deviation", 0))
        supplier_rating = facts.get("supplier_rating", 3.0)
        historical_incidents = facts.get("historical_incidents", 0)

        logger.info(
            "analyst.input_params",
            request_id=request_id,
            delay_days=delay_days,
            price_deviation=price_deviation,
            supplier_rating=supplier_rating,
            historical_incidents=historical_incidents,
        )

        # ── 阶段 2：查询历史模式 ──
        t0 = time.monotonic()
        entity_id = facts.get("supplier_id") or facts.get("order_id")
        if entity_id:
            historical = query_historical_patterns.invoke({"entity_id": str(entity_id)})
            logger.info(
                "analyst.historical_patterns",
                request_id=request_id,
                entity_id=entity_id,
                patterns_count=len(historical.get("patterns", [])),
                similarity_score=historical.get("similarity_score"),
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )

        # ── 阶段 3：计算风险评分 ──
        t1 = time.monotonic()
        risk_result = calculate_risk_score.invoke({
            "delay_days": delay_days,
            "price_deviation": price_deviation,
            "supplier_rating": supplier_rating,
            "historical_incidents": historical_incidents,
        })
        score = risk_result.get("score", 0)
        level = risk_result.get("level", "low")

        state["risk_score"] = score
        state["risk_level"] = level
        state["anomaly_tags"] = []
        if delay_days > 0:
            state["anomaly_tags"].append("delay")
        if price_deviation > 15:
            state["anomaly_tags"].append("price_anomaly")
        if supplier_rating < 3.0:
            state["anomaly_tags"].append("supplier_risk")
        state["analysis_reasoning"] = f"评分={score}, 等级={level}"
        state["retry_count"] = 0

        if level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
            logger.warning(
                "analyst.high_risk_detected",
                request_id=request_id,
                score=score,
                level=level,
                anomaly_tags=state["anomaly_tags"],
                will_trigger_reflection=True,
            )
        else:
            logger.info(
                "analyst.risk_calculated",
                request_id=request_id,
                score=score,
                level=level,
                anomaly_tags=state["anomaly_tags"],
                elapsed_ms=round((time.monotonic() - t1) * 1000, 1),
            )

    except Exception as e:
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["error_message"] = str(e)
        new_retry = state["retry_count"]

        if new_retry > 3:
            state["status"] = DecisionStatus.FAILED
            logger.error(
                "analyst.exhausted_retries",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
                exc_info=True,
            )
        else:
            logger.warning(
                "analyst.retry",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
            )

    state["updated_at"] = datetime.now().isoformat()
    total_elapsed = round((time.monotonic() - node_start) * 1000, 1)
    logger.info(
        "analyst.exit",
        request_id=request_id,
        status=state.get("status", DecisionStatus.PENDING),
        risk_score=state.get("risk_score"),
        risk_level=state.get("risk_level"),
        anomaly_tags=state.get("anomaly_tags"),
        elapsed_ms=total_elapsed,
    )
    return state