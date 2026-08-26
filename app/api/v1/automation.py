"""AI 自动化编排 API。

为风险分析、决策管理、规则引擎三大模块提供 AI 自动化入口。
"""
from fastapi import APIRouter, HTTPException

from app.api.deps import DBSession, CurrentUser, AdminUser
from app.core.exceptions import AppException
from app.schemas.automation import AutoAnalysisRequest, AutoReviewRequest, AutoRulesRequest
from app.schemas.common import DataResponse
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/automation")


@router.post("/run-analysis", response_model=DataResponse)
async def run_auto_analysis(req: AutoAnalysisRequest, db: DBSession, user: CurrentUser):
    """AI 自动分析：自动捞取待处理原始数据并运行 Agent 分析流水线。"""
    try:
        service = AutomationService(db)
        result = await service.run_auto_analysis(req.max_items)
        return DataResponse(data=result, message="自动分析完成")
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})


@router.post("/run-review", response_model=DataResponse)
async def run_auto_review(req: AutoReviewRequest, db: DBSession, user: CurrentUser):
    """AI 自动审核：按置信度与风险等级自动终局待处理决策。"""
    try:
        service = AutomationService(db)
        result = await service.run_auto_review(req.confidence_threshold)
        return DataResponse(data=result, message="自动审核完成")
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})


@router.post("/run-rules", response_model=DataResponse)
async def run_auto_rules(req: AutoRulesRequest, db: DBSession, user: AdminUser):
    """AI 规则优化：分析历史数据生成规则建议，可选直接应用。"""
    try:
        service = AutomationService(db)
        result = await service.run_auto_rules(req.apply)
        return DataResponse(data=result, message="规则优化完成")
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})
