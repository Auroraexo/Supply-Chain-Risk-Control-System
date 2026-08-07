from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import DBSession
from app.schemas.common import DataResponse
from app.schemas.decision import DecisionRequest, DecisionResponse, DecisionTraceResponse
from app.services.decision_service import DecisionService
from app.core.exceptions import AppException

router = APIRouter(prefix="/decision")

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