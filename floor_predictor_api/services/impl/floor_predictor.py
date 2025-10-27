"""Floor-Predictor service implementation is defined here."""

import asyncio
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import structlog
from floor_predictior.osm_height_predictor.geo import StoreyModelTrainer

from floor_predictor_api.services.data_parser import UrbanFeatureParser
from floor_predictor_api.services.floor_predictor import FloorPredictorService
from floor_predictor_api.services.impl.data_parser import UrbanFeatureParserImpl
from floor_predictor_api.services.urban_api import UrbanAPIClient


class FloorPredictorServiceImpl(FloorPredictorService):
    """Floor predictor that combines Urban API data retrieval, preprocessing, and model inference."""

    def __init__(
        self,
        urban_api_client: UrbanAPIClient,
        model_path: str,
        logger: structlog.BoundLogger,
        parser: UrbanFeatureParser | None = None,
    ):
        """
        Initialize the FloorPredictorServiceImpl.

        Args:
            urban_api_client: Instance of HTTPUrbanAPIClient for data retrieval.
            model_path: Path to the trained model file.
            parser: Optional UrbanFeatureParserImpl instance for preprocessing.
        """
        self.urban_api_client = urban_api_client
        self.parser = parser or UrbanFeatureParserImpl()
        self.model = StoreyModelTrainer.load_model(model_path)
        self._logger = logger

    async def predict_buildings_floors_by_scenario_id(
        self, scenario_id: int, token: str
    ) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]]]:
        # 1. Retrieve raw building data
        buildings = await self.urban_api_client.get_scenario_living_buildings(scenario_id, token)

        # 2. Preprocess using the injected parser
        df_to_predict, df_existing = await asyncio.to_thread(self.parser.parse_buildings, buildings)

        # 3. Predict number of floors
        predictions = self.model.predict(df_to_predict)
        df_to_predict["storey"] = pd.Series(np.rint(predictions), index=df_to_predict.index).astype("Int64")

        # 4. Build result GeoDataFrame
        result_gdf = pd.concat([df_existing, df_to_predict], ignore_index=True)
        result_gdf = result_gdf.set_geometry("geometry").to_crs(4326)

        # 5. Build summary (only predicted floors with building info)
        summary = df_to_predict[["building_id", "is_scenario_object", "storey"]].to_dict(orient="records")

        await self._logger.ainfo(
            "predicted building floors for scenario",
            scenario_id=scenario_id,
            total_buildings=len(result_gdf),
            predicted_buildings=len(df_to_predict),
        )

        return result_gdf, summary
