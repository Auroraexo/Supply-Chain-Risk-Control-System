import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    PENDING_REVIEW = "pending_review"


class DecisionResult(Base, TimestampMixin):
    __tablename__ = "decision_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_results.id"), nullable=False
    )
    decision: Mapped[Decision] = mapped_column(
        SAEnum(Decision, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    decision_path: Mapped[dict | None] = mapped_column(JSON, default=None)
    reflection_passed: Mapped[bool | None] = mapped_column(Boolean, default=None)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), default=None)
    case_status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolution: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analysis: Mapped["AnalysisResult"] = relationship("AnalysisResult", lazy="selectin")
