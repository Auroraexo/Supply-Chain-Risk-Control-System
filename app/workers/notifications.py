"""Run: python -m app.workers.notifications.

At-least-once outbox publishing, per-channel deduplication, bounded retries and DLQ.
SMTP/Webhook cannot guarantee exactly-once delivery across process crashes.
"""

import asyncio
import json
import smtplib
import ssl
from email.message import EmailMessage

import aio_pika
import httpx
import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import close_db_connection, get_session_factory
from app.core.mq import close_mq_connection, get_mq_channel, publish_risk_alert
from app.core.redis import close_redis_connection, get_redis
from app.models.audit_event import AuditEvent
from app.models.notification_outbox import NotificationOutbox
from app.services.settings_service import SettingsService

logger = structlog.get_logger(__name__)


async def publish_outbox() -> None:
    async with get_session_factory()() as db:
        rows = (
            (
                await db.execute(
                    select(NotificationOutbox)
                    .where(NotificationOutbox.status == "pending")
                    .order_by(NotificationOutbox.created_at)
                    .limit(20)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            try:
                await publish_risk_alert(
                    row.level, {**row.payload, "level": row.level, "event_id": row.id}
                )
                row.status = "published"
            except Exception:
                row.attempts += 1
                if row.attempts >= 5:
                    row.status = "failed"
                logger.warning(
                    "notification_publish_failed", event_id=row.id, attempts=row.attempts
                )
        await db.commit()


def send_email(address: str, payload: dict) -> None:
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        raise ValueError("SMTP is not configured")
    message = EmailMessage()
    message["From"], message["To"] = settings.SMTP_USER, address
    message["Subject"] = f"供应链风险预警 {payload.get('level', '')}"
    message.set_content(json.dumps(payload, ensure_ascii=False, indent=2))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def deliver(payload: dict) -> None:
    async with get_session_factory()() as db:
        value, _ = await SettingsService(db).read("notifications")
    channels = [c for c in (value or {}).get("channels", []) if c["enabled"]]
    if not channels:
        raise ValueError("No enabled notification channel")
    redis = await get_redis()
    for channel in channels:
        key = f"notification:{payload['event_id']}:{channel['id']}"
        if await redis.exists(key):
            continue
        if channel["type"] == "email":
            await asyncio.to_thread(send_email, channel["config"], payload)
        elif channel["type"] in ("webhook", "slack"):
            body = (
                {"text": json.dumps(payload, ensure_ascii=False)}
                if channel["type"] == "slack"
                else payload
            )
            async with httpx.AsyncClient(timeout=10) as client:
                result = await client.post(
                    channel["config"], json=body, headers={"Idempotency-Key": payload["event_id"]}
                )
                result.raise_for_status()
        else:
            raise ValueError("Unsupported notification channel")
        await redis.set(key, "delivered", ex=7 * 86400)
        async with get_session_factory()() as db:
            db.add(
                AuditEvent(
                    entity_id=payload["event_id"],
                    actor="notification-worker",
                    action="notification.delivered",
                    after={"channel_id": channel["id"]},
                )
            )
            await db.commit()


async def consume(message) -> None:
    redis = await get_redis()
    lock_key = f"notification-lock:{message.message_id}"
    locked = await redis.set(lock_key, "locked", nx=True, ex=120)
    if not locked:
        # Duplicate publishes from crash recovery are retried, not dropped.
        await retry_or_dead_letter(message)
        return
    try:
        await deliver(json.loads(message.body))
        await message.ack()
    except Exception:
        logger.warning("notification_delivery_failed", event_id=message.message_id)
        await retry_or_dead_letter(message)
    finally:
        await redis.delete(lock_key)


async def retry_or_dead_letter(message) -> None:
    attempts = int((message.headers or {}).get("attempts", 0))
    if attempts >= 3:
        await message.reject(requeue=False)
        return
    channel = await get_mq_channel()
    group = "high" if message.routing_key.endswith("high") else "normal"
    try:
        retry = aio_pika.Message(
            body=message.body,
            content_type="application/json",
            message_id=message.message_id,
            headers={"attempts": attempts + 1},
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(
            retry, routing_key=f"risk_alert.{group}.retry.v2", mandatory=True
        )
        await message.ack()
    except Exception:
        await message.nack(requeue=True)


async def main():
    from app.core.logging_config import setup_logging

    setup_logging()
    channel = await get_mq_channel()
    for group in ("high", "normal"):
        queue = await channel.get_queue(f"risk_alert.{group}.v2")
        await queue.consume(consume)
    try:
        while True:
            try:
                await publish_outbox()
            except Exception:
                logger.warning("notification_outbox_unavailable")
            await asyncio.sleep(10)
    finally:
        await close_mq_connection()
        await close_redis_connection()
        await close_db_connection()


if __name__ == "__main__":
    asyncio.run(main())
