"""Common logic exceptions are defined here."""

from starlette import status

from floor_predictor_api.exceptions import FloorPredictorApiError


class NoBuildingsFoundError(FloorPredictorApiError):
    """Exception to raise when no buildings found in scenario project data."""

    def __str__(self) -> str:
        return "На территории этого проектного сценария не было найдено ни одного здания с отсутствующей этажностью."

    def get_status_code(self) -> int:
        return status.HTTP_404_NOT_FOUND
