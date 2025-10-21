"""Exceptions connected with external services are defined here."""

from floor_predictor_api.exceptions.base import FloorPredictorApiError


class ExternalServiceResponseError(FloorPredictorApiError):
    """Exception to raise when external service returns http error."""

    def __init__(self, service: str, exc: str, exc_code: int):
        self.service = service
        self.exc = exc
        self.exc_code = exc_code
        super().__init__()

    def __str__(self) -> str:
        return f"Ошибка в ответе внешнего сервиса '{self.service}': {self.exc}"

    def get_status_code(self) -> int:
        """
        Return response error status code.
        """
        return self.exc_code


class ExternalServiceUnavailable(FloorPredictorApiError):
    """Exception to raise when external service is unavailable."""

    def __init__(self, service: str, exc_code: int):
        self.service = service
        self.exc_code = exc_code
        super().__init__()

    def __str__(self) -> str:
        return f"Внешний сервис '{self.service}' недоступен."

    def get_status_code(self) -> int:
        """
        Return '503 SERVICE UNAVAILABLE' status code.
        """
        return self.exc_code
