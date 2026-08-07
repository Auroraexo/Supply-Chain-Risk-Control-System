"""通知服务。"""
import structlog
from app.core.mq import publish_risk_alert

logger = structlog.get_logger(__name__)

class NotificationService:
    async def send_risk_alert(self, level: str, request_id: str, risk_score: float, details: dict) -> None:
        payload = {
            "type": "risk_alert",
            "level": level,
            "request_id": request_id,
            "risk_score": risk_score,
            "details": details,
        }
        await publish_risk_alert(level, payload)
        logger.info("risk_alert_published", level=level, request_id=request_id)

    async def send_websocket_alert(self, message: dict) -> None:
        from app.api.v1.websocket import manager
        await manager.broadcast(message)