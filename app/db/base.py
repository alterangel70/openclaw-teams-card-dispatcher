"""Declarative base class for SQLAlchemy ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
	"""Base class that all ORM models should inherit from."""

