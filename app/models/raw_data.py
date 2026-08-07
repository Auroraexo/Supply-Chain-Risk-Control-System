import uuid
from datetime import datetime
from sqlalchemy import String, JSON, Enum as SAEnum, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin
import enum

class RawDataStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    INVALID = "invalid"

class RawData(Base, TimestampMixin):
    __tablename__ = "raw_data"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[RawDataStatus] = mapped_column(SAEnum(RawDataStatus, values_callable=lambda x: [e.value for e in x]), default=RawDataStatus.PENDING)
    quality_score: Mapped[float | None] = mapped_column(Float, default=None)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)