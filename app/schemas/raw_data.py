from pydantic import BaseModel, Field


class RawDataCreate(BaseModel):
    source_type: str = Field(default="manual", min_length=1, max_length=50)
    source_id: str = Field(default="", max_length=100)
    payload: dict = Field(min_length=1)
