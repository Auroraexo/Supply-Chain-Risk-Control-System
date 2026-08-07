"""认证 API 路由。

提供用户登录、注册、获取当前用户信息等端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import DBSession, CurrentUser
from app.schemas.common import DataResponse, ErrorResponse
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfoResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post(
    "/login",
    response_model=DataResponse,
    responses={
        401: {"model": ErrorResponse, "description": "用户名或密码错误"},
        403: {"model": ErrorResponse, "description": "用户已被禁用"},
    },
)
async def login(request: LoginRequest, db: DBSession):
    """用户登录，获取 JWT Token。

    返回 access_token 和 refresh_token。
    access_token 在后续请求中通过 Authorization: Bearer <token> 头传递。
    """
    service = AuthService(db)
    result = await service.login(request)
    return DataResponse(data=result.model_dump())


@router.post(
    "/register",
    response_model=DataResponse,
    responses={
        409: {"model": ErrorResponse, "description": "用户名或邮箱已存在"},
        400: {"model": ErrorResponse, "description": "无效的角色"},
    },
)
async def register(request: RegisterRequest, db: DBSession):
    """用户注册。

    默认角色为 analyst，可指定为 analyst/decider/admin。
    """
    service = AuthService(db)
    result = await service.register(request)
    return DataResponse(data=result.model_dump())


@router.get("/me", response_model=DataResponse)
async def get_me(current_user: CurrentUser, db: DBSession):
    """获取当前登录用户信息。

    需要在请求头中携带 Authorization: Bearer <token>。
    """
    service = AuthService(db)
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    result = await service.get_current_user_info(user_id)
    return DataResponse(data=result.model_dump())