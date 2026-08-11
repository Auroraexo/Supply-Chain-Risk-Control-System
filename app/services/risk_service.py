"""风险分析服务。

提供风险评估的核心业务逻辑，协调数据采集、规则匹配和 Agent 决策。
"""
import time
import uuid
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.raw_data_repo import RawDataRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.decision_repo import DecisionRepository
from app.models.analysis_result import AnalysisResult, RiskLevel
from app.models.decision_result import DecisionResult, Decision as DecisionModel
from app.models.raw_data import RawDataStatus
from app.core.exceptions import NotFoundException, DataQualityException, AppException, ErrorCode
from app.agents.state import DecisionStatus
import structlog

logger = structlog.get_logger(__name__)


class RiskService:
    """风险分析服务。

    协调数据验证 → Agent 决策流程 → 结果持久化的完整流程。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.raw_data_repo = RawDataRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.decision_repo = DecisionRepository(db)

    async def analyze(self, raw_data_id: str, force_reanalyze: bool = False) -> dict:
        """执行风险分析（含 Agent 决策全流程）。

        Args:
            raw_data_id: 原始数据ID
            force_reanalyze: 是否强制重新分析

        Returns:
            分析结果字典
        """
        flow_start = time.monotonic()
        request_id = str(uuid.uuid4())

        logger.info(
            "risk_service.analyze_start",
            request_id=request_id,
            raw_data_id=raw_data_id,
            force_reanalyze=force_reanalyze,
        )

        # ── 阶段 1：数据验证 ──
        t0 = time.monotonic()
        raw_data = await self.raw_data_repo.get_by_id(raw_data_id)
        if not raw_data:
            logger.error(
                "risk_service.raw_data_not_found",
                request_id=request_id,
                raw_data_id=raw_data_id,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            raise NotFoundException(f"原始数据未找到: {raw_data_id}")

        if raw_data.status == RawDataStatus.INVALID:
            logger.warning(
                "risk_service.data_invalid",
                request_id=request_id,
                raw_data_id=raw_data_id,
                data_status=raw_data.status.value,
            )
            raise DataQualityException(0.0, ["数据已被标记为无效"])

        logger.info(
            "risk_service.data_validated",
            request_id=request_id,
            raw_data_id=raw_data_id,
            source_type=raw_data.source_type,
            source_id=raw_data.source_id,
            data_status=raw_data.status.value,
            elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
        )

        # ── 阶段 2：解析原始数据载荷 ──
        raw_data_payload = {}
        if raw_data.payload:
            try:
                raw_data_payload = json.loads(raw_data.payload) if isinstance(raw_data.payload, str) else raw_data.payload
            except (json.JSONDecodeError, TypeError):
                raw_data_payload = {"raw": str(raw_data.payload)[:500]}

        # ── 阶段 3：调用 Agent 决策流程 ──
        t1 = time.monotonic()
        from app.agents.graphs.decision_graph import run_decision_flow

        final_state = await run_decision_flow(
            request_id=request_id,
            raw_data_id=raw_data_id,
            raw_data_payload=raw_data_payload,
        )
        if final_state is None:
            logger.error(
                "risk_service.agent_flow_returned_none",
                request_id=request_id,
                raw_data_id=raw_data_id,
            )
            raise AppException(
                code=ErrorCode.AGENT_STATE_ERROR,
                message="Agent 决策流程返回空结果，请检查 LLM 配置",
                status_code=500,
            )
        logger.info(
            "risk_service.agent_flow_complete",
            request_id=request_id,
            agent_status=final_state.get("status"),
            risk_score=final_state.get("risk_score"),
            risk_level=final_state.get("risk_level"),
            decision=final_state.get("decision_result", {}).get("action"),
            confidence=final_state.get("confidence"),
            elapsed_ms=round((time.monotonic() - t1) * 1000, 1),
        )

        # ── 阶段 4：提取并持久化分析结果 ──
        analysis = AnalysisResult(
            request_id=request_id,
            raw_data_id=raw_data_id,
            risk_score=final_state.get("risk_score", 0.0),
            risk_level=RiskLevel(final_state.get("risk_level", "low")),
            anomaly_tags=final_state.get("anomaly_tags", []),
            reasoning=final_state.get("analysis_reasoning", ""),
            facts_summary={
                "source_id": raw_data.source_id,
                "source_type": raw_data.source_type,
                "data_quality_score": final_state.get("data_quality_score"),
                "data_issues": final_state.get("data_issues", []),
                "structured_facts": final_state.get("structured_facts"),
            },
        )
        await self.analysis_repo.create(analysis)

        # ── 阶段 5：提取并持久化决策结果 ──
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

        # ── 阶段 6：更新原始数据状态 ──
        quality_score = final_state.get("data_quality_score", 0.95)
        await self.raw_data_repo.update_status(raw_data_id, RawDataStatus.PROCESSED, quality_score=quality_score)

        # ── 阶段 7：高风险/人工审核通知 ──
        agent_status = final_state.get("status")
        risk_level = final_state.get("risk_level")
        if agent_status == DecisionStatus.HUMAN_REVIEW or risk_level in ("high", "critical"):
            try:
                from app.services.notification_service import NotificationService
                notifier = NotificationService()
                await notifier.send_risk_alert(
                    level=risk_level or "unknown",
                    request_id=request_id,
                    risk_score=final_state.get("risk_score", 0),
                    details={
                        "decision": decision_result.get("action"),
                        "confidence": final_state.get("confidence"),
                        "anomaly_tags": final_state.get("anomaly_tags", []),
                        "reflection_passed": reflection.get("passed"),
                    },
                )
                logger.info(
                    "risk_service.alert_sent",
                    request_id=request_id,
                    level=risk_level,
                    status=agent_status,
                )
            except Exception as e:
                logger.warning(
                    "risk_service.alert_failed",
                    request_id=request_id,
                    error=str(e),
                )

        # ── 阶段 8：显式提交事务 ──
        await self.db.commit()
        logger.debug(
            "risk_service.transaction_committed",
            request_id=request_id,
        )

        total_elapsed = round((time.monotonic() - flow_start) * 1000, 1)
        logger.info(
            "risk_service.analyze_complete",
            request_id=request_id,
            raw_data_id=raw_data_id,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level.value,
            decision=decision.decision.value,
            confidence=decision.confidence,
            agent_status=agent_status,
            total_elapsed_ms=total_elapsed,
        )

        return {
            "request_id": request_id,
            "status": "completed",
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level.value,
            "anomaly_tags": analysis.anomaly_tags or [],
            "analysis_reasoning": analysis.reasoning,
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "decision_explanation": decision.explanation,
            "reflection_passed": decision.reflection_passed,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        }

    async def get_result(self, request_id: str) -> dict | None:
        """获取分析结果。"""
        t0 = time.monotonic()
        analysis = await self.analysis_repo.get_by_request_id(request_id)

        if not analysis:
            logger.debug(
                "risk_service.result_not_found",
                request_id=request_id,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            return None

        # 同时获取决策结果
        decision = await self.decision_repo.get_by_request_id(request_id)

        logger.debug(
            "risk_service.result_fetched",
            request_id=request_id,
            risk_score=analysis.risk_score,
            has_decision=decision is not None,
            elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
        )

        return {
            "request_id": analysis.request_id,
            "status": "completed",
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level.value if analysis.risk_level else None,
            "anomaly_tags": analysis.anomaly_tags or [],
            "analysis_reasoning": analysis.reasoning,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "decision": decision.decision.value if decision else None,
            "confidence": decision.confidence if decision else None,
            "decision_explanation": decision.explanation if decision else None,
            "reflection_passed": decision.reflection_passed if decision else None,
        }