"""Delivery abstraction for channel-specific outbound messaging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DeliveryResult:
    """Normalized result for outbound adaptive card delivery."""

    success: bool
    message_id: str | None = None
    error_message: str | None = None
    retriable: bool = False


class DeliveryClient(Protocol):
    """Port for sending adaptive cards through a concrete channel implementation."""

    def send_adaptive_card(
        self,
        *,
        conversation_type: str,
        conversation_id: str,
        adaptive_card: dict,
        team_id: str | None = None,
        channel_id: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> DeliveryResult:
        """Send adaptive card and return a normalized delivery result."""
