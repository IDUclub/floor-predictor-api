"""Urban API response parser implementation is defined here."""

import geopandas as gpd
import pandas as pd
from floor_predictior.osm_height_predictor.geo import (
    GeometryFeatureGenerator,
    SpatialNeighborhoodAnalyzer,
    SpatialStatisticsComputer,
)

from floor_predictor_api.exceptions.logic.common import NoBuildingsFoundError
from floor_predictor_api.services.data_parser import UrbanFeatureParser


class UrbanFeatureParserImpl(UrbanFeatureParser):
    """Parser that extracts and prepares building features for floor prediction."""

    def parse_buildings(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        df = gdf.copy()

        # --- 1. Extract attributes ---
        df["building_id"] = df["building"].map(lambda b: b.get("id") if isinstance(b, dict) else None)
        df = df[df["building_id"].notna()]
        if df.empty:
            raise NoBuildingsFoundError()

        df["storey"] = df["building"].map(lambda b: b.get("floors") if isinstance(b, dict) else None)
        df["storey"] = pd.to_numeric(df["storey"], errors="coerce").astype("Int64")

        df["is_scenario_object"] = df["is_scenario_physical_object"].astype(int)
        df["is_living"] = 1  # by default
        df["is_predicted"] = df["storey"].notna().astype(int)

        # --- 2. Filter invalid geometries ---
        valid_geom_mask = df.geometry.apply(lambda g: g is not None and g.geom_type in ("Polygon", "MultiPolygon"))
        df = df[valid_geom_mask].reset_index(drop=True)

        if df.empty:
            raise NoBuildingsFoundError()

        df = df[["building_id", "storey", "is_scenario_object", "is_living", "is_predicted", "geometry"]].copy()

        # --- 3. Generate geometry features ---
        geo_gen = GeometryFeatureGenerator(df)
        df = geo_gen.compute_geometry_features()

        # --- 4. Compute spatial statistics ---
        stats = SpatialStatisticsComputer(df)
        df, _, _ = stats.compute_moran_and_lisa(col="storey")

        # --- 5. Analyze spatial neighborhood metrics ---
        analyzer = SpatialNeighborhoodAnalyzer(df)
        df, _ = analyzer.compute_neighborhood_metrics(plot=False, show_progress=False)

        # --- 6. Split by storey ---
        df_to_predict = df[df["storey"].isna()].reset_index(drop=True)
        df_existing = df[df["storey"].notna()].reset_index(drop=True)

        if df_to_predict.empty:
            raise NoBuildingsFoundError()

        return df_to_predict, df_existing
