"""消息队列连接管理模块。

提供 RabbitMQ (aio-pika) 异步连接管理。
"""

from typing import Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel

from app.core.config import get_settings

_connection: Optional[AbstractRobustConnection] = None
_channel: Optional[AbstractRobustChannel] = None


async def get_mq_connection() -> AbstractRobustConnection:
    """获取 RabbitMQ 连接。"""
    global _connection
    if _connection is None or _connection.is_closed:
        settings = get_settings()
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    return _connection


async def get_mq_channel() -> AbstractRobustChannel:
    """获取 RabbitMQ Channel。"""
    global _channel
    if _channel is None or _channel.is_closed:
        conn = await get_mq_connection()
        _channel = await conn.channel()
        # 声明 Exchange
        risk_exchange = await _channel.declare_exchange(
            "risk_alert.topic", aio_pika.ExchangeType.TOPIC, durable=True
        )
        # 声明队列
        await _channel.declare_queue("risk_alert.high", durable=True)
        await _channel.declare_queue("risk_alert.normal", durable=True)
        await _channel.declare_queue("risk_alert.dlq", durable=True)
        # 绑定
        await _channel.declare_queue("risk_alert.high", durable=True)
    return _channel


async def publish_risk_alert(level: str, payload: dict) -> None:
    """发布风险预警消息。

    Args:
        level: 风险等级 (high/medium/low)
        payload: 消息内容
    """
    channel = await get_mq_channel()
    exchange = await channel.get_exchange("risk_alert.topic")
    message = aio_pika.Message(body=str(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
    await exchange.publish(message, routing_key=f"risk.alert.{level}")


async def close_mq_connection() -> None:
    """关闭 RabbitMQ 连接（应用关闭时调用）。"""
    global _connection, _channel
    if _channel is not None and not _channel.is_closed:
        await _channel.close()
        _channel = None
    if _connection is not None and not _connection.is_closed:
        await _connection.close()
        _connection = None