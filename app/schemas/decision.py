from typing import Optional
from pydantic import BaseModel, Field

class DecisionRequest(BaseModel):
    request_id: str = Field(..., description="风险评估请求ID")

class DecisionResponse(BaseModel):
    request_id: str
    decision: str  # approve/reject/escalate/pending_review
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    decision_path: Optional[list[str]] = None
    reflection_passed: Optional[bool] = None
    reviewed_by: Optional[str] = None

class DecisionTraceResponse(BaseModel):
    request_id: str
    trace: list[dict]  # 各节点输入输出
    total_latency_ms: Optional[int] = None
    total_tokens: Optional[int] = None