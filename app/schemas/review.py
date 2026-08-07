from typing import Optional
from pydantic import BaseModel, Field

class ReviewDecision(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|override)$")
    comment: Optional[str] = None
    override_decision: Optional[str] = None
    override_confidence: Optional[float] = Field(default=None, ge=0, le=1)

class ReviewResponse(BaseModel):
    request_id: str
    status: str
    reviewed_by: Optional[str] = None
    decision: Optional[str] = None