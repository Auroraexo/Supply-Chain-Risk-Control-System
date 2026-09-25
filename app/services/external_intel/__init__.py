"""外部风险情报服务。

目前接入：
- USGS 实时地震 Feed（M4.5+，近 7 天）：https://earthquake.usgs.gov/

设计原则：
- 所有外部调用失败时静默降级，返回空结果，**绝不阻断主风控链路**。
- 外部数据只作为风险加分项，不覆盖规则引擎/评分卡结果。
- 可扩展：未来加制裁名单、天气、地缘政治事件时，在本目录新增对应模块。
"""
from __future__ import annotations

import math
import time

import httpx
import structlog

logger = structlog.get_logger(__name__)

USGS_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
_CACHE: dict[str, object] = {"fetched_at": 0.0, "features": []}
_CACHE_TTL_SEC = 600  # 地震数据 10 分钟缓存一次即可


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点间大圆距离（公里）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _fetch_earthquakes() -> list[dict]:
    """拉取 USGS 近 7 天 M4.5+ 地震列表，带 10 分钟缓存。"""
    now = time.time()
    if _CACHE["features"] and now - float(_CACHE["fetched_at"]) < _CACHE_TTL_SEC:
        return list(_CACHE["features"])  # type: ignore[arg-type]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(USGS_FEED_URL)
            resp.raise_for_status()
            data = resp.json()
        features = data.get("features", [])
        _CACHE["features"] = features
        _CACHE["fetched_at"] = now
        logger.info("external_intel.usgs_loaded", count=len(features))
        return features
    except Exception as e:  # noqa: BLE001
        logger.warning("external_intel.usgs_fetch_failed", error=str(e))
        return list(_CACHE["features"])  # 失败时退回旧缓存，可能为空


async def assess_disaster_risk(lat: float, lon: float, radius_km: float = 250.0) -> dict:
    """评估指定地点周边的地震风险。

    Args:
        lat: 供应商纬度
        lon: 供应商经度
        radius_km: 关注半径（公里）

    Returns:
        {
            "nearby_quakes": 近 7 天半径内 M4.5+ 地震数,
            "max_magnitude": 最大震级,
            "nearest_km": 最近一次地震距离,
            "risk_addon": 0-10 的风险加分,
            "events": [ {place, mag, km} ... 最多 5 条 ]
        }
    """
    empty = {
        "nearby_quakes": 0,
        "max_magnitude": 0.0,
        "nearest_km": None,
        "risk_addon": 0.0,
        "events": [],
    }

    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return empty

    features = await _fetch_earthquakes()
    nearby: list[dict] = []
    nearest: float | None = None
    max_mag = 0.0

    for f in features:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        q_lon, q_lat = coords[0], coords[1]
        try:
            km = _haversine_km(lat_f, lon_f, float(q_lat), float(q_lon))
        except (TypeError, ValueError):
            continue
        if km > radius_km:
            continue
        props = f.get("properties") or {}
        mag = float(props.get("mag") or 0.0)
        nearby.append({
            "place": props.get("place", "unknown"),
            "mag": mag,
            "km": round(km, 1),
            "time": props.get("time"),
        })
        max_mag = max(max_mag, mag)
        nearest = km if nearest is None else min(nearest, km)

    # 风险加分：M6+ 且 100km 内 +10；M5+ 且 200km 内 +5；其余 +0
    addon = 0.0
    if max_mag >= 6.0 and (nearest is not None and nearest <= 100):
        addon = 10.0
    elif max_mag >= 5.0 and (nearest is not None and nearest <= 200):
        addon = 5.0

    events = sorted(nearby, key=lambda x: x["km"])[:5]
    result = {
        "nearby_quakes": len(nearby),
        "max_magnitude": max_mag,
        "nearest_km": nearest,
        "risk_addon": addon,
        "events": events,
    }
    logger.info(
        "external_intel.disaster_assessed",
        lat=lat_f, lon=lon_f,
        nearby=len(nearby), max_mag=max_mag, addon=addon,
    )
    return result
