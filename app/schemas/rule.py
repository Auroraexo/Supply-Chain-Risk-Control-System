from typing import Optional
from pydantic import BaseModel, Field

class RuleConditionSchema(BaseModel):
    field: str
    operator: str
    value: str

class RuleCreateRequest(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., pattern="^(condition|action|group)$")
    parent_id: Optional[str] = None
    condition_type: Optional[str] = None
    field_name: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[str] = None
    logic_op: str = Field(default="AND", pattern="^(AND|OR|NOT)$")
    weight: float = Field(default=1.0, ge=0, le=100)
    action: Optional[str] = None
    action_params: Optional[dict] = None
    priority: int = Field(default=0, ge=0)
    description: Optional[str] = None

class RuleUpdateRequest(RuleCreateRequest):
    pass

class RuleResponse(BaseModel):
    id: str
    rule_name: str
    rule_type: str
    parent_id: Optional[str] = None
    condition_type: Optional[str] = None
    field_name: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[str] = None
    logic_op: str
    weight: float
    action: Optional[str] = None
    priority: int
    is_active: bool
    version: int
    description: Optional[str] = None
    children: list["RuleResponse"] = []

class RuleVersionResponse(BaseModel):
    rule_id: str
    version: int
    snapshot: dict
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    created_at: str

class RuleToggleRequest(BaseModel):
    is_active: bool

class RuleTreeResponse(BaseModel):
    root: RuleResponse