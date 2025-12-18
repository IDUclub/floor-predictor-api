"""Urban API HTTP Client is defined here."""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any

import geopandas as gpd
import structlog.stdlib
from aiohttp import ClientConnectionError, ClientResponse, ClientSession, ClientTimeout
from starlette import status

from floor_predictor_api.exceptions.logic.common import NoBuildingsFoundError
from floor_predictor_api.exceptions.services.external import ExternalServiceResponseError, ExternalServiceUnavailable
from floor_predictor_api.services.urban_api import UrbanAPIClient


def make_urban_api_client(
    host: str,
    *,
    ping_timeout_seconds: float = 2.0,
    operation_timeout_seconds: float = 120.0,
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__),
) -> UrbanAPIClient:
    """Get HTTP Urban API client."""

    client = HTTPUrbanAPIClient(
        host,
        ping_timeout_seconds=ping_timeout_seconds,
        operation_timeout_seconds=operation_timeout_seconds,
        logger=logger,
    )
    client.start()
    return client


def _handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions."""

    @wraps(func)
    async def _wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClientConnectionError as exc:
            raise ExternalServiceUnavailable("Urban API", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except asyncio.exceptions.TimeoutError as exc:
            raise ExternalServiceUnavailable("Urban API", status.HTTP_504_GATEWAY_TIMEOUT) from exc

    return _wrapper


class HTTPUrbanAPIClient(UrbanAPIClient):
    """Urban API client that uses HTTP/HTTPS as transport."""

    def __init__(
        self,
        host: str,
        *,
        ping_timeout_seconds: float = 2.0,
        operation_timeout_seconds: float = 60.0,
        logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__),
    ):
        if logger is ...:
            logger = structlog.get_logger()
        if not host.startswith("http"):
            logger.warning("http/https schema is not set, defaulting to http")
            host = f"http://{host.rstrip('/')}/"

        self._host = host
        self._logger = logger.bind(host=self._host)
        self._ping_timeout = ping_timeout_seconds
        self._operation_timeout = operation_timeout_seconds

        self._session: ClientSession | None = None
        self._types_cache: dict = {}

    # --- Context management --------------------------------------------------

    async def __aenter__(self):
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def start(self):
        self._session = ClientSession(base_url=self._host, timeout=ClientTimeout(self._operation_timeout))
        return self

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    # --- Internal helpers ----------------------------------------------------

    def _get_session(self) -> ClientSession:
        """Get client session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(base_url=self._host, timeout=ClientTimeout(self._operation_timeout))
        return self._session

    async def _request(self, method: str, path: str, **kwargs) -> list[Any] | dict[str, Any]:
        session = self._get_session()
        resp: ClientResponse = await session.request(method, path, **kwargs)

        if resp.status in (200, 201):
            return await resp.json()

        await self._logger.aerror(f"request failed: {method} {path}", status=resp.status, text=await resp.text())
        raise ExternalServiceResponseError("Urban API", await resp.text(), resp.status)

    # --- Public API ----------------------------------------------------------

    async def is_alive(self) -> bool:
        try:
            session = self._get_session()
            resp = await session.get("health_check/ping", timeout=ClientTimeout(self._ping_timeout))
            if resp.status == 200 and (await resp.json()) == {"message": "Pong!"}:
                return True
            await self._logger.awarning("error on ping", resp_code=resp.status, resp_text=await resp.text())
        except ClientConnectionError as exc:
            await self._logger.awarning("error on ping", error=repr(exc))
        except asyncio.exceptions.TimeoutError:
            await self._logger.awarning("timeout on ping")
        return False

    @_handle_exceptions
    async def get_version(self) -> str:
        resp = await self._request("GET", "api/openapi")
        return resp["info"]["version"]

    @_handle_exceptions
    async def get_physical_object_type_id_by_name(self, name: str) -> int:
        if name in self._types_cache:
            return self._types_cache[name]

        params = {"name": name}
        resp = await self._request("GET", "api/v1/physical_object_types", params=params)

        if len(resp) != 1:
            raise ValueError(f"No unique physical object type with name `{name}` found.")

        type_id = resp[0]["physical_object_type_id"]
        self._types_cache[name] = type_id
        return type_id

    @_handle_exceptions
    async def get_scenario_living_buildings(self, scenario_id: int, token: str) -> gpd.GeoDataFrame:
        type_id = await self.get_physical_object_type_id_by_name("жилой дом")

        headers = {"Authorization": f"Bearer {token}"}
        params = {"physical_object_type_id": type_id}
        resp = await self._request(
            "GET",
            f"api/v1/scenarios/{scenario_id}/physical_objects_with_geometry",
            params=params,
            headers=headers,
        )

        features = resp.get("features", [])
        if not features:
            raise NoBuildingsFoundError()

        return gpd.GeoDataFrame.from_features(features, crs=4326)
