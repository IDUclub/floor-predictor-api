"""All unit tests for UrbanFeatureParser are defined here."""

from unittest.mock import MagicMock

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from floor_predictor_api.exceptions.logic.common import NoBuildingsFoundError
from floor_predictor_api.services.impl.data_parser import UrbanFeatureParserImpl


def _init_mock_df(mock_obj, df):
    """Присваивает df в мок и возвращает сам мок (чтобы поведение имитировало конструктор)."""
    mock_obj.df = df
    return mock_obj


@pytest.fixture
def mock_dependencies(monkeypatch):
    """Подменяем все вычислительные классы на моки, чтобы не тянуть их логику."""
    mock_geo = MagicMock()
    mock_geo.compute_geometry_features.side_effect = lambda: mock_geo.df

    mock_stats = MagicMock()
    mock_stats.compute_moran_and_lisa.side_effect = lambda col=None: (mock_stats.df, None, None)

    mock_analyzer = MagicMock()
    mock_analyzer.compute_neighborhood_metrics.side_effect = lambda **kwargs: (mock_analyzer.df, None)

    prefix = "floor_predictor_api.services.impl.data_parser"
    monkeypatch.setattr(f"{prefix}.GeometryFeatureGenerator", lambda df: _init_mock_df(mock_geo, df))
    monkeypatch.setattr(f"{prefix}.SpatialStatisticsComputer", lambda df: _init_mock_df(mock_stats, df))
    monkeypatch.setattr(f"{prefix}.SpatialNeighborhoodAnalyzer", lambda df: _init_mock_df(mock_analyzer, df))

    return mock_geo, mock_stats, mock_analyzer


@pytest.fixture
def sample_gdf():
    """Простая тестовая GeoDataFrame."""
    return gpd.GeoDataFrame(
        [
            {
                "building": {"id": 1, "floors": 5},
                "is_scenario_physical_object": True,
                "geometry": Polygon([(0, 0), (0, 1), (1, 1), (1, 0)]),
            },
            {
                "building": {"id": 2, "floors": None},
                "is_scenario_physical_object": False,
                "geometry": Polygon([(1, 1), (1, 2), (2, 2), (2, 1)]),
            },
        ],
        crs=4326,
    )


def test_parse_buildings_basic(sample_gdf, mock_dependencies):
    """Проверяем, что парсер корректно разбивает на df_to_predict и df_existing."""
    parser = UrbanFeatureParserImpl()
    df_to_predict, df_existing = parser.parse_buildings(sample_gdf)

    # Проверяем колонки
    expected_cols = ["building_id", "storey", "is_scenario_object", "is_living", "is_predicted", "geometry"]
    assert all(col in df_to_predict.columns for col in expected_cols)
    assert all(col in df_existing.columns for col in expected_cols)

    # Проверяем значения
    assert df_existing["building_id"].tolist() == [1]
    assert df_existing["storey"].tolist() == [5]
    assert df_existing["is_predicted"].tolist() == [1]

    assert df_to_predict["building_id"].tolist() == [2]
    assert df_to_predict["storey"].isna().all()
    assert df_to_predict["is_predicted"].tolist() == [0]


def test_parse_buildings_invalid_geometry(sample_gdf, mock_dependencies):
    """Проверяем, что неверные геометрии фильтруются."""
    sample_gdf.at[0, "geometry"] = None
    parser = UrbanFeatureParserImpl()
    df_to_predict, df_existing = parser.parse_buildings(sample_gdf)

    # Остался только один объект
    assert len(df_to_predict) + len(df_existing) == 1


def test_parse_buildings_no_building_id(mock_dependencies):
    """Если нет building_id — вызывается NoBuildingsFoundError."""
    gdf = gpd.GeoDataFrame([{"building": None, "is_scenario_physical_object": True, "geometry": Polygon()}])
    parser = UrbanFeatureParserImpl()

    with pytest.raises(NoBuildingsFoundError):
        parser.parse_buildings(gdf)


def test_parse_buildings_no_valid_geometries(mock_dependencies):
    """Если нет валидных геометрий — тоже ошибка."""
    gdf = gpd.GeoDataFrame(
        [{"building": {"id": 1, "floors": 2}, "is_scenario_physical_object": True, "geometry": None}]
    )
    parser = UrbanFeatureParserImpl()
    with pytest.raises(NoBuildingsFoundError):
        parser.parse_buildings(gdf)


def test_parse_buildings_no_to_predict(mock_dependencies):
    """Если нет объектов без storey — ошибка."""
    gdf = gpd.GeoDataFrame(
        [
            {
                "building": {"id": 1, "floors": 3},
                "is_scenario_physical_object": True,
                "geometry": Polygon([(0, 0), (0, 1), (1, 1), (1, 0)]),
            },
        ],
        crs=4326,
    )
    parser = UrbanFeatureParserImpl()
    with pytest.raises(NoBuildingsFoundError):
        parser.parse_buildings(gdf)
