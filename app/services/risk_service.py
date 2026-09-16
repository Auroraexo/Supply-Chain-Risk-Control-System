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
        stage_ms: dict[str, float] = {}

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
        stage_ms["validate_data"] = round((time.monotonic() - t0) * 1000, 1)

        # ── 阶段 2：解析原始数据载荷 ──
        t_parse = time.monotonic()
        raw_data_payload = {}
        if raw_data.payload:
            try:
                raw_data_payload = json.loads(raw_data.payload) if isinstance(raw_data.payload, str) else raw_data.payload
            except (json.JSONDecodeError, TypeError):
                raw_data_payload = {"raw": str(raw_data.payload)[:500]}
        stage_ms["parse_payload"] = round((time.monotonic() - t_parse) * 1000, 1)
        logger.info(
            "risk_service.payload_parsed",
            request_id=request_id,
            payload_keys=list(raw_data_payload.keys()),
            elapsed_ms=stage_ms["parse_payload"],
        )

        # ── 阶段 3：调用 Agent 决策流程 ──
        t1 = time.monotonic()
        from app.agents.graphs.decision_graph import run_decision_flow

        # Agent 流程包含多次 LLM 推理，耗时可能达数分钟；
        # 先结束挂起的只读事务释放数据库连接，避免连接长时间空闲被 MySQL 断开，
        # 同时提前取出后续要用的字段（rollback 会使 ORM 对象属性过期）
        source_id, source_type = raw_data.source_id, raw_data.source_type
        await self.db.rollback()

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
        agent_elapsed = round((time.monotonic() - t1) * 1000, 1)
        stage_ms["agent_flow"] = agent_elapsed
        logger.info(
            "risk_service.agent_flow_complete",
            request_id=request_id,
            agent_status=final_state.get("status"),
            risk_score=final_state.get("risk_score"),
            risk_level=final_state.get("risk_level"),
            decision=(final_state.get("decision_result") or {}).get("action"),
            confidence=final_state.get("confidence"),
            node_timings=final_state.get("node_timings") or [],
            elapsed_ms=agent_elapsed,
        )

        # ── 阶段 4：提取并持久化分析结果 ──
        t4 = time.monotonic()
        # Agent 流程可能提前路由到人工审核（数据质量差/重试超限），
        # 此时 Analyst 未运行，risk_level/risk_score 保持初始的 None；
        # state 初始化时键已存在，dict.get 的默认值不会生效，必须显式判 None。
        _raw_level = final_state.get("risk_level")
        _raw_score = final_state.get("risk_score")
        if _raw_level is None:
            logger.warning(
                "risk_service.missing_risk_level",
                request_id=request_id,
                agent_status=final_state.get("status"),
                reason=final_state.get("human_review_reason"),
                error=final_state.get("error_message"),
            )
        analysis = AnalysisResult(
            request_id=request_id,
            raw_data_id=raw_data_id,
            risk_score=float(_raw_score) if _raw_score is not None else None,
            risk_level=RiskLevel(_raw_level) if _raw_level is not None else None,
            anomaly_tags=final_state.get("anomaly_tags") or [],
            reasoning=final_state.get("analysis_reasoning") or "",
            facts_summary={
                "source_id": source_id,
                "source_type": source_type,
                "data_quality_score": final_state.get("data_quality_score"),
                "data_issues": final_state.get("data_issues", []),
                "structured_facts": final_state.get("structured_facts"),
            },
        )
        await self.analysis_repo.create(analysis)
        stage_ms["persist_analysis"] = round((time.monotonic() - t4) * 1000, 1)
        logger.info(
            "risk_service.analysis_persisted",
            request_id=request_id,
            analysis_id=analysis.id,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level.value if analysis.risk_level else None,
            elapsed_ms=stage_ms["persist_analysis"],
        )

        # ── 阶段 5：提取并持久化决策结果 ──
        t5 = time.monotonic()
        decision_result = final_state.get("decision_result") or {}
        reflection = final_state.get("reflection_result") or {}
        agent_status = final_state.get("status")
        # 进入人工审核流程的决策标记为 pending_review，而非默认 approve
        decision_enum = (
            DecisionModel.PENDING_REVIEW
            if agent_status == DecisionStatus.HUMAN_REVIEW
            else DecisionModel(decision_result.get("action", "approve"))
        )
        decision = DecisionResult(
            request_id=request_id,
            analysis_id=analysis.id,
            decision=decision_enum,
            confidence=final_state.get("confidence") or 0.0,
            explanation=final_state.get("decision_explanation") or "",
            decision_path=final_state.get("decision_path") or [],
            reflection_passed=reflection.get("passed", True),
        )
        await self.decision_repo.create(decision)
        stage_ms["persist_decision"] = round((time.monotonic() - t5) * 1000, 1)
        logger.info(
            "risk_service.decision_persisted",
            request_id=request_id,
            decision=decision.decision.value,
            confidence=decision.confidence,
            reflection_passed=decision.reflection_passed,
            elapsed_ms=stage_ms["persist_decision"],
        )

        # ── 阶段 6：更新原始数据状态 ──
        t6 = time.monotonic()
        # Scout 异常中断时质量分为 None，回退到 0.0 而非虚假的 0.95
        quality_score = final_state.get("data_quality_score")
        if quality_score is None:
            quality_score = 0.0
        await self.raw_data_repo.update_status(raw_data_id, RawDataStatus.PROCESSED, quality_score=quality_score)
        stage_ms["update_raw_data"] = round((time.monotonic() - t6) * 1000, 1)
        logger.info(
            "risk_service.raw_data_updated",
            request_id=request_id,
            new_status=RawDataStatus.PROCESSED.value,
            quality_score=quality_score,
            elapsed_ms=stage_ms["update_raw_data"],
        )

        # ── 阶段 7：高风险/人工审核通知 ──
        risk_level = final_state.get("risk_level")
        if agent_status == DecisionStatus.HUMAN_REVIEW or risk_level in ("high", "critical"):
            t7 = time.monotonic()
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
                    elapsed_ms=round((time.monotonic() - t7) * 1000, 1),
                )
            except Exception as e:
                logger.warning(
                    "risk_service.alert_failed",
                    request_id=request_id,
                    error=str(e),
                )
            finally:
                stage_ms["notify"] = round((time.monotonic() - t7) * 1000, 1)

        # ── 阶段 8：显式提交事务 ──
        t8 = time.monotonic()
        await self.db.commit()
        stage_ms["commit"] = round((time.monotonic() - t8) * 1000, 1)
        logger.info(
            "risk_service.transaction_committed",
            request_id=request_id,
            elapsed_ms=stage_ms["commit"],
        )

        total_elapsed = round((time.monotonic() - flow_start) * 1000, 1)
        logger.info(
            "risk_service.analyze_complete",
            request_id=request_id,
            raw_data_id=raw_data_id,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level.value if analysis.risk_level else None,
            decision=decision.decision.value,
            confidence=decision.confidence,
            agent_status=agent_status,
            total_elapsed_ms=total_elapsed,
            stage_ms=stage_ms,
        )

        return {
            "request_id": request_id,
            "status": "completed",
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level.value if analysis.risk_level else None,
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