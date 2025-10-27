"""All unit tests for UrbanAPIClient are defined here."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import geopandas as gpd
import pytest
from aiohttp import ClientConnectionError, ClientSession

from floor_predictor_api.exceptions.logic.common import NoBuildingsFoundError
from floor_predictor_api.exceptions.services.external import ExternalServiceResponseError
from floor_predictor_api.services.impl.urban_api import HTTPUrbanAPIClient


@pytest.mark.asyncio
async def test_init_adds_http_prefix_and_binds_logger(mocker):
    logger = mocker.MagicMock()
    client = HTTPUrbanAPIClient("localhost:8000", logger=logger)

    assert client._host.startswith("http://")
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_start_and_close_creates_and_closes_session():
    client = HTTPUrbanAPIClient("http://testhost")
    assert client._session is None

    client.start()
    assert isinstance(client._session, ClientSession)

    await client.close()
    assert client._session is None


@pytest.mark.asyncio
async def test_get_session_recreates_if_closed(mocker):
    fake_new_session = MagicMock()
    mocker.patch("floor_predictor_api.services.impl.urban_api.ClientSession", return_value=fake_new_session)

    client = HTTPUrbanAPIClient("http://testhost")
    fake_old = MagicMock(closed=True)
    client._session = fake_old

    s = client._get_session()
    assert s is fake_new_session


@pytest.mark.asyncio
async def test_request_success_json(mocker):
    fake_session = AsyncMock()
    fake_resp = AsyncMock()
    fake_resp.status = 200
    fake_resp.json.return_value = {"ok": True}
    fake_session.request.return_value = fake_resp

    mocker.patch.object(HTTPUrbanAPIClient, "_get_session", return_value=fake_session)

    client = HTTPUrbanAPIClient("http://host")
    result = await client._request("GET", "/path")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_request_failure_logs_and_raises(mocker):
    fake_session = AsyncMock()
    fake_resp = AsyncMock()
    fake_resp.status = 404
    fake_resp.text.return_value = "Not found"
    fake_session.request.return_value = fake_resp
    mocker.patch.object(HTTPUrbanAPIClient, "_get_session", return_value=fake_session)

    client = HTTPUrbanAPIClient("http://host")
    client._logger = AsyncMock()

    with pytest.raises(ExternalServiceResponseError):
        await client._request("GET", "/missing")

    client._logger.aerror.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_alive_success(mocker):
    fake_session = AsyncMock()
    fake_resp = AsyncMock()
    fake_resp.status = 200
    fake_resp.json.return_value = {"message": "Pong!"}
    fake_session.get.return_value = fake_resp
    mocker.patch.object(HTTPUrbanAPIClient, "_get_session", return_value=fake_session)

    client = HTTPUrbanAPIClient("http://host")
    assert await client.is_alive() is True


@pytest.mark.asyncio
async def test_is_alive_timeout(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    client._session = AsyncMock()
    client._session.get.side_effect = asyncio.TimeoutError
    client._logger = AsyncMock()

    result = await client.is_alive()
    assert result is False
    client._logger.awarning.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_alive_connection_error(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    client._session = AsyncMock()
    client._session.get.side_effect = ClientConnectionError
    client._logger = AsyncMock()

    result = await client.is_alive()
    assert result is False
    client._logger.awarning.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_version_works(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    with patch.object(client, "_request", AsyncMock(return_value={"info": {"version": "1.2.3"}})):
        result = await client.get_version()
        assert result == "1.2.3"


@pytest.mark.asyncio
async def test_get_physical_object_type_id_by_name_caching(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    client._types_cache["жилое здание"] = 42

    with patch.object(client, "_request", AsyncMock()) as mock_req:
        result = await client.get_physical_object_type_id_by_name("жилое здание")

    assert result == 42
    mock_req.assert_not_called()


@pytest.mark.asyncio
async def test_get_physical_object_type_id_by_name_request(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    with patch.object(client, "_request", AsyncMock(return_value=[{"physical_object_type_id": 99}])):
        result = await client.get_physical_object_type_id_by_name("жилое здание")
        assert result == 99
        assert "жилое здание" in client._types_cache


@pytest.mark.asyncio
async def test_get_physical_object_type_id_by_name_invalid(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    with patch.object(client, "_request", AsyncMock(return_value=[])):
        with pytest.raises(ValueError):
            await client.get_physical_object_type_id_by_name("нет такого")


@pytest.mark.asyncio
async def test_get_scenario_living_buildings_success(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    fake_features = [{"geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"a": 1}}]

    with (
        patch.object(client, "get_physical_object_type_id_by_name", AsyncMock(return_value=123)),
        patch.object(client, "_request", AsyncMock(return_value={"features": fake_features})),
    ):
        gdf = await client.get_scenario_living_buildings(10, "token")
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 1


@pytest.mark.asyncio
async def test_get_scenario_living_buildings_empty(monkeypatch):
    client = HTTPUrbanAPIClient("http://host")
    with (
        patch.object(client, "get_physical_object_type_id_by_name", AsyncMock(return_value=123)),
        patch.object(client, "_request", AsyncMock(return_value={"features": []})),
    ):
        with pytest.raises(NoBuildingsFoundError):
            await client.get_scenario_living_buildings(10, "token")
