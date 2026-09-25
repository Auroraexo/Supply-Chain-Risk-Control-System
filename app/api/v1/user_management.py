"""用户管理 API 路由。

提供用户列表、创建、更新、删除、角色分配等管理接口（仅 Admin）。
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from app.api.deps import DBSession, AdminUser
from app.schemas.common import DataResponse, PaginatedResponse
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.core.security import hash_password
from app.core.redis import get_redis
from app.models.audit_event import AuditEvent

router = APIRouter(prefix="/users")


@router.get("", response_model=PaginatedResponse)
async def list_users(
    db: DBSession,
    admin: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    search: str | None = None,
):
    """获取用户列表（分页，仅 Admin）。"""
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if search:
        query = query.where(User.username.ilike(f"%{search}%"))
        count_query = count_query.where(User.username.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    data = [_serialize_user(item) for item in items]
    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.post("", response_model=DataResponse, status_code=201)
async def create_user(
    db: DBSession,
    admin: AdminUser,
    username: str = Query(..., min_length=2, max_length=50),
    email: str = Query(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    password: str = Query(..., min_length=6, max_length=128),
    role: str = Query("analyst"),
):
    """创建用户（仅 Admin）。"""
    repo = UserRepository(db)

    existing = await repo.get_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    existing_email = await repo.get_by_email(email)
    if existing_email:
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效角色: {role}")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=user_role,
    )
    user = await repo.create(user)
    db.add(
        AuditEvent(
            entity_id=user.id,
            action="user.create",
            actor=admin["sub"],
            after={"role": user.role.value},
        )
    )
    return DataResponse(data=_serialize_user(user), message="用户创建成功")


@router.put("/{user_id}", response_model=DataResponse)
async def update_user(
    user_id: str,
    db: DBSession,
    admin: AdminUser,
    email: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
):
    """更新用户信息（仅 Admin）。"""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    before = {"email": user.email, "role": user.role.value, "is_active": user.is_active}
    if email is not None:
        existing_email = await repo.get_by_email(email)
        if existing_email and existing_email.id != user_id:
            raise HTTPException(status_code=409, detail="邮箱已被其他用户使用")
        user.email = email

    if role is not None:
        try:
            user.role = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效角色: {role}")

    if is_active is not None:
        user.is_active = is_active

    await db.flush()
    await db.refresh(user)
    if (is_active is False or role is not None) and user_id != admin["sub"]:
        redis = await get_redis()
        async for key in redis.scan_iter("session:*"):
            import json

            value = await redis.get(key)
            if value and json.loads(value).get("sub") == user_id:
                await redis.delete(key)
    db.add(
        AuditEvent(
            entity_id=user.id,
            action="user.update",
            actor=admin["sub"],
            before=before,
            after={"email": user.email, "role": user.role.value, "is_active": user.is_active},
        )
    )
    return DataResponse(data=_serialize_user(user), message="用户更新成功")


@router.delete("/{user_id}", response_model=DataResponse)
async def delete_user(user_id: str, db: DBSession, admin: AdminUser):
    """删除用户（仅 Admin）。"""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user_id == admin["sub"]:
        raise HTTPException(status_code=422, detail="不能删除当前登录账号")

    db.add(
        AuditEvent(
            entity_id=user.id,
            action="user.deactivate",
            actor=admin["sub"],
            before={"role": user.role.value},
        )
    )
    user.is_active = False
    redis = await get_redis()
    async for key in redis.scan_iter("session:*"):
        import json

        value = await redis.get(key)
        if value and json.loads(value).get("sub") == user_id:
            await redis.delete(key)
    await db.flush()
    return DataResponse(message="用户已停用，历史审计记录已保留")


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
