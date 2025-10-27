"""Floor predictor service interface is defined here."""

from abc import ABC, abstractmethod
from typing import Any

import geopandas as gpd


class FloorPredictorService(ABC):
    """An abstract interface for predicting the number of floors of buildings."""

    @abstractmethod
    async def predict_buildings_floors_by_scenario_id(
        self, scenario_id: int, token: str
    ) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]]]:
        """
        Full prediction pipeline for buildings in a given scenario.

        Steps:
        1. Retrieve buildings from the Urban API.
        2. Parse buildings GeoDataFrame to extract relevant attributes.
        3. Load the trained model.
        4. Perform storey prediction.
        5. Return GeoDataFrame with predictions and a summary dictionary.

        Args:
            scenario_id: Scenario identifier.
            token: Authentication token.

        Returns:
            A tuple of:
            - GeoDataFrame with predicted storeys.
            - List of dicts with {physical_object_id, storey_before, storey_after}.
        """
