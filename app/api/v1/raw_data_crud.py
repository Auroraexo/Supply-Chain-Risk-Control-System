"""原始数据 CRUD API 路由。

提供原始数据的管理接口：列表查询、详情、创建、删除。
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func, delete as sa_delete, or_
from sqlalchemy.exc import IntegrityError
from app.api.deps import DBSession, AdminUser
from app.schemas.raw_data import RawDataCreate
from app.models.analysis_result import AnalysisResult
from app.models.audit_event import AuditEvent
from app.schemas.common import DataResponse, PaginatedResponse
from app.models.raw_data import RawData, RawDataStatus

router = APIRouter(prefix="/raw-data")


@router.get("", response_model=PaginatedResponse)
async def list_raw_data(
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    source: str | None = None,
    search: str | None = None,
):
    """获取原始数据列表（分页）。"""
    query = select(RawData)
    count_query = select(func.count()).select_from(RawData)

    if status:
        query = query.where(RawData.status == status)
        count_query = count_query.where(RawData.status == status)
    if source:
        query = query.where(RawData.source_type == source)
        count_query = count_query.where(RawData.source_type == source)
    if search:
        condition = or_(
            RawData.source_type.ilike(f"%{search}%"), RawData.source_id.ilike(f"%{search}%")
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(RawData.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        data=[_serialize_raw_data(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{raw_data_id}", response_model=DataResponse)
async def get_raw_data(raw_data_id: str, db: DBSession):
    """获取原始数据详情。"""
    result = await db.execute(select(RawData).where(RawData.id == raw_data_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=404, detail={"code": "ERR_NOT_FOUND", "message": "原始数据未找到"}
        )
    return DataResponse(data=_serialize_raw_data(item))


@router.post("", response_model=DataResponse, status_code=201)
async def create_raw_data(data: RawDataCreate, db: DBSession):
    """创建原始数据。"""
    import hashlib, json

    payload = data.payload
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    data_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    raw_data = RawData(
        source_type=data.source_type,
        source_id=data.source_id,
        payload=payload,
        data_hash=data_hash,
        status=RawDataStatus.PENDING,
    )
    db.add(raw_data)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "相同载荷已存在，请使用已有原始数据") from exc
    await db.refresh(raw_data)
    return DataResponse(data=_serialize_raw_data(raw_data), message="创建成功")


@router.delete("/{raw_data_id}", response_model=DataResponse)
async def delete_raw_data(raw_data_id: str, db: DBSession, user: AdminUser):
    """删除原始数据。"""
    linked = (
        await db.execute(
            select(func.count())
            .select_from(AnalysisResult)
            .where(AnalysisResult.raw_data_id == raw_data_id)
        )
    ).scalar_one()
    if linked:
        raise HTTPException(409, "数据已有风险分析证据，禁止删除；请使用归档流程")
    try:
        result = await db.execute(sa_delete(RawData).where(RawData.id == raw_data_id))
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "数据已被引用，无法删除") from exc
    await db.flush()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404, detail={"code": "ERR_NOT_FOUND", "message": "原始数据未找到"}
        )
    db.add(AuditEvent(entity_id=raw_data_id, action="raw_data.delete", actor=user["sub"]))
    return DataResponse(message="删除成功")


def _serialize_raw_data(item: RawData) -> dict:
    return {
        "id": item.id,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "payload": item.payload,
        "data_hash": item.data_hash,
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "quality_score": item.quality_score,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "processed_at": item.processed_at.isoformat() if item.processed_at else None,
    }
