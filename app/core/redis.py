"""Redis 连接管理模块。

提供异步 Redis 客户端和连接池管理。
"""

import redis.asyncio as aioredis
from typing import Optional

from app.core.config import get_settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端单例。"""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis


async def close_redis_connection() -> None:
    """关闭 Redis 连接（应用关闭时调用）。"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None