from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TreatmentUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]
    owner_id: str | None = None
    due_at: datetime | None = None
    resolution: str | None = Field(default=None, max_length=10000)
    comment: str = Field(min_length=1, max_length=2000)
    revision: int = Field(ge=0)
