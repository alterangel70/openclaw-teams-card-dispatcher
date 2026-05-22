"""Add conversation_id to adaptive_card_dispatches."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260522_0002"
down_revision = "20260522_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add conversation_id required for bot thread replies."""

    op.add_column(
        "adaptive_card_dispatches",
        sa.Column("conversation_id", sa.String(length=128), nullable=False, server_default=""),
    )
    op.alter_column("adaptive_card_dispatches", "conversation_id", server_default=None)


def downgrade() -> None:
    """Drop conversation_id column."""

    op.drop_column("adaptive_card_dispatches", "conversation_id")
