"""侦察兵 Agent 节点。

职责：数据采集、结构化处理、质量检查。
上游：无（入口节点）
下游：analyst 或 human_review
"""
import time
from datetime import datetime

import structlog

from app.agents.state import AgentState, DecisionStatus
from app.agents.tools.data_tools import check_data_quality, get_raw_data

logger = structlog.get_logger(__name__)


async def scout_node(state: AgentState) -> AgentState:
    """侦察兵节点：数据采集与结构化处理。"""
    node_start = time.monotonic()
    request_id = state["request_id"]
    raw_data_id = state["raw_data_id"]
    retry_count = state.get("retry_count", 0)

    logger.info(
        "scout.enter",
        request_id=request_id,
        raw_data_id=raw_data_id,
        retry_count=retry_count,
    )

    try:
        # ── 阶段 1：获取原始数据（优先使用注入的载荷） ──
        t0 = time.monotonic()
        injected_payload = state.get("raw_data_payload")
        if injected_payload:
            raw_data = {
                "raw_data_id": raw_data_id,
                "source_type": "injected",
                "payload": injected_payload,
            }
            logger.info(
                "scout.data_injected",
                request_id=request_id,
                raw_data_id=raw_data_id,
                payload_keys=list(injected_payload.keys()),
            )
        else:
            raw_data = get_raw_data.invoke({"raw_data_id": raw_data_id})
            logger.info(
                "scout.data_fetched",
                request_id=request_id,
                raw_data_id=raw_data_id,
                source_type=raw_data.get("source_type"),
                payload_keys=list(raw_data.get("payload", {}).keys()),
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )

        # ── 阶段 2：结构化事实 ──
        structured_facts = raw_data.get("payload", {})
        state["structured_facts"] = structured_facts
        logger.info(
            "scout.facts_structured",
            request_id=request_id,
            fact_count=len(structured_facts),
            fact_keys=list(structured_facts.keys()),
        )

        # ── 阶段 3：数据质量检查 ──
        t1 = time.monotonic()
        quality = check_data_quality.invoke({"raw_data": structured_facts})
        quality_score = quality.get("quality_score", 0.0)
        missing_fields = quality.get("missing_fields", [])
        state["data_quality_score"] = quality_score
        state["data_issues"] = missing_fields
        state["retry_count"] = 0

        if quality_score < 0.5:
            logger.warning(
                "scout.low_quality",
                request_id=request_id,
                quality_score=quality_score,
                missing_fields=missing_fields,
                total_fields=quality.get("total_fields"),
            )
        else:
            logger.info(
                "scout.quality_check_passed",
                request_id=request_id,
                quality_score=quality_score,
                elapsed_ms=round((time.monotonic() - t1) * 1000, 1),
            )

    except Exception as e:
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["error_message"] = str(e)
        new_retry = state["retry_count"]

        if new_retry > 2:
            state["status"] = DecisionStatus.FAILED
            logger.error(
                "scout.exhausted_retries",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
                exc_info=True,
            )
        else:
            logger.warning(
                "scout.retry",
                request_id=request_id,
                retry_count=new_retry,
                error=str(e),
            )

    state["updated_at"] = datetime.now().isoformat()
    total_elapsed = round((time.monotonic() - node_start) * 1000, 1)
    logger.info(
        "scout.exit",
        request_id=request_id,
        status=state.get("status", DecisionStatus.PENDING),
        quality_score=state.get("data_quality_score"),
        elapsed_ms=total_elapsed,
    )
    return state
