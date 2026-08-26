"""AI 自动化编排服务。

为三大核心模块提供 AI 自动化能力：
1. 自动分析（风险分析）：自动捞取待处理原始数据，逐条运行 Agent 分析流水线
2. 自动审核（决策管理）：AI 审核员按置信度与风险等级自动终局待处理决策
3. 规则优化（规则引擎）：AI 分析历史分析结果，生成规则建议并可选直接应用
"""
import json
import time
from collections import Counter

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.llm import get_llm
from app.models.analysis_result import AnalysisResult
from app.models.decision_result import Decision as DecisionEnum, DecisionResult
from app.repositories.raw_data_repo import RawDataRepository
from app.schemas.rule import RuleCreateRequest
from app.services.decision_service import DecisionService
from app.services.risk_service import RiskService
from app.services.rule_service import RuleService

logger = structlog.get_logger(__name__)

AI_REVIEWER = "ai-auto-review"


class AutomationService:
    """AI 自动化编排服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────
    # 1. 风险分析自动化：自动分析待处理原始数据
    # ──────────────────────────────────────────────
    async def run_auto_analysis(self, max_items: int) -> dict:
        """自动捞取待处理原始数据并运行 Agent 分析流水线。"""
        flow_start = time.monotonic()
        repo = RawDataRepository(self.db)
        pending = await repo.get_pending(limit=max_items)

        items: list[dict] = []
        risk_service = RiskService(self.db)
        for raw in pending:
            # 先取出标量值：analyze 内部会 commit/rollback 导致 ORM 对象过期
            raw_id, source_id = raw.id, raw.source_id
            try:
                result = await risk_service.analyze(raw_id)
                items.append({
                    "raw_data_id": raw_id,
                    "source_id": source_id,
                    "status": "completed",
                    "risk_level": result.get("risk_level"),
                    "risk_score": result.get("risk_score"),
                    "decision": result.get("decision"),
                })
            except AppException as e:
                await self.db.rollback()
                items.append({
                    "raw_data_id": raw_id,
                    "source_id": source_id,
                    "status": "failed",
                    "error": e.message,
                })
            except Exception as e:  # noqa: BLE001 - 单条失败不影响整体批次
                await self.db.rollback()
                items.append({
                    "raw_data_id": raw_id,
                    "source_id": source_id,
                    "status": "failed",
                    "error": str(e),
                })

        completed = sum(1 for i in items if i["status"] == "completed")
        logger.info(
            "automation.auto_analysis_done",
            total=len(pending),
            completed=completed,
            failed=len(items) - completed,
            elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
        )
        return {
            "total": len(pending),
            "completed": completed,
            "failed": len(items) - completed,
            "items": items,
        }

    # ──────────────────────────────────────────────
    # 2. 决策管理自动化：AI 自动审核待处理决策
    # ──────────────────────────────────────────────
    async def run_auto_review(self, confidence_threshold: float) -> dict:
        """AI 审核员自动终局待审核/已升级决策。

        策略：
        - 置信度 >= 阈值 且风险等级为 low/medium → 自动批准
        - 置信度 >= 阈值 且风险等级为 high/critical → 自动驳回
        - 其余保留人工审核
        """
        flow_start = time.monotonic()
        rows = await self.db.execute(
            select(DecisionResult).where(
                DecisionResult.decision.in_([DecisionEnum.PENDING_REVIEW, DecisionEnum.ESCALATE])
            )
        )
        pending = list(rows.scalars().all())

        service = DecisionService(self.db)
        items: list[dict] = []
        for decision in pending:
            # 先取出标量值：submit_review 内部 commit 会导致 ORM 对象过期
            request_id = decision.request_id
            analysis = decision.analysis
            risk_level = analysis.risk_level.value if analysis and analysis.risk_level else None
            confidence = decision.confidence or 0.0

            if confidence >= confidence_threshold and risk_level in ("low", "medium"):
                await service.submit_review(
                    request_id, "approve", AI_REVIEWER,
                    f"AI 自动审核：置信度 {confidence:.2f} ≥ 阈值且风险等级 {risk_level} 可接受",
                )
                items.append({
                    "request_id": request_id,
                    "action": "approve",
                    "reason": f"置信度 {confidence:.2f} 达标，风险等级 {risk_level} 可接受",
                })
            elif confidence >= confidence_threshold and risk_level in ("high", "critical"):
                await service.submit_review(
                    request_id, "reject", AI_REVIEWER,
                    f"AI 自动审核：置信度 {confidence:.2f} ≥ 阈值且风险等级 {risk_level} 过高",
                )
                items.append({
                    "request_id": request_id,
                    "action": "reject",
                    "reason": f"置信度 {confidence:.2f} 达标，风险等级 {risk_level} 过高",
                })
            else:
                items.append({
                    "request_id": request_id,
                    "action": "keep",
                    "reason": f"置信度 {confidence:.2f} 低于阈值 {confidence_threshold:.2f}，保留人工审核",
                })

        processed = sum(1 for i in items if i["action"] != "keep")
        logger.info(
            "automation.auto_review_done",
            total=len(pending),
            processed=processed,
            kept=len(items) - processed,
            elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
        )
        return {
            "total": len(pending),
            "processed": processed,
            "kept": len(items) - processed,
            "items": items,
        }

    # ──────────────────────────────────────────────
    # 3. 规则引擎自动化：AI 规则优化建议
    # ──────────────────────────────────────────────
    async def run_auto_rules(self, apply: bool) -> dict:
        """AI 分析历史分析结果并生成规则建议，可选直接应用到规则树。"""
        flow_start = time.monotonic()

        # ── 阶段 1：统计近期分析结果 ──
        rows = await self.db.execute(
            select(AnalysisResult).order_by(AnalysisResult.created_at.desc()).limit(50)
        )
        analyses = list(rows.scalars().all())

        level_counter = Counter(a.risk_level.value for a in analyses if a.risk_level)
        tag_counter: Counter = Counter()
        for a in analyses:
            for tag in (a.anomaly_tags or []):
                tag_counter[tag] += 1

        stats = {
            "total": len(analyses),
            "critical": level_counter.get("critical", 0),
            "high": level_counter.get("high", 0),
            "medium": level_counter.get("medium", 0),
            "low": level_counter.get("low", 0),
            "high_critical_count": level_counter.get("critical", 0) + level_counter.get("high", 0),
            "top_tags": [t for t, _ in tag_counter.most_common(3)],
        }

        # ── 阶段 2：LLM 生成建议，失败回退到确定性策略 ──
        suggestions, source = await self._suggest_rules(stats)

        # ── 阶段 3：去重并可选应用 ──
        applied: list[str] = []
        if apply and suggestions:
            rule_service = RuleService(self.db)
            tree = await rule_service.get_tree()
            existing_names = self._collect_names(tree)

            for s in suggestions:
                if s["rule_name"] in existing_names:
                    continue
                try:
                    root = await rule_service.create_rule(RuleCreateRequest(
                        rule_name=s["rule_name"],
                        rule_type="group",
                        logic_op="AND",
                        priority=s["priority"],
                        description=s["reason"],
                    ))
                    await rule_service.create_rule(RuleCreateRequest(
                        rule_name=f"{s['rule_name']}-条件",
                        rule_type="condition",
                        parent_id=root["id"],
                        field_name=s["condition"]["field"],
                        operator=s["condition"]["operator"],
                        threshold_value=s["condition"]["value"],
                        logic_op="AND",
                    ))
                    await rule_service.create_rule(RuleCreateRequest(
                        rule_name=f"{s['rule_name']}-动作",
                        rule_type="action",
                        parent_id=root["id"],
                        action=s["action"],
                    ))
                    applied.append(s["rule_name"])
                except Exception as e:  # noqa: BLE001 - 单条规则失败不影响其他
                    await self.db.rollback()
                    logger.warning("automation.rule_apply_failed", rule=s["rule_name"], error=str(e))

        logger.info(
            "automation.auto_rules_done",
            source=source,
            suggestion_count=len(suggestions),
            applied=applied,
            elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
        )
        return {
            "stats": stats,
            "suggestions": suggestions,
            "applied": applied,
            "source": source,
        }

    async def _suggest_rules(self, stats: dict) -> tuple[list[dict], str]:
        """优先用 LLM 生成规则建议，解析失败回退到确定性策略。"""
        try:
            llm = get_llm(temperature=0.0)
            user_msg = (
                f"近期供应链风险分析统计：共 {stats['total']} 条，"
                f"严重 {stats['critical']}、高 {stats['high']}、中 {stats['medium']}、低 {stats['low']}，"
                f"高频异常标签：{', '.join(stats['top_tags']) or '无'}。\n"
                "请输出 JSON 数组，每项包含字段："
                'rule_name、condition(field/operator/value)、action(approve/reject/escalate)、priority(0-100)、reason。'
                "仅输出 JSON，不要其他内容。"
            )
            resp = await llm.ainvoke([
                ("system", "你是供应链风险规则专家，只输出严格 JSON。"),
                ("human", user_msg),
            ])
            content = str(getattr(resp, "content", "") or "").strip()
            start, end = content.find("["), content.rfind("]")
            if start != -1 and end > start:
                parsed = json.loads(content[start:end + 1])
                if isinstance(parsed, list) and parsed:
                    return [self._normalize_suggestion(s) for s in parsed if isinstance(s, dict)], "llm"
        except Exception as e:  # noqa: BLE001 - LLM 不可用时回退
            logger.warning("automation.llm_suggestion_fallback", error=str(e))
        return self._fallback_suggestions(stats), "fallback"

    @staticmethod
    def _normalize_suggestion(raw: dict) -> dict:
        condition = raw.get("condition") or {}
        return {
            "rule_name": str(raw.get("rule_name", "AI 生成规则")),
            "condition": {
                "field": str(condition.get("field", "risk_score")),
                "operator": str(condition.get("operator", "gte")),
                "value": str(condition.get("value", "0.7")),
            },
            "action": str(raw.get("action", "escalate")),
            "priority": int(raw.get("priority", 50) or 50),
            "reason": str(raw.get("reason", "AI 生成")),
        }

    @staticmethod
    def _fallback_suggestions(stats: dict) -> list[dict]:
        """确定性兜底建议：基于统计分布生成阈值规则。"""
        suggestions = []
        if stats["high_critical_count"] > 0:
            suggestions.append({
                "rule_name": "AI 自动生成-高风险自动驳回",
                "condition": {"field": "risk_score", "operator": "gte", "value": "0.7"},
                "action": "reject",
                "priority": 90,
                "reason": f"近期 {stats['total']} 条分析中含 {stats['high_critical_count']} 条高/严重风险，建议 risk_score>=0.7 自动驳回",
            })
        if stats["low"] > 0:
            suggestions.append({
                "rule_name": "AI 自动生成-低风险自动批准",
                "condition": {"field": "risk_score", "operator": "lte", "value": "0.3"},
                "action": "approve",
                "priority": 80,
                "reason": f"近期 {stats['low']} 条低风险分析，建议 risk_score<=0.3 自动批准以提升效率",
            })
        if not suggestions:
            suggestions.append({
                "rule_name": "AI 自动生成-中风险升级人工",
                "condition": {"field": "risk_score", "operator": "gte", "value": "0.5"},
                "action": "escalate",
                "priority": 70,
                "reason": "暂无足够历史数据，建议中风险以上升级人工审核",
            })
        return suggestions

    @staticmethod
    def _collect_names(tree: list[dict]) -> set[str]:
        names: set[str] = set()

        def walk(nodes: list[dict]) -> None:
            for node in nodes:
                names.add(node.get("rule_name", ""))
                walk(node.get("children") or [])

        walk(tree)
        return names
