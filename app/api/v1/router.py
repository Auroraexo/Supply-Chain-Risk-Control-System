from fastapi import APIRouter
from app.api.v1 import risk, decision, review, rule, auth, dashboard, raw_data_crud, user_management

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, tags=["认证"])
api_router.include_router(risk.router, tags=["风险评估"])
api_router.include_router(decision.router, tags=["决策"])
api_router.include_router(review.router, tags=["人工审核"])
api_router.include_router(rule.router, tags=["规则管理"])
api_router.include_router(dashboard.router, tags=["仪表盘"])
api_router.include_router(raw_data_crud.router, tags=["原始数据"])
api_router.include_router(user_management.router, tags=["用户管理"])