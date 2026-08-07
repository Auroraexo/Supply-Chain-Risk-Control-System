"""数据查询工具。"""
import asyncio
import json
import structlog
from langchain_core.tools import tool
from typing import Optional

logger = structlog.get_logger(__name__)


def _query_raw_data_sync(raw_data_id: str) -> dict:
    """同步查询原始数据（内部使用 asyncio 桥接异步 DB 操作）。

    由于 LangChain @tool 要求同步函数，这里通过 asyncio 桥接
    异步数据库查询，确保在 Agent 节点中可以直接调用。
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 在已有事件循环中（如 FastAPI 请求上下文），创建新任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run_async_query, raw_data_id)
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(_async_query_raw_data(raw_data_id))
    except RuntimeError:
        # 没有事件循环，创建一个
        return asyncio.run(_async_query_raw_data(raw_data_id))


def _run_async_query(raw_data_id: str) -> dict:
    """在线程池中运行异步查询（用于已有事件循环的场景）。"""
    return asyncio.run(_async_query_raw_data(raw_data_id))


async def _async_query_raw_data(raw_data_id: str) -> dict:
    """异步查询原始数据，返回结构化信息。"""
    from app.core.database import get_session_factory
    from app.repositories.raw_data_repo import RawDataRepository

    factory = get_session_factory()
    async with factory() as session:
        try:
            repo = RawDataRepository(session)
            raw_data = await repo.get_by_id(raw_data_id)

            if not raw_data:
                logger.warning(
                    "data_tools.raw_data_not_found",
                    raw_data_id=raw_data_id,
                )
                return {
                    "raw_data_id": raw_data_id,
                    "source_type": "unknown",
                    "payload": {},
                    "data_hash": "",
                    "status": "not_found",
                    "quality_score": 0.0,
                }

            payload = raw_data.payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = {"raw": str(payload)[:500]}

            logger.info(
                "data_tools.raw_data_fetched",
                raw_data_id=raw_data_id,
                source_type=raw_data.source_type,
                source_id=raw_data.source_id,
                status=raw_data.status.value,
                quality_score=raw_data.quality_score,
            )

            return {
                "raw_data_id": raw_data.id,
                "source_type": raw_data.source_type,
                "source_id": raw_data.source_id,
                "payload": payload,
                "data_hash": raw_data.data_hash,
                "status": raw_data.status.value,
                "quality_score": raw_data.quality_score or 0.0,
            }
        except Exception as e:
            logger.error(
                "data_tools.query_failed",
                raw_data_id=raw_data_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "raw_data_id": raw_data_id,
                "source_type": "error",
                "payload": {},
                "error": str(e),
            }


@tool
def get_raw_data(raw_data_id: str) -> dict:
    """获取原始数据并返回结构化信息。

    从数据库查询指定 ID 的原始数据记录，返回包含
    source_type、payload、status 等字段的结构化字典。

    Args:
        raw_data_id: 原始数据ID
    """
    return _query_raw_data_sync(raw_data_id)


@tool
def check_data_quality(raw_data: dict, expected_fields: Optional[list[str]] = None) -> dict:
    """检查数据质量。

    Args:
        raw_data: 原始数据字典
        expected_fields: 期望字段列表
    """
    if expected_fields is None:
        expected_fields = ["order_id", "supplier_id", "amount", "expected_delivery", "actual_delivery"]
    present = [f for f in expected_fields if raw_data.get(f) is not None]
    score = len(present) / len(expected_fields) if expected_fields else 0.0
    missing = [f for f in expected_fields if f not in present]
    return {"quality_score": round(score, 2), "missing_fields": missing, "total_fields": len(expected_fields)}