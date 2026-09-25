import asyncio

from sqlalchemy import text

from app.core.database import get_engine
from app.core.mq import get_mq_connection
from app.core.redis import get_redis


async def dependency_health() -> dict:
    async def database():
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def redis():
        await (await get_redis()).ping()

    async def rabbitmq():
        connection = await get_mq_connection()
        if connection.is_closed:
            raise ConnectionError("RabbitMQ closed")

    async def probe(fn):
        try:
            async with asyncio.timeout(3):
                await fn()
            return "connected"
        except Exception:
            return "unavailable"

    results = await asyncio.gather(probe(database), probe(redis), probe(rabbitmq))
    deps = dict(zip(("database", "redis", "rabbitmq"), results, strict=True))
    return {"status": "ok" if all(v == "connected" for v in results) else "degraded", **deps}
