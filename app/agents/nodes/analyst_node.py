"""分析师 Agent 节点。

职责：计算风险评分、检测异常、生成分析推理。
上游：scout
下游：reflection（高风险）或 decider（低风险）或 human_review（失败）
"""
import json
import time
from datetime import datetime

import structlog

from app.agents.prompt_loader import get_prompt_loader
from app.agents.state import AgentState, DecisionStatus, RiskLevel
from app.agents.tools.risk_tools import calculate_risk_score, query_historical_patterns
from app.core.llm import get_llm

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
        similarity_score = 0.0
        historical_pattern_count = 0
        if entity_id:
            historical = query_historical_patterns.invoke({"entity_id": str(entity_id)})
            similarity_score = float(historical.get("similarity_score", 0.0) or 0.0)
            historical_pattern_count = len(historical.get("patterns", []))
            logger.info(
                "analyst.historical_patterns",
                request_id=request_id,
                entity_id=entity_id,
                patterns_count=historical_pattern_count,
                similarity_score=similarity_score,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )

        # ── 阶段 3：计算风险评分（含历史模式加权调整） ──
        t1 = time.monotonic()
        risk_result = calculate_risk_score.invoke({
            "delay_days": delay_days,
            "price_deviation": price_deviation,
            "supplier_rating": supplier_rating,
            "historical_incidents": historical_incidents,
        })
        raw_score = risk_result.get("score", 0)
        score, level = _apply_historical_adjustment(
            raw_score=raw_score,
            similarity_score=similarity_score,
            historical_pattern_count=historical_pattern_count,
        )

        state["risk_score"] = score
        state["risk_level"] = level
        state["anomaly_tags"] = []
        if delay_days > 0:
            state["anomaly_tags"].append("delay")
        if price_deviation > 15:
            state["anomaly_tags"].append("price_anomaly")
        if supplier_rating < 3.0:
            state["anomaly_tags"].append("supplier_risk")
        if similarity_score > 0:
            state["anomaly_tags"].append("historical_pattern")
        state["retry_count"] = 0

        # ── 阶段 4：LLM 生成分析推理（失败时回退到规则文本） ──
        state["analysis_reasoning"] = await _generate_reasoning(
            request_id=request_id,
            score=score,
            level=level,
            anomaly_tags=state["anomaly_tags"],
            facts=facts,
        )

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


def _apply_historical_adjustment(
    raw_score: float,
    similarity_score: float,
    historical_pattern_count: int,
) -> tuple[float, str]:
    """根据历史高风险相似度上调风险评分。

    历史高风险记录（similarity_score 0-1）按比例加权到原始评分，
    封顶 100；加权后重新映射风险等级。

    Args:
        raw_score: 规则计算出的原始评分 (0-100)
        similarity_score: 历史高风险相似度 (0-1)
        historical_pattern_count: 命中的历史模式数量

    Returns:
        (调整后的评分, 调整后的风险等级)
    """
    similarity = max(0.0, min(1.0, float(similarity_score or 0.0)))
    if similarity <= 0 or historical_pattern_count <= 0:
        score = round(raw_score, 2)
        return score, _score_to_level(score)

    # 历史相似度加权：最多上调 20 分（相似度 1.0 时）
    adjustment = similarity * 20.0
    score = round(min(100.0, raw_score + adjustment), 2)
    logger.info(
        "analyst.historical_adjustment",
        raw_score=raw_score,
        similarity_score=similarity,
        adjustment=round(adjustment, 2),
        adjusted_score=score,
    )
    return score, _score_to_level(score)


def _score_to_level(score: float) -> str:
    """根据评分映射风险等级（与 risk_tools.calculate_risk_score 保持一致）。"""
    if score > 70:
        return "critical"
    if score > 50:
        return "high"
    if score > 30:
        return "medium"
    return "low"


async def _generate_reasoning(
    request_id: str,
    score: float,
    level: str,
    anomaly_tags: list[str],
    facts: dict,
) -> str:
    """用 LLM 生成分析推理，失败时静默回退到规则文本。

    LLM 作为增强层：不改变确定性评分结果，仅丰富 reasoning 文本。
    在 mock 模式或 LLM 不可用时，回退到简洁的规则摘要，保证链路稳定。
    """
    fallback = f"评分={score}, 等级={level}, 异常标签={','.join(anomaly_tags) or '无'}"
    try:
        prompt = await get_prompt_loader().get_prompt("analyst")
        system_prompt = prompt.get("system_prompt", "")
        llm = get_llm(temperature=0.0)
        user_msg = (
            f"结构化事实: {json.dumps(facts, ensure_ascii=False, default=str)}\n"
            f"风险评分: {score}\n"
            f"风险等级: {level}\n"
            f"异常标签: {anomaly_tags or '无'}\n"
            "请用简洁中文输出风险分析推理（说明主要风险来源与依据）。"
        )
        messages = [
            ("system", system_prompt),
            ("human", user_msg),
        ]
        resp = await llm.ainvoke(messages)
        content = getattr(resp, "content", "")
        if content and str(content).strip():
            return str(content).strip()
    except Exception as e:
        logger.warning(
            "analyst.reasoning_llm_fallback",
            request_id=request_id,
            error=str(e),
        )
    return fallback
