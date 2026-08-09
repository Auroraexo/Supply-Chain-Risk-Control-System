import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import DBSession
from app.schemas.common import DataResponse, ErrorResponse, PaginatedResponse
from app.schemas.risk import RiskAnalysisRequest, RiskAnalysisResponse, RiskBatchRequest
from app.models.analysis_result import AnalysisResult
from app.services.risk_service import RiskService
from app.core.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/risk")

@router.get("/analyze", response_model=PaginatedResponse)
async def list_analysis_results(
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取分析结果列表（分页）。"""
    total_result = await db.execute(select(func.count()).select_from(AnalysisResult))
    total = total_result.scalar() or 0

    query = select(AnalysisResult).order_by(AnalysisResult.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    data = [_serialize_analysis(item) for item in items]
    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


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


def _serialize_analysis(item: AnalysisResult) -> dict:
    return {
        "id": item.id,
        "request_id": item.request_id,
        "raw_data_id": item.raw_data_id,
        "risk_score": item.risk_score,
        "risk_level": item.risk_level.value if hasattr(item.risk_level, "value") else item.risk_level,
        "anomaly_tags": item.anomaly_tags,
        "reasoning": item.reasoning,
        "facts_summary": item.facts_summary,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }