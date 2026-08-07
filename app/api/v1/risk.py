import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import DBSession
from app.schemas.common import DataResponse, ErrorResponse
from app.schemas.risk import RiskAnalysisRequest, RiskAnalysisResponse, RiskBatchRequest
from app.services.risk_service import RiskService
from app.core.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/risk")

@router.post("/analyze", response_model=DataResponse, responses={422: {"model": ErrorResponse}})
async def analyze_risk(request: RiskAnalysisRequest, db: DBSession):
    """提交风险评估请求（异步）。"""
    try:
        service = RiskService(db)
        result = await service.analyze(request.raw_data_id, force_reanalyze=request.force_reanalyze)
        return DataResponse(data=result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})

@router.get("/analyze/{request_id}", response_model=DataResponse)
async def get_analysis_result(request_id: str, db: DBSession):
    """查询评估结果。"""
    service = RiskService(db)
    result = await service.get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "ERR_NOT_FOUND", "message": "分析结果未找到"})
    return DataResponse(data=result)

@router.post("/analyze/batch", response_model=DataResponse)
async def batch_analyze(request: RiskBatchRequest, db: DBSession):
    """批量风险评估。"""
    service = RiskService(db)
    results = []
    for raw_data_id in request.raw_data_ids:
        try:
            result = await service.analyze(raw_data_id)
            results.append(result)
        except AppException as e:
            results.append({"raw_data_id": raw_data_id, "error": str(e)})
    return DataResponse(data={"total": len(request.raw_data_ids), "results": results})