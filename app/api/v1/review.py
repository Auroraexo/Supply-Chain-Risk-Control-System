from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import DBSession, CurrentUser
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.review import ReviewDecision, ReviewResponse
from app.services.decision_service import DecisionService
from app.core.exceptions import AppException

router = APIRouter(prefix="/review")

@router.get("/pending", response_model=PaginatedResponse)
async def get_pending_reviews(db: DBSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    """获取待审核列表。"""
    service = DecisionService(db)
    result = await service.get_pending_reviews(page=page, page_size=page_size)
    return PaginatedResponse(data=result["items"], total=result["total"], page=page, page_size=page_size)

@router.post("/{request_id}/approve", response_model=DataResponse)
async def approve_review(request_id: str, review: ReviewDecision, db: DBSession, user: CurrentUser):
    """审核通过。"""
    try:
        service = DecisionService(db)
        result = await service.submit_review(request_id, "approve", user.get("sub", "unknown"), review.comment)
        return DataResponse(data=result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})

@router.post("/{request_id}/reject", response_model=DataResponse)
async def reject_review(request_id: str, review: ReviewDecision, db: DBSession, user: CurrentUser):
    """审核驳回。"""
    try:
        service = DecisionService(db)
        result = await service.submit_review(request_id, "reject", user.get("sub", "unknown"), review.comment)
        return DataResponse(data=result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})

@router.post("/{request_id}/override", response_model=DataResponse)
async def override_decision(request_id: str, review: ReviewDecision, db: DBSession, user: CurrentUser):
    """人工覆盖决策。"""
    try:
        service = DecisionService(db)
        result = await service.submit_review(request_id, "override", user.get("sub", "unknown"), review.comment, override_decision=review.override_decision)
        return DataResponse(data=result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})