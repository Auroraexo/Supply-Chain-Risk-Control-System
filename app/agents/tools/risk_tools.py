"""风险计算工具。"""
import asyncio
import concurrent.futures
from typing import Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


@tool
def calculate_risk_score(delay_days: int, price_deviation: float, supplier_rating: float, historical_incidents: int) -> dict:
    """计算供应链风险评分。

    Args:
        delay_days: 延迟天数
        price_deviation: 价格偏差百分比
        supplier_rating: 供应商评分 (0-5)
        historical_incidents: 历史事故次数
    """
    score = delay_days * 5.0 + price_deviation * 3.0 + (5 - supplier_rating) * 4.0 + historical_incidents * 10.0
    score = min(score, 100.0)
    level = "low"
    if score > 70:
        level = "critical"
    elif score > 50:
        level = "high"
    elif score > 30:
        level = "medium"
    return {"score": round(score, 2), "level": level}


@tool
def query_historical_patterns(entity_id: str, pattern_type: str = "risk", limit: int = 20) -> dict:
    """查询历史风险模式。

    从历史分析结果中检索与指定实体（supplier_id / source_id）相关的模式，
    返回匹配的历史风险等级分布与相似度评分。

    Args:
        entity_id: 实体 ID（supplier_id 或 source_id）
        pattern_type: 模式类型 (risk/supplier/logistics)
        limit: 查询的历史记录条数上限
    """
    return _query_historical_sync(entity_id, pattern_type, limit)


def _query_historical_sync(entity_id: str, pattern_type: str, limit: int) -> dict:
    """同步桥接：在事件循环中安全地运行异步历史查询。"""
    factory = lambda: _query_historical_async(entity_id, pattern_type, limit)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    # 已有运行中的事件循环（如 FastAPI 请求上下文），用线程池桥接
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, factory())
        return future.result(timeout=10)


async def _query_historical_async(entity_id: str, pattern_type: str, limit: int) -> dict:
    """异步查询历史分析结果，按实体匹配并计算相似度。"""
    empty = {
        "patterns": [],
        "similarity_score": 0.0,
        "entity_id": entity_id,
        "pattern_type": pattern_type,
        "total_matched": 0,
    }
    try:
        from app.core.database import get_session_factory
        from app.repositories.analysis_repo import AnalysisRepository

        factory = get_session_factory()
        async with factory() as session:
            repo = AnalysisRepository(session)
            history = await repo.get_recent(limit=limit)

        patterns: list[dict] = []
        matched = 0
        for item in history:
            facts = (item.facts_summary or {}).get("structured_facts") or {}
            candidate_entity = (
                str(facts.get("supplier_id") or "")
                or str(facts.get("source_id") or "")
                or str((item.facts_summary or {}).get("source_id") or "")
            )
            if not candidate_entity or str(candidate_entity) != str(entity_id):
                continue
            matched += 1
            if item.risk_level is not None:
                patterns.append({
                    "request_id": item.request_id,
                    "risk_score": item.risk_score,
                    "risk_level": item.risk_level.value,
                    "anomaly_tags": item.anomaly_tags or [],
                })

        # 相似度：历史匹配中高风险占比，用于衡量该实体的历史风险倾向
        if matched == 0:
            similarity = 0.0
        else:
            risky = sum(
                1
                for p in patterns
                if p["risk_level"] in ("high", "critical")
            )
            similarity = round(risky / matched, 2)

        logger.info(
            "risk_tools.historical_patterns_queried",
            entity_id=entity_id,
            pattern_type=pattern_type,
            total_scanned=len(history),
            matched=matched,
            similarity_score=similarity,
        )
        return {
            "patterns": patterns,
            "similarity_score": similarity,
            "entity_id": entity_id,
            "pattern_type": pattern_type,
            "total_matched": matched,
        }
    except Exception as e:
        logger.warning(
            "risk_tools.historical_query_failed",
            entity_id=entity_id,
            error=str(e),
        )
        return empty
