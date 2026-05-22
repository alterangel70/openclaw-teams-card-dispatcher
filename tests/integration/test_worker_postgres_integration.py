from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.dispatch import AdaptiveCardDispatch, DispatchStatus
from app.repositories.dispatch_repository import DispatchRepository
from app.services.delivery_client import DeliveryResult
from app.services.dispatch_service import DispatchProcessingService


class SuccessDeliveryClient:
    def send_adaptive_card(self, **_kwargs) -> DeliveryResult:
        return DeliveryResult(success=True, message_id="itest-activity-1")


class FailureDeliveryClient:
    def __init__(self, retriable: bool) -> None:
        self._retriable = retriable

    def send_adaptive_card(self, **_kwargs) -> DeliveryResult:
        return DeliveryResult(success=False, error_message="itest failure", retriable=self._retriable)


@pytest.mark.integration
def test_worker_processing_success_with_real_postgres(integration_session) -> None:
    """Validate worker processing success path using real PostgreSQL repository operations."""

    repository = DispatchRepository()
    correlation_id = f"itest-worker-success-{int(datetime.now(timezone.utc).timestamp())}"

    repository.create_pending_dispatch(
        integration_session,
        correlation_id=correlation_id,
        team_id="team-itest",
        channel_id="channel-itest",
        conversation_id="conversation-itest",
        reply_to_message_id="reply-itest",
        adaptive_card={"type": "AdaptiveCard", "version": "1.4", "body": []},
    )
    integration_session.commit()

    service = DispatchProcessingService(
        integration_session,
        repository,
        delivery_client=SuccessDeliveryClient(),
        max_retries=3,
    )

    processed_count = service.process_pending_batch(batch_size=10)

    assert processed_count == 1
    row = integration_session.query(AdaptiveCardDispatch).filter_by(correlation_id=correlation_id).one()
    assert row.status == DispatchStatus.SENT
    assert row.retry_count == 0
    assert row.graph_message_id == "itest-activity-1"
    assert row.sent_at is not None


@pytest.mark.integration
def test_worker_processing_failed_after_max_retries_with_real_postgres(integration_session) -> None:
    """Validate failed transition when max retries are exhausted."""

    repository = DispatchRepository()
    correlation_id = f"itest-worker-failed-{int(datetime.now(timezone.utc).timestamp())}"

    dispatch = repository.create_pending_dispatch(
        integration_session,
        correlation_id=correlation_id,
        team_id="team-itest",
        channel_id="channel-itest",
        conversation_id="conversation-itest",
        reply_to_message_id="reply-itest",
        adaptive_card={"type": "AdaptiveCard", "version": "1.4", "body": []},
    )
    dispatch.retry_count = 2
    integration_session.commit()

    service = DispatchProcessingService(
        integration_session,
        repository,
        delivery_client=FailureDeliveryClient(retriable=True),
        max_retries=3,
    )

    processed_count = service.process_pending_batch(batch_size=10)

    assert processed_count == 1
    row = integration_session.query(AdaptiveCardDispatch).filter_by(correlation_id=correlation_id).one()
    assert row.status == DispatchStatus.FAILED
    assert row.retry_count == 3
    assert row.last_error is not None
