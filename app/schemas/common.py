from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

class BaseResponse(BaseModel):
    code: str = "OK"
    message: str = "success"
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class DataResponse(BaseResponse):
    data: Any = None

class PaginatedResponse(BaseResponse):
    data: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20

class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[dict] = None
    trace_id: Optional[str] = None