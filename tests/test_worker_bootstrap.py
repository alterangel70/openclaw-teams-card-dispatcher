from app.config import Settings
from app.workers.dispatch_worker import WorkerRuntime
from app.workers.dispatch_worker import log_cycle_result
from app.services.dispatch_service import calculate_retry_delay_seconds


def test_worker_runtime_defaults() -> None:
    runtime = WorkerRuntime()
    assert runtime.should_stop is False


def test_settings_has_worker_poll_interval() -> None:
    settings = Settings()
    assert settings.worker_poll_interval_seconds > 0


def test_retry_delay_helper_has_positive_value() -> None:
    assert calculate_retry_delay_seconds(1) > 0


def test_log_cycle_result_uses_debug_when_idle(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    def fake_debug(message: str, *args, **kwargs):  # noqa: ANN001
        events.append(("debug", message))

    def fake_info(message: str, *args, **kwargs):  # noqa: ANN001
        events.append(("info", message))

    from app.workers import dispatch_worker

    monkeypatch.setattr(dispatch_worker.logger, "debug", fake_debug)
    monkeypatch.setattr(dispatch_worker.logger, "info", fake_info)

    log_cycle_result(0)

    assert events == [("debug", "Worker cycle idle")]


def test_log_cycle_result_uses_info_when_processed(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    def fake_debug(message: str, *args, **kwargs):  # noqa: ANN001
        events.append(("debug", message))

    def fake_info(message: str, *args, **kwargs):  # noqa: ANN001
        events.append(("info", message))

    from app.workers import dispatch_worker

    monkeypatch.setattr(dispatch_worker.logger, "debug", fake_debug)
    monkeypatch.setattr(dispatch_worker.logger, "info", fake_info)

    log_cycle_result(2)

    assert events == [("info", "Worker cycle complete")]
