"""Create adaptive_card_dispatches table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260522_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create dispatch status enum and adaptive card dispatches table."""

    dispatch_status = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "SENT",
        "FAILED",
        name="dispatch_status",
    )
    dispatch_status.create(op.get_bind(), checkfirst=True)

    dispatch_status_column = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "SENT",
        "FAILED",
        name="dispatch_status",
        create_type=False,
    )

    op.create_table(
        "adaptive_card_dispatches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("team_id", sa.String(length=128), nullable=False),
        sa.Column("channel_id", sa.String(length=128), nullable=False),
        sa.Column("reply_to_message_id", sa.String(length=128), nullable=False),
        sa.Column("adaptive_card_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", dispatch_status_column, nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("graph_message_id", sa.String(length=128), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("correlation_id", name="uq_adaptive_card_dispatches_correlation_id"),
    )

    op.create_index(
        "ix_adaptive_card_dispatches_status_next_attempt_at",
        "adaptive_card_dispatches",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_adaptive_card_dispatches_status_created_at",
        "adaptive_card_dispatches",
        ["status", "created_at"],
    )


def downgrade() -> None:
    """Drop adaptive card dispatches table and dispatch status enum."""

    op.drop_index("ix_adaptive_card_dispatches_status_created_at", table_name="adaptive_card_dispatches")
    op.drop_index("ix_adaptive_card_dispatches_status_next_attempt_at", table_name="adaptive_card_dispatches")
    op.drop_table("adaptive_card_dispatches")

    dispatch_status = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "SENT",
        "FAILED",
        name="dispatch_status",
    )
    dispatch_status.drop(op.get_bind(), checkfirst=True)