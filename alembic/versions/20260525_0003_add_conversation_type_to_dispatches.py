"""Add conversation_type and make channel-only fields nullable."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525_0003"
down_revision = "20260522_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add conversation_type column and relax NOT NULL on channel-only fields."""

    op.add_column(
        "adaptive_card_dispatches",
        sa.Column(
            "conversation_type",
            sa.String(length=16),
            nullable=False,
            server_default="channel",
        ),
    )
    op.alter_column("adaptive_card_dispatches", "conversation_type", server_default=None)

    # team_id, channel_id and reply_to_message_id are irrelevant for DM dispatches.
    op.alter_column("adaptive_card_dispatches", "team_id", nullable=True)
    op.alter_column("adaptive_card_dispatches", "channel_id", nullable=True)
    op.alter_column("adaptive_card_dispatches", "reply_to_message_id", nullable=True)


def downgrade() -> None:
    """Revert nullable relaxation and drop conversation_type column."""

    # Re-fill NULLs with empty string before restoring NOT NULL constraint.
    op.execute(
        "UPDATE adaptive_card_dispatches SET team_id = '' WHERE team_id IS NULL"
    )
    op.execute(
        "UPDATE adaptive_card_dispatches SET channel_id = '' WHERE channel_id IS NULL"
    )
    op.execute(
        "UPDATE adaptive_card_dispatches"
        " SET reply_to_message_id = '' WHERE reply_to_message_id IS NULL"
    )

    op.alter_column("adaptive_card_dispatches", "team_id", nullable=False)
    op.alter_column("adaptive_card_dispatches", "channel_id", nullable=False)
    op.alter_column("adaptive_card_dispatches", "reply_to_message_id", nullable=False)

    op.drop_column("adaptive_card_dispatches", "conversation_type")
