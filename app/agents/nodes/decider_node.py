"""决策官 Agent 节点。

职责：综合风险评分与置信度，做出最终决策（approve/reject/escalate）。
上游：analyst 或 reflection
下游：END 或 human_review

决策优先级：
1. 规则引擎（rule_nodes 决策树，若 DB 中存在活跃规则）
2. 决策阈值矩阵（内置兜底）
"""
import time
from datetime import datetime

import structlog

from app.agents.prompt_loader import get_prompt_loader
from app.agents.state import AgentState, DecisionStatus
from app.core.llm import get_llm

logger = structlog.get_logger(__name__)

# 决策阈值矩阵：(risk_score 上限, decision, confidence) —— 作为规则引擎不可用时的兜底
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

        # ── 阶段 1：决策匹配（规则引擎优先，矩阵兜底） ──
        decision, confidence, path, decision_source = await _resolve_decision(
            request_id=request_id,
            risk_score=risk_score,
            risk_level=risk_level,
            facts=state.get("structured_facts") or {},
        )

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
        state["decision_path"] = path
        state["decision_explanation"] = await _generate_explanation(
            request_id=request_id,
            decision=decision,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            decision_source=decision_source,
        )
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
                decision_path=path,
                decision_source=decision_source,
            )
        else:
            logger.info(
                "decider.decision_made",
                request_id=request_id,
                decision=decision,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                decision_path=path,
                decision_source=decision_source,
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


async def _resolve_decision(
    request_id: str,
    risk_score: float,
    risk_level: str,
    facts: dict,
) -> tuple[str, float, list[str], str]:
    """解析决策结果。

    优先使用规则引擎（rule_nodes 决策树），不可用时回退到决策矩阵。
    返回 (decision, confidence, path, source)。
    """
    # 尝试规则引擎
    try:
        rule_decision = await _decision_from_rule_engine(
            request_id=request_id,
            risk_score=risk_score,
            risk_level=risk_level,
            facts=facts,
        )
        if rule_decision is not None:
            return rule_decision
    except Exception as e:
        logger.warning(
            "decider.rule_engine_fallback",
            request_id=request_id,
            error=str(e),
        )

    # 矩阵兜底
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

    path = ["root", "risk_assessment", decision]
    return decision, confidence, path, "matrix"


async def _decision_from_rule_engine(
    request_id: str,
    risk_score: float,
    risk_level: str,
    facts: dict,
) -> tuple[str, float, list[str], str] | None:
    """从规则引擎（rule_nodes 决策树）解析决策。

    通过 DecisionTreeWalker 遍历活跃规则树，命中 action 节点则采用；
    未命中或 DB 无规则时返回 None，由调用方回退到矩阵。
    """
    from app.core.database import get_session_factory
    from app.repositories.rule_repo import RuleRepository
    from app.rule_engine.tree_walker import DecisionTreeWalker

    context = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "decision_action": None,
        **{k: v for k, v in facts.items() if k in ("delay_days", "price_deviation", "supplier_rating", "historical_incidents")},
    }

    factory = get_session_factory()
    async with factory() as session:
        repo = RuleRepository(session)
        roots = await repo.get_root_nodes()

        if not roots:
            logger.info("decider.rule_engine.no_active_rules", request_id=request_id)
            return None

        walker = DecisionTreeWalker(rule_repo=repo)
        matched_action = None
        matched_path: list[str] = []

        # 按优先级由高到低遍历根节点
        for root in roots:
            path = await walker.walk(root.id, context)
            action = context.get("decision_action")
            if action is not None:
                matched_action = action
                matched_path = path
                break

    if matched_action is None:
        logger.info("decider.rule_engine.no_match", request_id=request_id)
        return None

    # 规则引擎命中的 action 归一化；置信度按风险等级映射
    confidence = _confidence_for_action(matched_action, risk_level)
    logger.info(
        "decider.rule_engine.matched",
        request_id=request_id,
        action=matched_action,
        path=matched_path,
        confidence=confidence,
    )
    return matched_action, confidence, matched_path, "rule_engine"


def _confidence_for_action(action: str, risk_level: str) -> float:
    """根据 action 与风险等级估算置信度。"""
    if action == "approve":
        return 0.95 if risk_level in ("low", "medium") else 0.80
    if action == "escalate":
        return 0.60
    if action == "reject":
        return 0.90
    return 0.70


async def _generate_explanation(
    request_id: str,
    decision: str,
    risk_score: float,
    risk_level: str,
    confidence: float,
    decision_source: str,
) -> str:
    """用 LLM 生成决策解释，失败时回退到规则文本。"""
    fallback = (
        f"风险评分 {risk_score}，等级 {risk_level}，"
        f"置信度 {confidence:.2f}，决策为 {decision}"
    )
    try:
        prompt = await get_prompt_loader().get_prompt("decider")
        system_prompt = prompt.get("system_prompt", "")
        llm = get_llm(temperature=0.0)
        user_msg = (
            f"风险评分: {risk_score}\n"
            f"风险等级: {risk_level}\n"
            f"决策来源: {decision_source}\n"
            f"最终决策: {decision}\n"
            f"置信度: {confidence:.2f}\n"
            "请用简洁中文输出决策解释（说明决策依据与主要风险点）。"
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
            "decider.explanation_llm_fallback",
            request_id=request_id,
            error=str(e),
        )
    return fallback
