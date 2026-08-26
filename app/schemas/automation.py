from typing import Optional
from pydantic import BaseModel, Field


class AutoAnalysisRequest(BaseModel):
    max_items: int = Field(default=5, ge=1, le=20, description="单次最多自动分析的原始数据条数")


class AutoReviewRequest(BaseModel):
    confidence_threshold: float = Field(default=0.8, ge=0, le=1, description="AI 自动批准的置信度阈值")


class AutoRulesRequest(BaseModel):
    apply: bool = Field(default=False, description="是否将 AI 建议的规则直接应用到规则树")
