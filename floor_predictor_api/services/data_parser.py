"""Data parser interface for Urban API is defined here."""

from abc import ABC, abstractmethod

import geopandas as gpd


class UrbanFeatureParser(ABC):
    """Abstract base class for parsing GeoDataFrames from Urban API features."""

    @abstractmethod
    def parse_buildings(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Converts the GeoDataFrame of buildings to a format suitable for model input.

        Steps:
        1. Extract key attributes:
           - building_id (from building.id)
           - is_scenario_object (from is_scenario_physical_object)
           - storey (from building.floors)
           - is_living (default 1)
        2. Filter out invalid geometries (non-polygonal).
        3. Generate geometric features.
        4. Compute spatial autocorrelation (Moran, LISA).
        5. Add neighborhood metrics.
        6. Split into:
           - df_to_predict (storey is null)
           - df_existing (storey not null)

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Input GeoDataFrame with columns `geometry`, `building`, `is_scenario_physical_object`.

        Returns
        -------
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]
            (df_to_predict, df_existing)
        """
