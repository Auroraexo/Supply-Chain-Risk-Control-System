from fastapi import APIRouter, Depends
from app.core.security import get_current_active_user
from app.api.v1 import treatment
from app.api.v1 import (
    risk,
    decision,
    review,
    rule,
    auth,
    dashboard,
    raw_data_crud,
    user_management,
    settings,
    automation,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, tags=["认证"])
for module, tag in (
    (risk, "风险评估"),
    (decision, "决策"),
    (review, "人工审核"),
    (rule, "规则管理"),
    (dashboard, "仪表盘"),
    (raw_data_crud, "原始数据"),
    (user_management, "用户管理"),
    (settings, "系统设置"),
    (automation, "AI自动化"),
    (treatment, "风险处置"),
):
    api_router.include_router(
        module.router, tags=[tag], dependencies=[Depends(get_current_active_user)]
    )
