"""认证服务。

处理用户登录、注册、Token 生成等业务逻辑。
"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
)
from app.core.config import get_settings
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfoResponse


class AuthService:
    """认证服务。"""

    def __init__(self, db: AsyncSession):
        self._repo = UserRepository(db)
        self._settings = get_settings()

    async def login(self, request: LoginRequest) -> TokenResponse:
        """用户登录。

        Args:
            request: 登录请求

        Returns:
            TokenResponse: 包含 access_token 和 refresh_token

        Raises:
            HTTPException: 用户名或密码错误
        """
        user = await self._repo.get_by_username(request.username)
        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用",
            )

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        await self._repo.db.flush()

        # 生成 Token
        scopes = self._get_scopes_for_role(user.role)
        access_token = create_access_token(
            data={
                "sub": user.id,
                "username": user.username,
                "role": user.role.value,
                "scopes": scopes,
                "is_active": user.is_active,
            }
        )
        refresh_token = create_refresh_token(data={"sub": user.id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register(self, request: RegisterRequest) -> UserInfoResponse:
        """用户注册。

        Args:
            request: 注册请求

        Returns:
            UserInfoResponse: 用户信息

        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = await self._repo.get_by_username(request.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )

        # 检查邮箱是否已存在
        existing_email = await self._repo.get_by_email(request.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被注册",
            )

        # 验证角色
        try:
            role = UserRole(request.role) if request.role else UserRole.ANALYST
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的角色: {request.role}，可选值: analyst, decider, admin",
            )

        user = User(
            username=request.username,
            email=request.email,
            hashed_password=hash_password(request.password),
            role=role,
        )

        user = await self._repo.create(user)

        return UserInfoResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            last_login_at=None,
        )

    async def get_current_user_info(self, user_id: str) -> UserInfoResponse:
        """获取当前用户信息。"""
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )

        return UserInfoResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        )

    @staticmethod
    def _get_scopes_for_role(role: UserRole) -> list[str]:
        """根据角色获取权限范围。"""
        scopes_map = {
            UserRole.ADMIN: ["read", "write", "admin", "agent"],
            UserRole.DECIDER: ["read", "write", "agent"],
            UserRole.ANALYST: ["read", "agent"],
        }
        return scopes_map.get(role, ["read"])