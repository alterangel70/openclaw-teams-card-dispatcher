from app.config import Settings
from app.workers.dispatch_worker import WorkerRuntime
from app.services.dispatch_service import calculate_retry_delay_seconds


def test_worker_runtime_defaults() -> None:
    runtime = WorkerRuntime()
    assert runtime.should_stop is False


def test_settings_has_worker_poll_interval() -> None:
    settings = Settings()
    assert settings.worker_poll_interval_seconds > 0


def test_retry_delay_helper_has_positive_value() -> None:
    assert calculate_retry_delay_seconds(1) > 0
