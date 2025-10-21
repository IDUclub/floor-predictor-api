"""Prediction endpoints for scenario buildings are defined here."""

from fastapi.params import Depends, Path
from starlette import status
from starlette.requests import Request

from floor_predictor_api.api.v1.routers import project_scenario_router
from floor_predictor_api.core.auth import verify_token
from floor_predictor_api.schemas import GeoJSONResponse, PredictionResult
from floor_predictor_api.schemas.predict import PredictionSummary
from floor_predictor_api.services.floor_predictor import FloorPredictorService


@project_scenario_router.get(
    "/scenarios/{scenario_id}/predict/floors",
    response_model=PredictionResult,
    status_code=status.HTTP_200_OK,
)
async def predict_living_buildings_floors(
    request: Request,
    scenario_id: int = Path(..., description="scenario identifier", gt=0),
    token: str = Depends(verify_token),
) -> PredictionResult:
    """
    ## This method predict floors for each living building in given scenario.
    It returns geojson with living buildings and summary data (list of buildings with predicted floors).

    ### Parameters:
    - **scenario_id** (int, Path): Unique identifier of the scenario.

    ### Returns:
    - **PredictionResult**: Response containing geojson with buildings and summary data.

    ### Errors:
    - **403 Forbidden**: If the user does not have access rights.
    - **404 Not Found**: If the scenario does not exist or buildings were not found.

    ### Constraints:
    - The user must be the project owner.
    """
    floor_predictor_service: FloorPredictorService = request.app.state.floor_predictor_service

    gdf, summary = await floor_predictor_service.predict_buildings_floors_by_scenario_id(scenario_id, token)

    return PredictionResult(
        geojson=await GeoJSONResponse.from_gdf(gdf),
        summary=[PredictionSummary(**building) for building in summary],
    )
