"""Worker loop skeleton for dispatch processing."""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass

from app.config import Settings
from app.db.session import SessionLocal
from app.repositories.dispatch_repository import DispatchRepository
from app.services.dispatch_service import DispatchProcessingService
from app.services.teams_bot_client import TeamsBotClient
from app.services.token_provider import BotTokenProvider

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
    """Run worker polling loop and process pending dispatches in sequential batches."""

    runtime = WorkerRuntime()
    install_signal_handlers(runtime)
    token_provider = BotTokenProvider(settings)
    delivery_client = TeamsBotClient(
        token_provider=token_provider,
        service_url=settings.teams_service_url,
        bot_app_id=settings.bot_app_id,
        bot_name=settings.bot_name,
    )
    repository = DispatchRepository()

    logger.info(
        "Worker started",
        extra={
            "poll_interval_seconds": settings.worker_poll_interval_seconds,
            "batch_size": settings.worker_batch_size,
            "correlation_id": "worker",
        },
    )

    while not runtime.should_stop:
        try:
            with SessionLocal() as session:
                service = DispatchProcessingService(
                    session,
                    repository,
                    delivery_client=delivery_client,
                    max_retries=settings.max_retries,
                )
                processed_count = service.process_pending_batch(batch_size=settings.worker_batch_size)
                logger.info(
                    "Worker cycle complete",
                    extra={
                        "processed_count": processed_count,
                        "correlation_id": "worker",
                    },
                )
        except Exception as exc:
            logger.exception(
                "Worker cycle failed",
                extra={
                    "error": str(exc),
                    "correlation_id": "worker",
                },
            )
        time.sleep(settings.worker_poll_interval_seconds)

    logger.info("Worker stopped gracefully", extra={"correlation_id": "worker"})
