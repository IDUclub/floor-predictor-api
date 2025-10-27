"""Abstract protocol for Urban API client is defined here."""

import abc

import geopandas as gpd


class UrbanAPIClient(abc.ABC):
    """Urban API client"""

    @abc.abstractmethod
    def start(self):
        """Start the client session."""

    @abc.abstractmethod
    async def close(self):
        """Close the client session."""

    @abc.abstractmethod
    async def _request(self, method: str, path: str, **kwargs):
        """Perform a request."""

    @abc.abstractmethod
    async def is_alive(self) -> bool:
        """Check if urban_api instance is alive."""

    @abc.abstractmethod
    async def get_version(self) -> str | None:
        """Get API version if appliable."""

    @abc.abstractmethod
    async def get_physical_object_type_id_by_name(self, name: str) -> int:
        """Get physical object function identifier by name."""

    @abc.abstractmethod
    async def get_scenario_living_buildings(self, scenario_id: int, token: str | None) -> gpd.GeoDataFrame:
        """Get living buildings GeoDataFrame by scenario identifier."""
