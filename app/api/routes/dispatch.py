"""Dispatch API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.dispatch_repository import DispatchRepository
from app.schemas.dispatch import DispatchCreateRequest, DispatchResponse
from app.services.dispatch_service import DispatchService

router = APIRouter(prefix="/teams", tags=["dispatch"])
logger = logging.getLogger(__name__)


def get_dispatch_service(session: Session = Depends(get_db_session)) -> DispatchService:
    """Build a dispatch service instance for request handlers."""

    repository = DispatchRepository()
    return DispatchService(session=session, repository=repository)


@router.post(
	"/adaptive-card",
	response_model=DispatchResponse,
	response_model_by_alias=True,
	status_code=status.HTTP_202_ACCEPTED,
)
def create_adaptive_card_dispatch(
    payload: DispatchCreateRequest,
    response: Response,
    service: DispatchService = Depends(get_dispatch_service),
) -> DispatchResponse:
	"""Create a pending dispatch record and enforce idempotency by correlation id."""

	dispatch, created = service.create_or_get_dispatch(payload)
	if not created:
		response.status_code = status.HTTP_200_OK

	logger.info(
		"Dispatch ingestion completed",
		extra={
			"correlation_id": payload.correlation_id,
			"dispatch_id": dispatch.id,
			"status": dispatch.status.value,
			"idempotent_replay": not created,
			"http_status": response.status_code,
		},
	)
	return DispatchResponse.from_model(dispatch)
