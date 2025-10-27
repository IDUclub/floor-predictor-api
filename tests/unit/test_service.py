"""All unit tests for FloorPredictorService are defined here."""

from unittest.mock import AsyncMock, MagicMock, patch

import geopandas as gpd
import numpy as np
import pytest

from floor_predictor_api.services.impl.floor_predictor import FloorPredictorServiceImpl


@pytest.mark.asyncio
async def test_predict_buildings_floors_by_scenario_id_success(monkeypatch):
    # --- Arrange ---
    fake_buildings = gpd.GeoDataFrame(
        {
            "building_id": [1, 2],
            "geometry": gpd.points_from_xy([30.3, 30.4], [59.9, 59.8]),
        },
        crs=4326,
    )

    fake_df_to_predict = gpd.GeoDataFrame(
        {
            "building_id": [1],
            "is_scenario_object": [True],
            "geometry": gpd.points_from_xy([30.3], [59.9]),
        },
        crs=4326,
    )

    fake_df_existing = gpd.GeoDataFrame(
        {
            "building_id": [2],
            "is_scenario_object": [False],
            "geometry": gpd.points_from_xy([30.4], [59.8]),
        },
        crs=4326,
    )

    # mock urban_api_client
    mock_client = AsyncMock()
    mock_client.get_scenario_living_buildings.return_value = fake_buildings

    # mock parser
    mock_parser = MagicMock()
    mock_parser.parse_buildings.return_value = (fake_df_to_predict.copy(), fake_df_existing.copy())

    # mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([5.4])  # => округляется до 5

    # mock logger
    mock_logger = AsyncMock()

    # mock load_model (static method)
    with patch(
        "floor_predictor_api.services.impl.floor_predictor.StoreyModelTrainer.load_model",
        return_value=mock_model,
    ):
        service = FloorPredictorServiceImpl(
            urban_api_client=mock_client,
            model_path="fake_model.pkl",
            logger=mock_logger,
            parser=mock_parser,
        )

    # --- Act ---
    result_gdf, summary = await service.predict_buildings_floors_by_scenario_id(99, "token123")

    # --- Assert ---
    mock_client.get_scenario_living_buildings.assert_awaited_once_with(99, "token123")
    mock_parser.parse_buildings.assert_called_once()
    mock_model.predict.assert_called_once()

    # check result_gdf content
    assert isinstance(result_gdf, gpd.GeoDataFrame)
    assert set(result_gdf.columns) >= {"building_id", "geometry", "is_scenario_object"}
    assert "storey" in result_gdf.columns

    # check summary
    assert isinstance(summary, list)
    assert summary[0]["storey"] == 5
    assert summary[0]["building_id"] == 1

    # check async logger call
    mock_logger.ainfo.assert_awaited_once()
    log_call = mock_logger.ainfo.await_args[1]
    assert log_call["scenario_id"] == 99
    assert log_call["predicted_buildings"] == 1


@pytest.mark.asyncio
async def test_parser_raises(monkeypatch):
    """Проверяем, что исключение в парсере пробрасывается наружу."""
    mock_client = AsyncMock()
    mock_client.get_scenario_living_buildings.return_value = gpd.GeoDataFrame()

    mock_parser = MagicMock()
    mock_parser.parse_buildings.side_effect = ValueError("bad data")

    mock_logger = AsyncMock()
    mock_model = MagicMock()

    with patch(
        "floor_predictor_api.services.impl.floor_predictor.StoreyModelTrainer.load_model",
        return_value=mock_model,
    ):
        service = FloorPredictorServiceImpl(mock_client, "fake_model", mock_logger, mock_parser)

    with pytest.raises(ValueError, match="bad data"):
        await service.predict_buildings_floors_by_scenario_id(1, "t")


@pytest.mark.asyncio
async def test_logger_called_even_on_partial_success(monkeypatch):
    """Даже если часть данных пустая, логгер должен вызываться."""
    mock_client = AsyncMock()
    mock_client.get_scenario_living_buildings.return_value = gpd.GeoDataFrame()

    mock_parser = MagicMock()
    mock_parser.parse_buildings.return_value = (
        gpd.GeoDataFrame(columns=["building_id", "is_scenario_object", "geometry"], crs=4326),
        gpd.GeoDataFrame(columns=["building_id", "is_scenario_object", "geometry"], crs=4326),
    )

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([])

    mock_logger = AsyncMock()

    with patch(
        "floor_predictor_api.services.impl.floor_predictor.StoreyModelTrainer.load_model",
        return_value=mock_model,
    ):
        service = FloorPredictorServiceImpl(mock_client, "fake_model", mock_logger, mock_parser)

    await service.predict_buildings_floors_by_scenario_id(3, "t")
    mock_logger.ainfo.assert_awaited_once()
