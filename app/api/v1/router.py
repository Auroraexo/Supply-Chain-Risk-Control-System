from fastapi import APIRouter
from app.api.v1 import risk, decision, review, rule

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(risk.router, tags=["风险评估"])
api_router.include_router(decision.router, tags=["决策"])
api_router.include_router(review.router, tags=["人工审核"])
api_router.include_router(rule.router, tags=["规则管理"])