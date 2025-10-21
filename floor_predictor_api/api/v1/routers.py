"""Api routers are defined here."""

from fastapi import APIRouter

project_scenario_router = APIRouter(tags=["scenario"], prefix="/api/v1")

routers_list = [
    project_scenario_router,
]

__all__ = [
    "routers_list",
]
