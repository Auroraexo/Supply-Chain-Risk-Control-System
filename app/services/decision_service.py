"""决策服务。

负责决策的生成、查询、追踪和人工审核。
优先从 Agent 流程已持久化的结果中读取，必要时重新运行决策流程。
"""

import time
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit_event import AuditEvent
from app.core.exceptions import ValidationException, AppException
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
        """获取决策结果。

        request_id 参数兼容主键 id：前端列表跳转传的是记录主键。
        """
        decision = await self.decision_repo.get_by_request_or_id(request_id)
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
            "id": decision.id,
            "analysis_id": decision.analysis_id,
            "created_at": decision.created_at.isoformat(),
            "updated_at": decision.updated_at.isoformat() if decision.updated_at else None,
            "case_status": decision.case_status,
            "owner_id": decision.owner_id,
            "due_at": decision.due_at.isoformat() if decision.due_at else None,
            "resolution": decision.resolution,
            "revision": decision.revision,
        }

    async def get_trace(self, request_id: str) -> dict:
        """获取决策追踪信息。

        request_id 兼容主键 id；输出结构对齐前端 DecisionTrace：
        steps 为 Agent 执行步骤列表，final_decision/confidence 来自决策记录。
        """
        decision = await self.decision_repo.get_by_request_or_id(request_id)
        actual_request_id = decision.request_id if decision else request_id

        logs = await self.agent_log_repo.get_by_request_id(actual_request_id)
        total_tokens = await self.agent_log_repo.get_total_tokens(actual_request_id)
        steps = [
            {
                "step": log.node_name,
                "action": log.agent_name,
                "input": None,
                "output": log.error_message or None,
                "elapsed_ms": log.latency_ms or 0,
                "status": "error" if log.error_message else "success",
            }
            for log in logs
        ]
        total_latency = sum(log.latency_ms or 0 for log in logs)
        return {
            "request_id": actual_request_id,
            "steps": steps,
            "final_decision": decision.decision.value if decision else "unknown",
            "confidence": decision.confidence if decision else 0.0,
            "total_latency_ms": total_latency,
            "total_tokens": total_tokens,
        }

    async def get_pending_reviews(self, page: int = 1, page_size: int = 20) -> dict:
        """获取待审核列表。"""
        pending = await self.decision_repo.get_pending_reviews(
            limit=page_size, offset=(page - 1) * page_size
        )
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
            "total": await self.decision_repo.count_pending_reviews(),
        }

    async def submit_review(
        self,
        request_id: str,
        action: str,
        reviewer: str,
        comment: str | None = None,
        override_decision: str | None = None,
    ) -> dict:
        """提交人工审核结果。

        request_id 参数兼容主键 id：前端审批页路由参数是记录主键。
        """
        decision = (
            await self.db.execute(
                select(DecisionResult)
                .where(
                    (DecisionResult.request_id == request_id) | (DecisionResult.id == request_id)
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not decision:
            raise NotFoundException(f"决策结果未找到: {request_id}")

        if decision.decision not in (DecisionModel.PENDING_REVIEW, DecisionModel.ESCALATE):
            raise AppException(message="该决策已审核，请刷新后查看最新结果", status_code=409)
        if action not in ("approve", "reject", "override"):
            raise ValidationException("未知审核动作")
        if action in ("reject", "override") and not (comment or "").strip():
            raise ValidationException("驳回和覆盖必须填写理由")
        if action == "override" and override_decision not in ("approve", "reject", "escalate"):
            raise ValidationException("覆盖决策只能为 approve/reject/escalate")
        previous = decision.decision.value

        if action == "approve":
            decision.decision = DecisionModel.APPROVE
        elif action == "reject":
            decision.decision = DecisionModel.REJECT
        elif action == "override" and override_decision:
            decision.decision = DecisionModel(override_decision)

        decision.reviewed_by = reviewer
        decision.revision += 1
        # Human approval is not model confidence: preserve the original score.
        self.db.add(
            AuditEvent(
                entity_id=decision.id,
                action=f"review.{action}",
                actor=reviewer,
                before={"decision": previous},
                after={"decision": decision.decision.value},
                comment=comment,
            )
        )
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
