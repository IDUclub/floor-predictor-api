"""FastAPI application initialization is performed here."""
import asyncio
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from floor_predictor_api.__version__ import LAST_UPDATE, VERSION
from floor_predictor_api.api import list_of_routers
from floor_predictor_api.core.config import Config
from floor_predictor_api.core.logging import configure_logging
from floor_predictor_api.middlewares.exception_handler import ExceptionHandlerMiddleware
from floor_predictor_api.middlewares.logging import LoggingMiddleware
from floor_predictor_api.prometheus import server as prometheus_server
from floor_predictor_api.services.impl.floor_predictor import FloorPredictorServiceImpl
from floor_predictor_api.services.impl.urban_api import make_urban_api_client
from floor_predictor_api.utils.minio import download_model_from_minio


def bind_routes(application: FastAPI, prefix: str) -> None:
    """Bind all routes to application."""
    for router in list_of_routers:
        if len(router.routes) > 0:
            application.include_router(router, prefix=(prefix if "/" not in {r.path for r in router.routes} else ""))


def get_app(prefix: str = "") -> FastAPI:
    """Create application and all dependable objects."""

    app_config: Config = Config.from_file_or_default(os.getenv("CONFIG_PATH"))

    description = "This API provides methods to predict the number of floors for living buildings."

    application = FastAPI(
        title="Floor Predictor API",
        description=description,
        docs_url=None,
        openapi_url=f"{prefix}/openapi",
        version=f"{VERSION} ({LAST_UPDATE})",
        terms_of_service="http://swagger.io/terms/",
        contact={"email": "idu@itmo.ru"},
        license_info={"name": "Apache 2.0", "url": "http://www.apache.org/licenses/LICENSE-2.0.html"},
        lifespan=lifespan,
    )
    bind_routes(application, prefix)

    @application.get(f"{prefix}/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui.css",
        )

    origins = ["*"]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.state.config = app_config

    application.add_middleware(
        LoggingMiddleware,
    )
    application.add_middleware(
        ExceptionHandlerMiddleware,
        debug=[False],  # reinitialized on startup
    )

    return application


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Lifespan function.

    Initializes logger, urban API client and main service.
    """
    app_config: Config = application.state.config

    loggers_dict = {logger_config.filename: logger_config.level for logger_config in app_config.logging.files}
    logger = configure_logging(app_config.logging.level, loggers_dict)
    application.state.logger = logger

    for middleware in application.user_middleware:
        if middleware.cls == ExceptionHandlerMiddleware:
            middleware.kwargs["debug"][0] = app_config.app.debug

    with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as temp_file:
        model_tmp_path = temp_file.name

    await asyncio.to_thread(download_model_from_minio, app_config.fileserver, model_tmp_path)
    await logger.ainfo("Model downloaded to temporary file", path=model_tmp_path)

    urban_api_client = make_urban_api_client(
        host=app_config.urban_api.host,
        ping_timeout_seconds=app_config.urban_api.ping_timeout_seconds,
        operation_timeout_seconds=app_config.urban_api.operation_timeout_seconds,
        logger=logger,
    )

    floor_predictor_service = FloorPredictorServiceImpl(
        urban_api_client=urban_api_client,
        model_path=model_tmp_path,
        logger=logger,
    )
    application.state.floor_predictor_service = floor_predictor_service

    if not app_config.prometheus.disable:
        prometheus_server.start_server(port=app_config.prometheus.port)

    yield

    await urban_api_client.close()

    if os.path.exists(model_tmp_path):
        os.remove(model_tmp_path)

    if not app_config.prometheus.disable:
        prometheus_server.stop_server()


app = get_app()
