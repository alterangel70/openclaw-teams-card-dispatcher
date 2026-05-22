"""CLI entrypoint to start the dispatcher worker."""

from __future__ import annotations

from app.config import get_settings
from app.logging import configure_logging
from app.workers.dispatch_worker import run_dispatch_worker


def main() -> None:
    """Initialize dependencies and start worker loop."""

    settings = get_settings()
    configure_logging(settings)
    run_dispatch_worker(settings)


if __name__ == "__main__":
    main()
