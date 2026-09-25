"""认证 API 路由。

提供用户登录、注册、获取当前用户信息等端点。
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, DBSession
from app.core.redis import get_redis
from app.core.security import decode_token
from app.core.session import rotate_session, set_auth_cookies
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.common import DataResponse, ErrorResponse
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
async def login(credentials: LoginRequest, db: DBSession, response: Response, request: Request):
    """Browser sessions use HttpOnly cookies; non-browser clients may receive bearer tokens."""
    service = AuthService(db)
    result = await service.login(credentials)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    data = result.model_dump()
    if request.headers.get("origin"):
        data.pop("access_token", None)
        data.pop("refresh_token", None)
        data.pop("token_type", None)
    return DataResponse(data=data)


@router.post("/refresh", response_model=DataResponse)
async def refresh(request: Request, response: Response, db: DBSession):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "缺少刷新凭证")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "刷新凭证无效")
    user = await db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise HTTPException(401, "用户不可用")
    claims = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "scopes": AuthService._get_scopes_for_role(user.role),
        "is_active": True,
    }
    access, refresh_token = await rotate_session(token, claims)
    set_auth_cookies(response, access, refresh_token)
    return DataResponse(data={"status": "refreshed"})


@router.post("/logout", response_model=DataResponse)
async def logout(request: Request, response: Response):
    token = request.cookies.get("refresh_token") or request.cookies.get("access_token")
    if token:
        try:
            payload = decode_token(token)
        except HTTPException:
            payload = {}
        if payload.get("sid"):
            await (await get_redis()).delete(f"session:{payload['sid']}")
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return DataResponse(data={"status": "logged_out"})


@router.post(
    "/register",
    response_model=DataResponse,
    responses={
        409: {"model": ErrorResponse, "description": "用户名或邮箱已存在"},
        400: {"model": ErrorResponse, "description": "无效的角色"},
    },
)
async def register(request: RegisterRequest, db: DBSession):
    """公开注册始终创建 analyst；提权必须走管理员用户管理。"""
    service = AuthService(db)
    result = await service.register(request)
    return DataResponse(data=result.model_dump())


@router.get("/me", response_model=DataResponse)
async def get_me(current_user: CurrentUser, db: DBSession):
    """获取当前登录用户信息，支持 HttpOnly 会话或 Bearer Token。"""
    service = AuthService(db)
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    result = await service.get_current_user_info(user_id)
    return DataResponse(data=result.model_dump())
