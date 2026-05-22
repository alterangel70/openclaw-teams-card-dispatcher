from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    """Provide integration database URL from environment or skip integration tests."""

    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping integration tests.")
    return database_url


@pytest.fixture(scope="session")
def integration_engine(integration_database_url: str):
    """Create engine for integration tests against a real PostgreSQL database."""

    engine = create_engine(integration_database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot connect to integration database: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture()
def integration_session(integration_engine) -> Iterator[Session]:
    """Provide database session and cleanup integration test rows after each test."""

    local_session = sessionmaker(bind=integration_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = local_session()
    try:
        yield session
    finally:
        # Cleanup only test-generated rows by correlation id prefix.
        session.execute(
            text("DELETE FROM adaptive_card_dispatches WHERE correlation_id LIKE 'itest-%'"),
        )
        session.commit()
        session.close()
