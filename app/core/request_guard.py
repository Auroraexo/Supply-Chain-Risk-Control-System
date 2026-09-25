"""ASGI request size guard and distributed fixed-window rate limiting."""

import hashlib
import time

import structlog
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import decode_token

LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 65) end
return count
"""


class RequestGuardMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/v1/"):
            return await self.app(scope, receive, send)
        settings = get_settings()
        headers = dict(scope.get("headers", []))
        if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
            origin = headers.get(b"origin", b"").decode()
            cookie_auth = b"access_token=" in headers.get(
                b"cookie", b""
            ) or b"refresh_token=" in headers.get(b"cookie", b"")
            if (origin and origin not in settings.cors_origins_list) or (
                cookie_auth and not origin
            ):
                return await JSONResponse(
                    {"code": "ERR_FORBIDDEN", "message": "请求来源不受信任"}, 403
                )(scope, receive, send)
        max_bytes = settings.REQUEST_BODY_MAX_SIZE_MB * 1024 * 1024
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse(
                {"code": "ERR_VALIDATION", "message": "无效的 Content-Length"}, 400
            )(scope, receive, send)
        if declared < 0 or declared > max_bytes:
            return await JSONResponse({"code": "ERR_VALIDATION", "message": "请求体过大"}, 413)(
                scope, receive, send
            )
        ip = scope.get("client", ("unknown",))[0]
        identities = [f"ip:{ip}"]  # Do not trust arbitrary X-Forwarded-For headers.
        auth = headers.get(b"authorization", b"").decode()
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth[7:])
                if payload.get("type") == "access":
                    identities.append(f"user:{payload['sub']}")
            except Exception:
                pass  # Authentication is still enforced by the endpoint.
        login = scope["path"] in ("/api/v1/auth/login", "/api/v1/auth/register")
        limit = settings.LOGIN_RATE_LIMIT_PER_MINUTE if login else settings.RATE_LIMIT_PER_MINUTE
        bucket = int(time.time()) // 60
        retry_after = str(60 - int(time.time()) % 60)
        try:
            redis = await get_redis()
            for identity in identities:
                hashed = hashlib.sha256(identity.encode()).hexdigest()
                count = await redis.eval(
                    LIMIT_SCRIPT, 1, f"ratelimit:{'auth' if login else 'api'}:{hashed}:{bucket}"
                )
                if count > limit:
                    return await JSONResponse(
                        {"code": "ERR_RATE_LIMITED", "message": "请求过于频繁，请稍后重试"},
                        429,
                        headers={"Retry-After": retry_after},
                    )(scope, receive, send)
        except Exception:
            if settings.is_production:
                return await JSONResponse(
                    {"code": "ERR_SERVICE_UNAVAILABLE", "message": "限流服务不可用"}, 503
                )(scope, receive, send)
            structlog.get_logger(__name__).warning(
                "rate_limit_unavailable", environment=settings.ENVIRONMENT
            )
        # Buffer bounded bodies so chunked transfer cannot bypass the size limit.
        packets = []
        if scope["method"] in ("POST", "PUT", "PATCH"):
            size = 0
            while True:
                packet = await receive()
                if packet["type"] == "http.disconnect":
                    return
                packets.append(packet)
                size += len(packet.get("body", b""))
                if size > max_bytes:
                    return await JSONResponse(
                        {"code": "ERR_VALIDATION", "message": "请求体过大"}, 413
                    )(scope, receive, send)
                if not packet.get("more_body", False):
                    break

        async def replay():
            if packets:
                return packets.pop(0)
            return await receive()

        return await self.app(scope, replay, send)
