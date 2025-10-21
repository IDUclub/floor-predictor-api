"""Prediction response schemas are defined here."""

from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel, Field

from floor_predictor_api.schemas.geometries import GeoJSONResponse


class BuildingFloors(BaseModel):
    """Model for building attributes."""

    building_id: int = Field(..., description="building identifier")
    is_scenario_object: bool = Field(..., description="boolean param to determine scenario object")
    is_living: bool = Field(..., description="boolean param to determine living building")
    storey: int | None = Field(..., description="the number of storey after prediction")
    is_predicted: bool = Field(..., description="boolean param to determine building with predicted number of floors")


class PredictionSummary(BaseModel):
    """Model for prediction summary. It is only for buildings with predicted floors."""

    building_id: int = Field(..., description="building identifier")
    is_scenario_object: bool = Field(..., description="boolean param to determine scenario object")
    storey: int | None = Field(..., description="the number of storey after prediction")


class PredictionResult(BaseModel):
    """Model for prediction results including geojson and summary data."""

    geojson: GeoJSONResponse[Feature[Geometry, BuildingFloors]]
    summary: list[PredictionSummary]
