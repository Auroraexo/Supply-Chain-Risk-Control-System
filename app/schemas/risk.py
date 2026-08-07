from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RiskAnalysisRequest(BaseModel):
    raw_data_id: str = Field(..., description="原始数据ID")
    force_reanalyze: bool = Field(default=False, description="是否强制重新分析")

class RiskAnalysisResponse(BaseModel):
    request_id: str
    status: str  # pending/processing/completed/failed
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    anomaly_tags: Optional[list[str]] = None
    analysis_reasoning: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class RiskBatchRequest(BaseModel):
    raw_data_ids: list[str] = Field(..., min_length=1, max_length=100, description="批量原始数据ID列表")