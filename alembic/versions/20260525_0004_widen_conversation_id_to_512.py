"""Widen conversation_id column from VARCHAR(128) to VARCHAR(512).

Bot Framework a:... DM conversation IDs for Teams personal chats can exceed
128 characters.  VARCHAR(512) provides sufficient headroom for all known
Teams conversation ID formats.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525_0004"
down_revision = "20260525_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Widen conversation_id to VARCHAR(512)."""

    op.alter_column(
        "adaptive_card_dispatches",
        "conversation_id",
        type_=sa.String(length=512),
        existing_type=sa.String(length=128),
        nullable=False,
    )


def downgrade() -> None:
    """Revert conversation_id to VARCHAR(128)."""

    op.alter_column(
        "adaptive_card_dispatches",
        "conversation_id",
        type_=sa.String(length=128),
        existing_type=sa.String(length=512),
        nullable=False,
    )
