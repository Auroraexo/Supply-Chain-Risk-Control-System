"""Revocable Redis sessions and atomically rotated refresh tokens."""

import json
import uuid

from fastapi import HTTPException, Response

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import create_access_token, create_refresh_token, decode_token

ROTATE_SCRIPT = """
local old = redis.call('GET', KEYS[1])
if not old then return 0 end
local session = cjson.decode(old)
if session.refresh_id ~= ARGV[1] then return 0 end
session.refresh_id = ARGV[2]
redis.call('SET', KEYS[1], cjson.encode(session), 'EX', ARGV[3])
return 1
"""


def token_pair(claims: dict, sid: str, refresh_id: str) -> tuple[str, str]:
    return (
        create_access_token({**claims, "sid": sid}),
        create_refresh_token({"sub": claims["sub"], "sid": sid, "jti": refresh_id}),
    )


async def new_session(claims: dict) -> tuple[str, str]:
    sid, refresh_id = uuid.uuid4().hex, uuid.uuid4().hex
    redis = await get_redis()
    await redis.set(
        f"session:{sid}",
        json.dumps({"sub": claims["sub"], "refresh_id": refresh_id}),
        ex=get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return token_pair(claims, sid, refresh_id)


async def rotate_session(token: str, claims: dict) -> tuple[str, str]:
    payload = decode_token(token)
    if (
        payload.get("type") != "refresh"
        or payload.get("sub") != claims["sub"]
        or not payload.get("sid")
        or not payload.get("jti")
    ):
        raise HTTPException(401, "刷新凭证无效")
    refresh_id = uuid.uuid4().hex
    redis = await get_redis()
    rotated = await redis.eval(
        ROTATE_SCRIPT,
        1,
        f"session:{payload['sid']}",
        payload["jti"],
        refresh_id,
        get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    if not rotated:
        raise HTTPException(401, "刷新凭证已使用或会话已撤销")
    return token_pair(claims, payload["sid"], refresh_id)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )
