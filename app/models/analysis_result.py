import uuid
from sqlalchemy import String, JSON, Float, Enum as SAEnum, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AnalysisResult(Base, TimestampMixin):
    __tablename__ = "analysis_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    raw_data_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_data.id"), nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float, default=None)
    risk_level: Mapped[RiskLevel | None] = mapped_column(SAEnum(RiskLevel, values_callable=lambda x: [e.value for e in x]), default=None)
    anomaly_tags: Mapped[dict | None] = mapped_column(JSON, default=None)
    reasoning: Mapped[str | None] = mapped_column(Text, default=None)
    facts_summary: Mapped[dict | None] = mapped_column(JSON, default=None)
    raw_data: Mapped["RawData"] = relationship("RawData", lazy="selectin")