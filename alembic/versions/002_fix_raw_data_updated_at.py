"""修复 raw_data 表缺少 updated_at 列。"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("raw_data", sa.Column("updated_at", sa.DateTime, default=None))


def downgrade() -> None:
    op.drop_column("raw_data", "updated_at")