"""Health check endpoint."""

import structlog
from fastapi import APIRouter

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", summary="Health check", tags=["health"])
def health() -> dict:
    """Always returns HTTP 200 with status ok."""
    return {"status": "ok"}
