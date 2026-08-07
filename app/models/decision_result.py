import uuid
from sqlalchemy import String, JSON, Float, Enum as SAEnum, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum

class Decision(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    PENDING_REVIEW = "pending_review"

class DecisionResult(Base, TimestampMixin):
    __tablename__ = "decision_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_results.id"), nullable=False)
    decision: Mapped[Decision] = mapped_column(SAEnum(Decision, values_callable=lambda x: [e.value for e in x]), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    decision_path: Mapped[dict | None] = mapped_column(JSON, default=None)
    reflection_passed: Mapped[bool | None] = mapped_column(Boolean, default=None)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), default=None)
    analysis: Mapped["AnalysisResult"] = relationship("AnalysisResult", lazy="selectin")