"""Dispatch ORM model and status enum."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DispatchStatus(str, enum.Enum):
	"""Valid lifecycle states for adaptive card dispatches."""

	PENDING = "PENDING"
	PROCESSING = "PROCESSING"
	SENT = "SENT"
	FAILED = "FAILED"


class AdaptiveCardDispatch(Base):
	"""Persistence model for outgoing adaptive card dispatch requests."""

	__tablename__ = "adaptive_card_dispatches"
	__table_args__ = (
		Index(
			"ix_adaptive_card_dispatches_status_next_attempt_at",
			"status",
			"next_attempt_at",
		),
		Index(
			"ix_adaptive_card_dispatches_status_created_at",
			"status",
			"created_at",
		),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	correlation_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
	team_id: Mapped[str] = mapped_column(String(128), nullable=False)
	channel_id: Mapped[str] = mapped_column(String(128), nullable=False)
	reply_to_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
	adaptive_card_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
	status: Mapped[DispatchStatus] = mapped_column(
		Enum(DispatchStatus, name="dispatch_status"),
		nullable=False,
		default=DispatchStatus.PENDING,
	)
	retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
	graph_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
	next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=func.now(),
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=func.now(),
		onupdate=func.now(),
	)
	sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
