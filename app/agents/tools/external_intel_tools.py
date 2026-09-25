"""外部情报 LangChain Tools，供 Agent 节点调用。"""
from __future__ import annotations

import asyncio
import concurrent.futures

import structlog
from langchain_core.tools import tool

from app.services.external_intel import assess_disaster_risk

logger = structlog.get_logger(__name__)


def _run_async(coro_factory, timeout: float = 8.0):
    """在事件循环中桥接异步协程。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(asyncio.run, coro_factory())
        return fut.result(timeout=timeout)


@tool
def query_disaster_risk(lat: float, lon: float, radius_km: float = 250.0) -> dict:
    """查询指定经纬度周边近 7 天的地震风险（USGS M4.5+）。

    当供应商所在地区有强震时，会返回风险加分（0-10），用于 Analyst 节点调整风险评分。
    外部服务不可用时返回空结果，不影响主流程。

    Args:
        lat: 供应商纬度
        lon: 供应商经度
        radius_km: 关注半径（公里），默认 250
    """
    try:
        return _run_async(lambda: assess_disaster_risk(lat, lon, radius_km))
    except Exception as e:  # noqa: BLE001
        logger.warning("external_intel.tool_failed", lat=lat, lon=lon, error=str(e))
        return {
            "nearby_quakes": 0,
            "max_magnitude": 0.0,
            "nearest_km": None,
            "risk_addon": 0.0,
            "events": [],
            "error": str(e),
        }
