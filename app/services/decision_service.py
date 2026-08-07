"""决策服务。

负责决策的生成、查询、追踪和人工审核。
优先从 Agent 流程已持久化的结果中读取，必要时重新运行决策流程。
"""
import time
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.decision_repo import DecisionRepository
from app.repositories.agent_log_repo import AgentLogRepository
from app.models.decision_result import DecisionResult, Decision as DecisionModel
from app.core.exceptions import NotFoundException, HumanReviewRequiredException
import structlog

logger = structlog.get_logger(__name__)


class DecisionService:
    """决策服务。

    优先从已有的分析结果中获取决策，避免重复运行 Agent 流程。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analysis_repo = AnalysisRepository(db)
        self.decision_repo = DecisionRepository(db)
        self.agent_log_repo = AgentLogRepository(db)

    async def make_decision(self, request_id: str) -> dict:
        """生成决策。

        优先从已有的分析结果中读取决策数据。
        如果分析已完成但无决策结果，则重新运行 Agent 流程。
        """
        flow_start = time.monotonic()

        # 优先查找已有决策结果
        existing_decision = await self.decision_repo.get_by_request_id(request_id)
        if existing_decision:
            logger.info(
                "decision_service.cached_decision",
                request_id=request_id,
                decision=existing_decision.decision.value,
                confidence=existing_decision.confidence,
                elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
            )
            return {
                "request_id": request_id,
                "decision": existing_decision.decision.value,
                "confidence": existing_decision.confidence,
                "explanation": existing_decision.explanation,
                "decision_path": existing_decision.decision_path or [],
                "reflection_passed": existing_decision.reflection_passed,
                "from_cache": True,
            }

        # 查找分析结果
        analysis = await self.analysis_repo.get_by_request_id(request_id)
        if not analysis:
            raise NotFoundException(f"分析结果未找到: {request_id}")

        logger.info(
            "decision_service.making_decision",
            request_id=request_id,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level.value if analysis.risk_level else None,
        )

        # 分析存在但无决策 → 重新运行 Agent 决策流程
        from app.agents.graphs.decision_graph import run_decision_flow

        # 解析 facts_summary 中的结构化事实
        raw_data_payload = {}
        if analysis.facts_summary:
            facts = analysis.facts_summary
            raw_data_payload = facts.get("structured_facts", facts)

        final_state = await run_decision_flow(
            request_id=request_id,
            raw_data_id=analysis.raw_data_id,
            raw_data_payload=raw_data_payload,
        )

        # 持久化决策结果
        decision_result = final_state.get("decision_result") or {}
        reflection = final_state.get("reflection_result") or {}
        decision = DecisionResult(
            request_id=request_id,
            analysis_id=analysis.id,
            decision=DecisionModel(decision_result.get("action", "approve")),
            confidence=final_state.get("confidence", 0.0),
            explanation=final_state.get("decision_explanation", ""),
            decision_path=final_state.get("decision_path", []),
            reflection_passed=reflection.get("passed", True),
        )
        await self.decision_repo.create(decision)
        await self.db.commit()

        logger.info(
            "decision_service.decision_complete",
            request_id=request_id,
            decision=decision.decision.value,
            confidence=decision.confidence,
            total_elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
        )

        return {
            "request_id": request_id,
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "explanation": decision.explanation,
            "decision_path": decision.decision_path or [],
            "reflection_passed": decision.reflection_passed,
        }

    async def get_decision(self, request_id: str) -> dict | None:
        """获取决策结果。"""
        decision = await self.decision_repo.get_by_request_id(request_id)
        if not decision:
            return None
        return {
            "request_id": decision.request_id,
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "explanation": decision.explanation,
            "decision_path": decision.decision_path or [],
            "reflection_passed": decision.reflection_passed,
            "reviewed_by": decision.reviewed_by,
        }

    async def get_trace(self, request_id: str) -> dict:
        """获取决策追踪信息。"""
        logs = await self.agent_log_repo.get_by_request_id(request_id)
        total_tokens = await self.agent_log_repo.get_total_tokens(request_id)
        trace = [
            {
                "agent": log.agent_name,
                "node": log.node_name,
                "latency_ms": log.latency_ms,
                "tokens": {"prompt": log.prompt_tokens, "completion": log.completion_tokens},
                "error": log.error_message,
            }
            for log in logs
        ]
        total_latency = sum(log.latency_ms or 0 for log in logs)
        return {
            "request_id": request_id,
            "trace": trace,
            "total_latency_ms": total_latency,
            "total_tokens": total_tokens,
        }

    async def get_pending_reviews(self, page: int = 1, page_size: int = 20) -> dict:
        """获取待审核列表。"""
        pending = await self.decision_repo.get_pending_reviews(limit=page_size)
        return {
            "items": [
                {
                    "request_id": d.request_id,
                    "decision": d.decision.value,
                    "confidence": d.confidence,
                    "explanation": d.explanation,
                }
                for d in pending
            ],
            "total": len(pending),
        }

    async def submit_review(self, request_id: str, action: str, reviewer: str, comment: str | None = None, override_decision: str | None = None) -> dict:
        """提交人工审核结果。"""
        decision = await self.decision_repo.get_by_request_id(request_id)
        if not decision:
            raise NotFoundException(f"决策结果未找到: {request_id}")

        if action == "approve":
            decision.decision = DecisionModel.APPROVE
        elif action == "reject":
            decision.decision = DecisionModel.REJECT
        elif action == "override" and override_decision:
            decision.decision = DecisionModel(override_decision)

        decision.reviewed_by = reviewer
        decision.confidence = 1.0
        await self.decision_repo.update(decision.id, {
            "decision": decision.decision,
            "reviewed_by": reviewer,
            "confidence": 1.0,
        })
        await self.db.commit()

        logger.info(
            "decision_service.review_submitted",
            request_id=request_id,
            action=action,
            reviewer=reviewer,
            final_decision=decision.decision.value,
        )
        return {
            "request_id": request_id,
            "status": "reviewed",
            "reviewed_by": reviewer,
            "decision": decision.decision.value,
        }