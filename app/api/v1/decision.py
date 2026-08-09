from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from app.api.deps import DBSession
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.decision import DecisionRequest, DecisionResponse, DecisionTraceResponse
from app.models.decision_result import DecisionResult
from app.services.decision_service import DecisionService
from app.core.exceptions import AppException

router = APIRouter(prefix="/decision")


@router.get("", response_model=PaginatedResponse)
async def list_decisions(
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取决策结果列表（分页）。"""
    total_result = await db.execute(select(func.count()).select_from(DecisionResult))
    total = total_result.scalar() or 0

    query = select(DecisionResult).order_by(DecisionResult.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    data = [_serialize_decision(item) for item in items]
    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.post("/make", response_model=DataResponse)
async def make_decision(request: DecisionRequest, db: DBSession):
    """提交决策请求。"""
    try:
        service = DecisionService(db)
        result = await service.make_decision(request.request_id)
        return DataResponse(data=result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})

@router.get("/{request_id}", response_model=DataResponse)
async def get_decision(request_id: str, db: DBSession):
    """查询决策结果。"""
    service = DecisionService(db)
    result = await service.get_decision(request_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "ERR_NOT_FOUND", "message": "决策结果未找到"})
    return DataResponse(data=result)

@router.get("/{request_id}/trace", response_model=DataResponse)
async def get_decision_trace(request_id: str, db: DBSession):
    """获取决策链路追踪。"""
    service = DecisionService(db)
    trace = await service.get_trace(request_id)
    return DataResponse(data=trace)


def _serialize_decision(item: DecisionResult) -> dict:
    return {
        "id": item.id,
        "request_id": item.request_id,
        "analysis_id": item.analysis_id,
        "decision": item.decision.value if hasattr(item.decision, "value") else item.decision,
        "confidence": item.confidence,
        "explanation": item.explanation,
        "decision_path": item.decision_path,
        "reflection_passed": item.reflection_passed,
        "reviewed_by": item.reviewed_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }