import uuid
from sqlalchemy import String, Enum as SAEnum, Float, JSON, ForeignKey, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum

class RuleType(str, enum.Enum):
    CONDITION = "condition"
    ACTION = "action"
    GROUP = "group"

class LogicOp(str, enum.Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

class RuleNode(Base, TimestampMixin):
    __tablename__ = "rule_nodes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("rule_nodes.id", ondelete="CASCADE"), default=None, index=True)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SAEnum(RuleType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    condition_type: Mapped[str | None] = mapped_column(String(50), default=None)
    field_name: Mapped[str | None] = mapped_column(String(100), default=None)
    operator: Mapped[str | None] = mapped_column(String(20), default=None)
    threshold_value: Mapped[str | None] = mapped_column(String(200), default=None)
    logic_op: Mapped[LogicOp] = mapped_column(SAEnum(LogicOp, values_callable=lambda x: [e.value for e in x]), default=LogicOp.AND)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    action: Mapped[str | None] = mapped_column(String(50), default=None)
    action_params: Mapped[dict | None] = mapped_column(JSON, default=None)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    children: Mapped[list["RuleNode"]] = relationship("RuleNode", back_populates="parent", remote_side="RuleNode.id", lazy="selectin")
    parent: Mapped["RuleNode | None"] = relationship("RuleNode", back_populates="children", remote_side="RuleNode.parent_id", lazy="selectin")