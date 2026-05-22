"""Dispatch route placeholders for upcoming phases."""

from fastapi import APIRouter

router = APIRouter(prefix="/teams", tags=["dispatch"])
