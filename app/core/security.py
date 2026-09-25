"""认证与安全模块。

提供 JWT Token 创建/验证、密码哈希、RBAC 权限依赖。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt

from app.core.config import get_settings

# === 密码哈希 ===


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def hash_password(password: str) -> str:
    """哈希密码。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# === OAuth2 配置 ===
oauth2_scheme = OAuth2PasswordBearer(
    auto_error=False,
    tokenUrl="/api/v1/auth/login",
    scopes={
        "read": "读取权限",
        "write": "写入权限",
        "admin": "管理员权限",
        "agent": "Agent 调用权限",
    },
)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT Access Token。"""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """创建 JWT Refresh Token。"""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """解码并验证 JWT Token。"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    security_scopes: SecurityScopes,
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """获取当前认证用户（FastAPI 依赖）。

    使用方式：
        @router.get("/me")
        async def get_me(user: dict = Depends(get_current_user)):
            ...
    """
    token = token or request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "请先登录")
    payload = decode_token(token)
    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="需要有效的 Access Token")
    from app.core.redis import get_redis
    import json

    sid = payload.get("sid")
    session = await (await get_redis()).get(f"session:{sid}") if sid else None
    if not session or json.loads(session).get("sub") != payload["sub"]:
        raise HTTPException(401, "会话已失效，请重新登录")

    # 验证 scope
    token_scopes = payload.get("scopes", [])
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 scope: {scope}",
            )

    return payload


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """获取当前活跃用户（额外检查用户状态）。"""
    from app.core.database import get_session_factory
    from app.models.user import User

    async with get_session_factory()() as session:
        user = await session.get(User, current_user["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    from app.services.auth_service import AuthService

    current_user.update(
        role=user.role.value, scopes=AuthService._get_scopes_for_role(user.role), is_active=True
    )
    return current_user
