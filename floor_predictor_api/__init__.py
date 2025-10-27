"""This is a Digital Territories Platform API to access and manipulate basic territories' data."""

__all__ = [
    "app",
    "VERSION",
]

from .__version__ import VERSION
from .fastapi_init import app
