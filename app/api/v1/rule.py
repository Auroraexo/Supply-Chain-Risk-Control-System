from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import DBSession, AdminUser
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.rule import RuleCreateRequest, RuleUpdateRequest, RuleResponse, RuleTreeResponse, RuleToggleRequest, RuleVersionResponse
from app.services.rule_service import RuleService
from app.core.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/rules")

@router.get("", response_model=PaginatedResponse)
async def get_rules(db: DBSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), is_active: bool | None = None):
    """获取规则列表。"""
    service = RuleService(db)
    rules, total = await service.get_rules(page=page, page_size=page_size, is_active=is_active)
    return PaginatedResponse(data=rules, total=total, page=page, page_size=page_size)

@router.get("/tree", response_model=DataResponse)
async def get_rule_tree(db: DBSession):
    """获取决策树结构。"""
    service = RuleService(db)
    tree = await service.get_tree()
    return DataResponse(data=tree)

@router.post("", response_model=DataResponse, status_code=201)
async def create_rule(rule: RuleCreateRequest, db: DBSession, user: AdminUser):
    """创建规则。"""
    try:
        service = RuleService(db)
        result = await service.create_rule(rule)
        return DataResponse(data=result, message="规则创建成功")
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code.value, "message": e.message, "detail": e.detail})

@router.put("/{rule_id}", response_model=DataResponse)
async def update_rule(rule_id: str, rule: RuleUpdateRequest, db: DBSession, user: AdminUser):
    """更新规则。"""
    try:
        service = RuleService(db)
        result = await service.update_rule(rule_id, rule)
        return DataResponse(data=result, message="规则更新成功")
    except NotFoundException:
        raise HTTPException(status_code=404, detail={"code": "ERR_NOT_FOUND", "message": "规则未找到"})

@router.delete("/{rule_id}", response_model=DataResponse)
async def delete_rule(rule_id: str, db: DBSession, user: AdminUser):
    """软删除规则（禁用）。"""
    service = RuleService(db)
    await service.delete_rule(rule_id)
    return DataResponse(message="规则已删除")

@router.post("/{rule_id}/toggle", response_model=DataResponse)
async def toggle_rule(rule_id: str, toggle: RuleToggleRequest, db: DBSession, user: AdminUser):
    """启用/禁用规则。"""
    service = RuleService(db)
    result = await service.toggle_rule(rule_id, toggle.is_active)
    return DataResponse(data=result)

@router.get("/{rule_id}/versions", response_model=DataResponse)
async def get_rule_versions(rule_id: str, db: DBSession):
    """获取规则版本历史。"""
    service = RuleService(db)
    versions = await service.get_versions(rule_id)
    return DataResponse(data=versions)

@router.post("/{rule_id}/rollback", response_model=DataResponse)
async def rollback_rule(rule_id: str, version: int = Query(..., ge=1), db: DBSession = None, user: AdminUser = None):
    """回滚到指定版本。"""
    service = RuleService(db)
    result = await service.rollback(rule_id, version)
    return DataResponse(data=result)