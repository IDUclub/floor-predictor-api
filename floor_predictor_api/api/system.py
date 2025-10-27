"""System endpoints are defined here."""

import fastapi
from starlette import status

from floor_predictor_api.schemas import PingResponse

from .routers import system_router


@system_router.get("/", status_code=status.HTTP_307_TEMPORARY_REDIRECT, include_in_schema=False)
@system_router.get("/api/", status_code=status.HTTP_307_TEMPORARY_REDIRECT, include_in_schema=False)
async def redirect_to_swagger_docs():
    """Redirects to **/docs** from **/**"""
    return fastapi.responses.RedirectResponse("/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@system_router.get(
    "/health_check/ping",
    response_model=PingResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """Return health check response."""
    return PingResponse()
