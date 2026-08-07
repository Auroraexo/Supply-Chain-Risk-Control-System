from collections.abc import AsyncGenerator
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_active_user

# 数据库会话依赖
DBSession = Annotated[AsyncSession, Depends(get_db)]

# 当前用户依赖
CurrentUser = Annotated[dict, Depends(get_current_active_user)]

# 管理员权限依赖
async def get_admin_user(current_user: CurrentUser) -> dict:
    if "admin" not in current_user.get("scopes", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user

AdminUser = Annotated[dict, Depends(get_admin_user)]