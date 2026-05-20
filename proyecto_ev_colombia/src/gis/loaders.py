from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.generation_locations import apply_generation_location_overrides
from src.load_data import read_sql_source_table, read_sql_table_if_exists
from src.project_config import load_yaml_config
from src.territorial import normalize_department_series

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CONFIG_DIR = PROJECT_ROOT / "config"
MAPS_CONFIG_PATH = CONFIG_DIR / "maps.yaml"

PRIORITY_PATH = PROCESSED_DIR / "priorizacion_territorial.csv"
DEMAND_PATH = PROCESSED_DIR / "demanda_energetica.csv"
HYDRAULIC_GEOCODED_PATH = PROCESSED_DIR / "activos_hidraulicos_geocoded.csv"
GENERATION_RAW_PATH = RAW_DIR / "infraestructura_generacion_86_registros.xlsx"
PARATEC_RAW_PATH = RAW_DIR / "PARATEC_Phidráulica_18-05-2026.xlsx"
PRIORITY_TABLE = "priorizacion_territorial"
DEMAND_TABLE = "demanda_energetica"


def _require_sql_result_table(table_name: str) -> pd.DataFrame:
    dataframe = read_sql_table_if_exists(table_name)
    if dataframe is None:
        raise RuntimeError(
            f"La tabla SQL '{table_name}' no existe o no está disponible. Ejecuta el pipeline para materializar resultados en MySQL antes de renderizar mapas."
        )
    return dataframe



def get_maps_config() -> dict:
    return load_yaml_config(MAPS_CONFIG_PATH)



def build_geodataframe_from_coords(
    dataframe: pd.DataFrame,
    lat_col: str = "latitud",
    lon_col: str = "longitud",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    geo_df = dataframe.copy()
    geo_df[lat_col] = pd.to_numeric(geo_df.get(lat_col), errors="coerce")
    geo_df[lon_col] = pd.to_numeric(geo_df.get(lon_col), errors="coerce")
    geo_df = geo_df.dropna(subset=[lat_col, lon_col])
    return gpd.GeoDataFrame(
        geo_df,
        geometry=gpd.points_from_xy(geo_df[lon_col], geo_df[lat_col]),
        crs=crs,
    )



def load_priority_data() -> pd.DataFrame:
    dataframe = _require_sql_result_table(PRIORITY_TABLE)
    dataframe["departamento"] = normalize_department_series(dataframe["departamento"])
    return dataframe



def load_priority_geodataframe() -> gpd.GeoDataFrame:
    dataframe = load_priority_data()
    return build_geodataframe_from_coords(dataframe)



def load_demand_points() -> gpd.GeoDataFrame:
    demand_df = _require_sql_result_table(DEMAND_TABLE)
    demand_df["departamento"] = normalize_department_series(demand_df["departamento"])
    demand_df["anio"] = pd.to_numeric(demand_df["anio"], errors="coerce")
    latest_year = demand_df["anio"].max()
    demand_df = demand_df[demand_df["anio"] == latest_year].copy()

    priority_df = load_priority_data()[["departamento", "latitud", "longitud", "categoria_prioridad", "ranking_prioridad"]]
    merged_df = demand_df.merge(priority_df, on="departamento", how="left")
    return build_geodataframe_from_coords(merged_df)


def load_department_yearly_demand_data() -> pd.DataFrame:
    demand_df = _require_sql_result_table(DEMAND_TABLE)
    demand_df["departamento"] = normalize_department_series(demand_df["departamento"])
    demand_df["anio"] = pd.to_numeric(demand_df["anio"], errors="coerce")

    yearly_df = (
        demand_df.groupby(["anio", "departamento"], dropna=False)
        .agg(
            cantidad_ev_historica=("cantidad_ev", "sum"),
            cantidad_ev_modelada=("cantidad_ev_modelada", "sum"),
            consumo_energetico=("consumo_energetico", "sum"),
            demanda_futura=("demanda_futura", "sum"),
        )
        .reset_index()
        .sort_values(["departamento", "anio"])
    )

    yearly_df["aumento_demanda"] = (
        yearly_df.groupby("departamento")["demanda_futura"].diff().fillna(0)
    )
    yearly_df["aumento_demanda_pct"] = (
        yearly_df.groupby("departamento")["demanda_futura"].pct_change().replace([pd.NA, pd.NaT], 0)
    )
    yearly_df["aumento_demanda_pct"] = pd.to_numeric(
        yearly_df["aumento_demanda_pct"],
        errors="coerce",
    ).replace([float("inf"), float("-inf")], 0).fillna(0)
    return yearly_df



def load_generation_points() -> gpd.GeoDataFrame:
    dataframe = pd.read_excel(GENERATION_RAW_PATH)
    dataframe.columns = [column.strip().lower().replace(" ", "_") for column in dataframe.columns]
    dataframe = dataframe.rename(columns={"latitud_aprox": "latitud", "longitud_aprox": "longitud"})
    dataframe["departamento"] = normalize_department_series(dataframe["departamento"])
    dataframe = apply_generation_location_overrides(dataframe)
    return build_geodataframe_from_coords(dataframe)



def load_hydraulic_points() -> gpd.GeoDataFrame:
    dataframe = read_sql_source_table("activos_hidraulicos")
    dataframe["departamento"] = normalize_department_series(dataframe["departamento"])
    return build_geodataframe_from_coords(dataframe)



def load_department_boundaries() -> gpd.GeoDataFrame:
    config = get_maps_config()
    boundary_url = config.get("boundaries", {}).get("adm1_geojson_url")
    if not boundary_url:
        raise ValueError("No se encontró una URL de límites ADM1 en config/maps.yaml")

    boundaries = gpd.read_file(boundary_url)
    boundaries["departamento"] = normalize_department_series(boundaries["shapeName"])
    return boundaries


def load_department_metrics_geodataframe() -> gpd.GeoDataFrame:
    boundaries = load_department_boundaries()
    priority_df = load_priority_data()
    merged = boundaries.merge(priority_df, on="departamento", how="left")
    return merged
