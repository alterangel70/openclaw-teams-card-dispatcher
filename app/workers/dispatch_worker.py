"""Worker loop skeleton for dispatch processing."""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class WorkerRuntime:
    """Runtime control flags for worker loop."""

    should_stop: bool = False


def install_signal_handlers(runtime: WorkerRuntime) -> None:
    """Install SIGINT/SIGTERM handlers for graceful shutdown."""

    def _stop_worker(signum: int, _frame) -> None:
        runtime.should_stop = True
        logger.info(
            "Shutdown signal received",
            extra={"signal": signum, "correlation_id": "worker"},
        )

    signal.signal(signal.SIGINT, _stop_worker)
    signal.signal(signal.SIGTERM, _stop_worker)


def run_dispatch_worker(settings: Settings) -> None:
    """Run the worker polling loop.

    This phase only emits heartbeat logs. Dispatch processing is implemented in later phases.
    """

    runtime = WorkerRuntime()
    install_signal_handlers(runtime)

    logger.info(
        "Worker started",
        extra={
            "poll_interval_seconds": settings.worker_poll_interval_seconds,
            "batch_size": settings.worker_batch_size,
            "correlation_id": "worker",
        },
    )

    while not runtime.should_stop:
        logger.info(
            "Worker heartbeat",
            extra={"correlation_id": "worker"},
        )
        time.sleep(settings.worker_poll_interval_seconds)

    logger.info("Worker stopped gracefully", extra={"correlation_id": "worker"})
