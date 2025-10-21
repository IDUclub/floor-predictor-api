"""Api routers are defined here."""

from fastapi import APIRouter

from .v1 import routers_list as v1

system_router = APIRouter(tags=["system"])

routers_list = [
    *v1,
    system_router,
]

__all__ = [
    "routers_list",
]
