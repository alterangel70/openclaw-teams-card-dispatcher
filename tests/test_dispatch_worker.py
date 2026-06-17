from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.dispatch import DispatchStatus
from app.services.delivery_client import DeliveryResult
from app.services.dispatch_service import DispatchProcessingService, calculate_retry_delay_seconds


@dataclass
class FakeDispatch:
    id: int
    correlation_id: str
    conversation_type: str
    conversation_id: str
    adaptive_card_json: dict
    status: DispatchStatus
    retry_count: int
    team_id: str | None = None
    channel_id: str | None = None
    reply_to_message_id: str | None = None
    last_error: str | None = None
    graph_message_id: str | None = None
    next_attempt_at: datetime | None = None
    sent_at: datetime | None = None


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepository:
    def __init__(self, dispatches: list[FakeDispatch]) -> None:
        self._dispatches = dispatches

    def list_due_pending_dispatches(self, _session, *, now: datetime, limit: int) -> list[FakeDispatch]:
        due = [
            item
            for item in self._dispatches
            if item.status == DispatchStatus.PENDING
            and (item.next_attempt_at is None or item.next_attempt_at <= now)
        ]
        return due[:limit]

    def get_by_id(self, _session, dispatch_id: int) -> FakeDispatch | None:
        for dispatch in self._dispatches:
            if dispatch.id == dispatch_id:
                return dispatch
        return None

    def mark_processing(self, dispatch: FakeDispatch) -> None:
        dispatch.status = DispatchStatus.PROCESSING
        dispatch.last_error = None

    def mark_sent(self, dispatch: FakeDispatch, *, graph_message_id: str, sent_at: datetime) -> None:
        dispatch.status = DispatchStatus.SENT
        dispatch.graph_message_id = graph_message_id
        dispatch.sent_at = sent_at
        dispatch.next_attempt_at = None
        dispatch.last_error = None

    def mark_pending_retry(
        self,
        dispatch: FakeDispatch,
        *,
        retry_count: int,
        next_attempt_at: datetime,
        last_error: str,
    ) -> None:
        dispatch.status = DispatchStatus.PENDING
        dispatch.retry_count = retry_count
        dispatch.next_attempt_at = next_attempt_at
        dispatch.last_error = last_error

    def mark_failed(self, dispatch: FakeDispatch, *, retry_count: int, last_error: str) -> None:
        dispatch.status = DispatchStatus.FAILED
        dispatch.retry_count = retry_count
        dispatch.last_error = last_error
        dispatch.next_attempt_at = None


class SuccessDeliveryClient:
    def send_adaptive_card(self, **_kwargs) -> DeliveryResult:
        return DeliveryResult(success=True, message_id="activity-1")


class FailureDeliveryClient:
    def __init__(self, retriable: bool) -> None:
        self._retriable = retriable

    def send_adaptive_card(self, **_kwargs) -> DeliveryResult:
        return DeliveryResult(success=False, error_message="Delivery failed", retriable=self._retriable)


def _pending_channel_dispatch(retry_count: int = 0) -> FakeDispatch:
    return FakeDispatch(
        id=1,
        correlation_id="corr-1",
        conversation_type="channel",
        team_id="team-1",
        channel_id="channel-1",
        conversation_id="conversation-1",
        reply_to_message_id="msg-1",
        adaptive_card_json={"type": "AdaptiveCard", "version": "1.4"},
        status=DispatchStatus.PENDING,
        retry_count=retry_count,
    )


def _pending_dm_dispatch(retry_count: int = 0) -> FakeDispatch:
    return FakeDispatch(
        id=2,
        correlation_id="corr-dm-1",
        conversation_type="dm",
        conversation_id="8:orgid:user-aad-object-id",
        adaptive_card_json={"type": "AdaptiveCard", "version": "1.4"},
        status=DispatchStatus.PENDING,
        retry_count=retry_count,
    )


# Keep old name as alias so tests that import it externally don't break.
_pending_dispatch = _pending_channel_dispatch


def test_process_pending_batch_marks_sent_on_success() -> None:
    dispatch = _pending_channel_dispatch()
    session = FakeSession()
    repository = FakeRepository([dispatch])
    service = DispatchProcessingService(
        session,
        repository,
        delivery_client=SuccessDeliveryClient(),
        max_retries=3,
    )

    processed = service.process_pending_batch(batch_size=10)

    assert processed == 1
    assert dispatch.status == DispatchStatus.SENT
    assert dispatch.graph_message_id == "activity-1"
    assert dispatch.sent_at is not None


def test_process_pending_batch_marks_sent_for_dm_dispatch() -> None:
    dispatch = _pending_dm_dispatch()
    session = FakeSession()
    repository = FakeRepository([dispatch])
    service = DispatchProcessingService(
        session,
        repository,
        delivery_client=SuccessDeliveryClient(),
        max_retries=3,
    )

    processed = service.process_pending_batch(batch_size=10)

    assert processed == 1
    assert dispatch.status == DispatchStatus.SENT
    assert dispatch.graph_message_id == "activity-1"


def test_process_pending_batch_retries_when_failure_and_retries_left() -> None:
    dispatch = _pending_channel_dispatch(retry_count=1)
    session = FakeSession()
    repository = FakeRepository([dispatch])
    service = DispatchProcessingService(
        session,
        repository,
        delivery_client=FailureDeliveryClient(retriable=True),
        max_retries=3,
    )

    processed = service.process_pending_batch(batch_size=10)

    assert processed == 1
    assert dispatch.status == DispatchStatus.PENDING
    assert dispatch.retry_count == 2
    assert dispatch.last_error is not None
    assert dispatch.next_attempt_at is not None
    assert dispatch.next_attempt_at > datetime.now(timezone.utc) - timedelta(seconds=1)


def test_process_pending_batch_marks_failed_at_max_retries() -> None:
    dispatch = _pending_channel_dispatch(retry_count=2)
    session = FakeSession()
    repository = FakeRepository([dispatch])
    service = DispatchProcessingService(
        session,
        repository,
        delivery_client=FailureDeliveryClient(retriable=False),
        max_retries=3,
    )

    processed = service.process_pending_batch(batch_size=10)

    assert processed == 1
    assert dispatch.status == DispatchStatus.FAILED
    assert dispatch.retry_count == 3
    assert dispatch.next_attempt_at is None
    assert dispatch.last_error is not None


def test_calculate_retry_delay_seconds_exponential_and_capped() -> None:
    assert calculate_retry_delay_seconds(1) == 5
    assert calculate_retry_delay_seconds(2) == 10
    assert calculate_retry_delay_seconds(3) == 20
    assert calculate_retry_delay_seconds(10) == 300
