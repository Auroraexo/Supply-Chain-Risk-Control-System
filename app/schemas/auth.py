"""认证相关 Schema。"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class RegisterRequest(BaseModel):
    """注册请求。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    role: Optional[str] = Field(default="analyst", description="角色（analyst/decider/admin）")


class TokenResponse(BaseModel):
    """Token 响应。"""
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class UserInfoResponse(BaseModel):
    """用户信息响应。"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None