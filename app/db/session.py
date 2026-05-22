"""Database engine and session management helpers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine():
	"""Create and cache the SQLAlchemy engine instance."""

	settings = get_settings()
	return create_engine(settings.database_url, pool_pre_ping=True)


SessionLocal = sessionmaker(
	bind=get_engine(),
	autocommit=False,
	autoflush=False,
	expire_on_commit=False,
	class_=Session,
)


def get_db_session() -> Generator[Session, None, None]:
	"""Provide a scoped database session for request handlers."""

	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()
