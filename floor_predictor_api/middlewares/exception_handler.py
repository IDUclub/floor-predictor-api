"""Exception handling middleware is defined here."""

import itertools
import traceback
from http.client import HTTPException

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from floor_predictor_api.core.logging import get_handler_from_path
from floor_predictor_api.exceptions import FloorPredictorApiError
from floor_predictor_api.prometheus import metrics


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware to handle uncaught exceptions and convert them into HTTP responses.

    If debug is enabled, full stack trace and details are returned.
    Otherwise, only a safe generic error message is exposed.
    In all cases, error metrics are incremented.
    """

    def __init__(self, app: FastAPI, debug: list[bool]):
        """Passing debug as a list with single element is a hack to allow
        changing the value on application startup.
        """
        super().__init__(app)
        self._debug = debug

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            status_code = 500
            if isinstance(exc, (FloorPredictorApiError, HTTPException)):
                status_code = getattr(exc, "status_code", 500)

            # Record metrics
            metrics.ERRORS_COUNTER.labels(
                method=request.method,
                path=get_handler_from_path(request.url.path),
                error_type=type(exc).__name__,
                status_code=status_code,
            ).inc(1)

            if self._debug[0]:
                return JSONResponse(
                    {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "path": request.url.path,
                        "params": request.url.query,
                        "trace": list(
                            itertools.chain.from_iterable(
                                map(lambda x: x.split("\n"), traceback.format_tb(exc.__traceback__))
                            )
                        ),
                    },
                    status_code=status_code,
                )

            return JSONResponse({"detail": str(exc)}, status_code=status_code)
