"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    """Always returns 200."""
    return {"status": "ok"}
