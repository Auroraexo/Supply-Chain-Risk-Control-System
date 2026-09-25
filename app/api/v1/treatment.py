"""Risk treatment lifecycle and read-only audit trail."""

from datetime import UTC

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DBSession, DeciderUser
from app.models.audit_event import AuditEvent
from app.models.decision_result import Decision, DecisionResult
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.treatment import TreatmentUpdate

router = APIRouter()
TRANSITIONS = {
    "open": {"open", "in_progress"},
    "in_progress": {"in_progress", "resolved"},
    "resolved": {"in_progress", "resolved", "closed"},
    "closed": {"open"},
}


@router.get("/treatment/owners", response_model=DataResponse)
async def owners(db: DBSession, user: DeciderUser):
    rows = (
        await db.execute(
            select(User.id, User.username).where(User.is_active.is_(True)).order_by(User.username)
        )
    ).all()
    return DataResponse(data=[{"id": row.id, "username": row.username} for row in rows])


def serialize_event(row: AuditEvent) -> dict:
    return {
        "id": row.id,
        "entity_id": row.entity_id,
        "action": row.action,
        "actor": row.actor,
        "before": row.before,
        "after": row.after,
        "comment": row.comment,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/decision/{identifier}/history", response_model=DataResponse)
async def decision_history(identifier: str, db: DBSession, user: CurrentUser):
    row = (
        await db.execute(
            select(DecisionResult).where(
                (DecisionResult.id == identifier) | (DecisionResult.request_id == identifier)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "决策不存在")
    events = (
        (
            await db.execute(
                select(AuditEvent)
                .where(AuditEvent.entity_id == row.id)
                .order_by(AuditEvent.created_at, AuditEvent.id)
            )
        )
        .scalars()
        .all()
    )
    return DataResponse(data=[serialize_event(e) for e in events])


@router.put("/decision/{identifier}/treatment", response_model=DataResponse)
async def update_treatment(identifier: str, req: TreatmentUpdate, db: DBSession, user: DeciderUser):
    row = (
        await db.execute(
            select(DecisionResult)
            .where((DecisionResult.id == identifier) | (DecisionResult.request_id == identifier))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "决策不存在")
    if row.revision != req.revision:
        raise HTTPException(409, "任务已更新，请刷新后重试")
    if req.status not in TRANSITIONS[row.case_status]:
        raise HTTPException(422, "不允许跳过处置或复核步骤")
    if row.case_status == "closed" and user["role"] != "admin":
        raise HTTPException(403, "只有管理员可以重新打开已关闭风险")
    if req.status == "closed" and row.decision in (Decision.PENDING_REVIEW, Decision.ESCALATE):
        raise HTTPException(422, "须先完成决策审核，再关闭风险")
    if not req.comment.strip():
        raise HTTPException(422, "请填写处置说明")
    owner_id = req.owner_id or row.owner_id
    due_at = req.due_at or row.due_at
    if owner_id:
        owner = await db.get(User, owner_id)
        if owner is None or not owner.is_active:
            raise HTTPException(422, "负责人不存在或已禁用")
    resolution = req.resolution if req.resolution is not None else row.resolution
    if req.status != "open" and (not owner_id or not due_at):
        raise HTTPException(422, "处置任务必须有负责人和截止时间")
    if req.status in ("resolved", "closed") and not (resolution or "").strip():
        raise HTTPException(422, "解决和关闭必须填写整改结果及证据")
    before = {
        "status": row.case_status,
        "owner_id": row.owner_id,
        "resolution": row.resolution,
        "due_at": row.due_at.isoformat() if row.due_at else None,
    }
    if due_at and due_at.tzinfo:
        due_at = due_at.astimezone(UTC).replace(tzinfo=None)
    row.case_status, row.owner_id, row.due_at, row.resolution = (
        req.status,
        owner_id,
        due_at,
        resolution,
    )
    row.revision += 1
    after = {
        "status": row.case_status,
        "owner_id": row.owner_id,
        "resolution": row.resolution,
        "due_at": row.due_at.isoformat() if row.due_at else None,
    }
    db.add(
        AuditEvent(
            entity_id=row.id,
            action="treatment.update",
            actor=user["sub"],
            before=before,
            after=after,
            comment=req.comment,
        )
    )
    await db.commit()
    return DataResponse(data={**after, "revision": row.revision})


@router.get("/audit", response_model=PaginatedResponse)
async def audit_log(
    db: DBSession,
    user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = (await db.execute(select(func.count()).select_from(AuditEvent))).scalar_one()
    rows = (
        (
            await db.execute(
                select(AuditEvent)
                .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return PaginatedResponse(
        data=[serialize_event(e) for e in rows], total=total, page=page, page_size=page_size
    )
