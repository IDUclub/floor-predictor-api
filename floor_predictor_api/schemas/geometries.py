"""Pydantic geometry schemas are defined here."""

import asyncio
from typing import Any, Literal, TypeVar

import geopandas as gpd
import shapely.geometry as geom
from geojson_pydantic import Feature, FeatureCollection
from pydantic import BaseModel

# Generic typing
T = TypeVar("T", bound=BaseModel)

_BaseGeomTypes = geom.Point | geom.Polygon | geom.MultiPolygon

PointCoords = tuple[float, float]
PolygonCoords = list[list[PointCoords]]
MultiPolygonCoords = list[PolygonCoords]


class Geometry(BaseModel):
    """Geometry representation for GeoJSON model appliable for polygons and multipolygons."""

    type: Literal["Point", "Polygon", "MultiPolygon"]
    coordinates: PointCoords | PolygonCoords | MultiPolygonCoords

    @classmethod
    def from_shapely_geometry(cls, geometry: _BaseGeomTypes | None) -> "Geometry":
        """Construct Geometry model from shapely geometry."""
        if geometry is None:
            return None
        return cls(**geom.mapping(geometry))


class GeoJSONResponse(FeatureCollection):
    """GeoJSON representation."""

    type: Literal["FeatureCollection"] = "FeatureCollection"

    @classmethod
    async def from_gdf(cls, gdf: gpd.GeoDataFrame) -> "GeoJSONResponse":
        """Construct GeoJSON model from GeoDataFrame."""

        def build_sync():
            features = [
                Feature(
                    type="Feature",
                    geometry=geometry,
                    properties=props,
                )
                for geometry, props in zip(gdf.geometry, gdf.drop(columns="geometry").to_dict(orient="records"))
            ]
            return cls(features=features)

        return await asyncio.to_thread(build_sync)

    @classmethod
    async def from_list(cls, data: list[dict[str, Any]]) -> "GeoJSONResponse":
        """Construct GeoJSON model from a list of dictionaries."""

        def build_sync() -> "GeoJSONResponse":
            features = [
                Feature(
                    type="Feature",
                    geometry=item["geometry"],
                    properties=item["properties"],
                )
                for item in data
            ]
            return cls(features=features)

        return await asyncio.to_thread(build_sync)
