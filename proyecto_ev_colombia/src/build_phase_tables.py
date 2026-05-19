from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

try:
    from .load_data import read_sql_source_table
    from .project_config import (
        get_forecast_horizons,
        get_simultaneidad,
        get_simultaneidad_scenarios,
        get_weights,
    )
    from .territorial import normalize_department_series
    from .train_temporal_baseline import run_baseline
except ImportError:
    from load_data import read_sql_source_table
    from project_config import (
        get_forecast_horizons,
        get_simultaneidad,
        get_simultaneidad_scenarios,
        get_weights,
    )
    from territorial import normalize_department_series
    from train_temporal_baseline import run_baseline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GEOCODED_PARATEC_PATH = PROCESSED_DIR / "activos_hidraulicos_geocoded.csv"
TEMPORAL_PREDICTIONS_PATH = PROCESSED_DIR / "etapa1_temporal_predicciones.csv"
FORECAST_OUTPUT_PATH = PROCESSED_DIR / "forecast_ev.csv"
DEFAULT_SIMULTANEIDAD = 0.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construye tablas procesadas para ETAPA 1, ETAPA 2 y ETAPA 3."
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Escenario de simultaneidad definido en config/scenarios.yaml.",
    )
    parser.add_argument(
        "--simultaneidad",
        type=float,
        default=None,
        help="Sobrescribe la simultaneidad configurada por escenario.",
    )
    parser.add_argument(
        "--forecast-horizons",
        type=int,
        nargs="+",
        default=None,
        help="Horizontes futuros en anios para proyectar ETAPA 1.",
    )
    return parser.parse_args()


def standardize_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def min_max_scale(series: pd.Series) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_value = numeric_series.min()
    max_value = numeric_series.max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series(0.0, index=series.index)
    return (numeric_series - min_value) / (max_value - min_value)


def load_master_dataset() -> pd.DataFrame:
    dataframe = read_sql_source_table("vehiculos_ev")
    rename_map = {
        "anio_registro": "anio",
        "clase": "tipo_vehiculo",
        "cantidad": "cantidad_ev",
        "capacidad_kwh": "kwh_promedio",
        "potencia_carga_dc_kw": "potencia_carga",
    }
    dataframe = dataframe.rename(columns=rename_map)
    dataframe["departamento"] = normalize_department_series(dataframe["departamento"])
    dataframe["tipo_vehiculo"] = standardize_text(dataframe["tipo_vehiculo"])
    dataframe["anio"] = pd.to_numeric(dataframe["anio"], errors="coerce")
    dataframe["cantidad_ev"] = pd.to_numeric(dataframe["cantidad_ev"], errors="coerce").fillna(0)
    dataframe["kwh_promedio"] = pd.to_numeric(dataframe.get("kwh_promedio"), errors="coerce")
    dataframe["potencia_carga"] = pd.to_numeric(dataframe.get("potencia_carga"), errors="coerce")
    dataframe["consumo_wh_km"] = pd.to_numeric(dataframe.get("consumo_wh_km"), errors="coerce")
    return dataframe


def build_temporal_table(master_df: pd.DataFrame) -> pd.DataFrame:
    temporal_df = (
        master_df.groupby(["anio", "departamento", "tipo_vehiculo"], dropna=False)
        .agg(
            cantidad_ev=("cantidad_ev", "sum"),
            kwh_promedio=("kwh_promedio", "mean"),
            potencia_carga=("potencia_carga", "mean"),
            consumo_wh_km=("consumo_wh_km", "mean"),
        )
        .reset_index()
        .sort_values(["anio", "departamento", "tipo_vehiculo"])
    )
    return temporal_df


def build_energy_table(temporal_df: pd.DataFrame, simultaneidad: float) -> pd.DataFrame:
    energy_df = temporal_df.copy()
    energy_df["anio_base"] = pd.NA
    energy_df["horizonte_anios"] = pd.NA
    if TEMPORAL_PREDICTIONS_PATH.exists():
        predictions_df = pd.read_csv(TEMPORAL_PREDICTIONS_PATH)
        join_columns = ["anio", "departamento", "tipo_vehiculo"]
        prediction_columns = join_columns + ["cantidad_ev_pred"]
        predictions_df = predictions_df[prediction_columns].drop_duplicates()
        energy_df = energy_df.merge(predictions_df, on=join_columns, how="left")
        energy_df["cantidad_ev_modelada"] = energy_df["cantidad_ev_pred"].fillna(energy_df["cantidad_ev"])
        energy_df["fuente_cantidad_ev"] = energy_df["cantidad_ev_pred"].notna().map(
            {True: "forecast_baseline", False: "historico"}
        )
    else:
        energy_df["cantidad_ev_modelada"] = energy_df["cantidad_ev"]
        energy_df["fuente_cantidad_ev"] = "historico"

    if FORECAST_OUTPUT_PATH.exists():
        forecast_df = pd.read_csv(FORECAST_OUTPUT_PATH)
        future_columns = [
            "anio",
            "departamento",
            "tipo_vehiculo",
            "kwh_promedio",
            "potencia_carga",
            "consumo_wh_km",
            "cantidad_ev_pred",
            "anio_base",
            "horizonte_anios",
        ]
        future_df = forecast_df[future_columns].drop_duplicates().copy()
        future_df["cantidad_ev"] = 0.0
        future_df["cantidad_ev_modelada"] = future_df["cantidad_ev_pred"]
        future_df["fuente_cantidad_ev"] = "forecast_futuro"
        energy_df = pd.concat([energy_df, future_df], ignore_index=True, sort=False)

    energy_df["simultaneidad"] = simultaneidad
    energy_df["kwh_promedio"] = energy_df["kwh_promedio"].fillna(0)
    energy_df["potencia_carga"] = energy_df["potencia_carga"].fillna(0)
    energy_df["consumo_energetico"] = energy_df["cantidad_ev_modelada"] * energy_df["kwh_promedio"]
    energy_df["demanda_futura"] = (
        energy_df["cantidad_ev_modelada"] * energy_df["potencia_carga"] * energy_df["simultaneidad"]
    )
    energy_df["consumo_energetico_kwh"] = energy_df["consumo_energetico"]
    energy_df["demanda_futura_kw"] = energy_df["demanda_futura"]
    return energy_df


def build_energy_sensitivity_table(
    energy_df: pd.DataFrame,
    simultaneidad_scenarios: dict[str, float],
) -> pd.DataFrame:
    scenario_frames: list[pd.DataFrame] = []
    base_columns = [
        "anio",
        "anio_base",
        "horizonte_anios",
        "departamento",
        "tipo_vehiculo",
        "cantidad_ev",
        "cantidad_ev_modelada",
        "fuente_cantidad_ev",
        "kwh_promedio",
        "potencia_carga",
        "consumo_wh_km",
        "consumo_energetico",
        "consumo_energetico_kwh",
    ]

    for scenario_name, scenario_simultaneidad in simultaneidad_scenarios.items():
        scenario_df = energy_df[base_columns].copy()
        scenario_df["escenario_simultaneidad"] = scenario_name
        scenario_df["simultaneidad"] = float(scenario_simultaneidad)
        scenario_df["demanda_futura"] = (
            scenario_df["cantidad_ev_modelada"]
            * scenario_df["potencia_carga"]
            * scenario_df["simultaneidad"]
        )
        scenario_df["demanda_futura_kw"] = scenario_df["demanda_futura"]
        scenario_frames.append(scenario_df)

    if not scenario_frames:
        return pd.DataFrame()

    return pd.concat(scenario_frames, ignore_index=True, sort=False)


def load_hydraulic_layer() -> pd.DataFrame:
    dataframe = read_sql_source_table("activos_hidraulicos")
    dataframe["departamento"] = normalize_department_series(dataframe["departamento"])
    dataframe["municipio"] = standardize_text(dataframe.get("municipio", pd.Series(dtype="string")))
    dataframe["latitud"] = pd.to_numeric(dataframe.get("latitud"), errors="coerce")
    dataframe["longitud"] = pd.to_numeric(dataframe.get("longitud"), errors="coerce")
    dataframe["capacidad_hidraulica"] = pd.to_numeric(dataframe.get("capacidad_hidraulica"), errors="coerce")
    return dataframe


def build_gis_table(
    energy_df: pd.DataFrame,
    hydraulic_df: pd.DataFrame,
    weights: dict[str, float],
) -> pd.DataFrame:
    target_year = int(pd.to_numeric(energy_df["anio"], errors="coerce").max())
    energy_snapshot_df = energy_df[energy_df["anio"] == target_year].copy()

    energy_dept_df = (
        energy_snapshot_df.groupby("departamento", dropna=False)
        .agg(
            anio_min=("anio", "min"),
            anio_max=("anio", "max"),
            cantidad_ev=("cantidad_ev", "sum"),
            cantidad_ev_modelada=("cantidad_ev_modelada", "sum"),
            consumo_energetico=("consumo_energetico", "sum"),
            demanda_futura=("demanda_futura", "sum"),
        )
        .reset_index()
    )

    hydraulic_dept_df = (
        hydraulic_df.groupby("departamento", dropna=False)
        .agg(
            total_activos_hidraulicos=("nombre_activo", "count"),
            capacidad_hidraulica_total=("capacidad_hidraulica", "sum"),
            latitud_hidraulica_promedio=("latitud", "mean"),
            longitud_hidraulica_promedio=("longitud", "mean"),
        )
        .reset_index()
    )

    gis_df = energy_dept_df.merge(hydraulic_dept_df, on="departamento", how="left")
    gis_df["latitud"] = gis_df["latitud_hidraulica_promedio"]
    gis_df["longitud"] = gis_df["longitud_hidraulica_promedio"]

    numeric_fill_columns = [
        "total_activos_hidraulicos",
        "capacidad_hidraulica_total",
        "latitud_hidraulica_promedio",
        "longitud_hidraulica_promedio",
    ]
    for column in numeric_fill_columns:
        if column in gis_df.columns:
            gis_df[column] = pd.to_numeric(gis_df[column], errors="coerce").fillna(0)

    gis_df["criterio_demanda"] = min_max_scale(gis_df["demanda_futura"])
    gis_df["criterio_crecimiento_ev"] = min_max_scale(gis_df["cantidad_ev_modelada"])
    gis_df["criterio_soporte_hidraulico"] = min_max_scale(gis_df["capacidad_hidraulica_total"])
    gis_df["criterio_cobertura_hidraulica"] = min_max_scale(gis_df["total_activos_hidraulicos"])
    gis_df["criterio_brecha_soporte_hidraulico"] = 1 - gis_df["criterio_soporte_hidraulico"]
    gis_df["criterio_brecha_cobertura_hidraulica"] = 1 - gis_df["criterio_cobertura_hidraulica"]

    gis_df["indice_prioridad_territorial"] = (
        weights["demanda"] * gis_df["criterio_demanda"]
        + weights["crecimiento_ev"] * gis_df["criterio_crecimiento_ev"]
        + weights["soporte_hidraulico"] * gis_df["criterio_brecha_soporte_hidraulico"]
        + weights["cobertura_hidraulica"] * gis_df["criterio_brecha_cobertura_hidraulica"]
    )
    gis_df["ranking_prioridad"] = gis_df["indice_prioridad_territorial"].rank(
        ascending=False,
        method="dense",
    ).astype(int)

    gis_df["categoria_prioridad"] = "MEDIA"
    gis_df.loc[gis_df["indice_prioridad_territorial"] >= 0.66, "categoria_prioridad"] = "ALTA"
    gis_df.loc[gis_df["indice_prioridad_territorial"] < 0.33, "categoria_prioridad"] = "BAJA"
    gis_df["anio_escenario"] = target_year
    gis_df["escenario_energetico_base"] = "medio"

    gis_df["observacion_prioridad"] = "Prioridad balanceada"
    gis_df.loc[
        (gis_df["criterio_demanda"] >= 0.66)
        & (gis_df["criterio_brecha_soporte_hidraulico"] >= 0.66),
        "observacion_prioridad",
    ] = "Alta demanda proyectada y brecha de soporte hidraulico"
    gis_df.loc[
        (gis_df["criterio_demanda"] >= 0.66)
        & (gis_df["criterio_brecha_cobertura_hidraulica"] >= 0.66),
        "observacion_prioridad",
    ] = "Alta demanda proyectada y baja cobertura hidraulica"
    gis_df.loc[
        (gis_df["criterio_demanda"] < 0.33)
        & (gis_df["criterio_crecimiento_ev"] < 0.33),
        "observacion_prioridad",
    ] = "Presion territorial baja en el escenario base"

    gis_df = gis_df.sort_values(
        ["ranking_prioridad", "departamento"],
        ascending=[True, True],
    ).reset_index(drop=True)
    return gis_df


def build_gis_validation_table(gis_df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    validation_df = gis_df.copy()
    validation_df["peso_demanda"] = float(weights["demanda"])
    validation_df["peso_crecimiento_ev"] = float(weights["crecimiento_ev"])
    validation_df["peso_brecha_soporte_hidraulico"] = float(weights["soporte_hidraulico"])
    validation_df["peso_brecha_cobertura_hidraulica"] = float(weights["cobertura_hidraulica"])
    validation_df["sin_soporte_hidraulico"] = validation_df["capacidad_hidraulica_total"].fillna(0).eq(0)
    validation_df["sin_cobertura_hidraulica"] = validation_df["total_activos_hidraulicos"].fillna(0).eq(0)
    validation_df["consistencia_territorial_ok"] = (
        (validation_df["indice_prioridad_territorial"] <= 0.33)
        | (validation_df["criterio_demanda"] >= 0.10)
        | (validation_df["criterio_crecimiento_ev"] >= 0.10)
    )
    columns = [
        "departamento",
        "anio_escenario",
        "escenario_energetico_base",
        "ranking_prioridad",
        "categoria_prioridad",
        "indice_prioridad_territorial",
        "demanda_futura",
        "consumo_energetico",
        "cantidad_ev_modelada",
        "capacidad_hidraulica_total",
        "total_activos_hidraulicos",
        "criterio_demanda",
        "criterio_crecimiento_ev",
        "criterio_soporte_hidraulico",
        "criterio_cobertura_hidraulica",
        "criterio_brecha_soporte_hidraulico",
        "criterio_brecha_cobertura_hidraulica",
        "peso_demanda",
        "peso_crecimiento_ev",
        "peso_brecha_soporte_hidraulico",
        "peso_brecha_cobertura_hidraulica",
        "sin_soporte_hidraulico",
        "sin_cobertura_hidraulica",
        "consistencia_territorial_ok",
        "observacion_prioridad",
    ]
    return validation_df[columns]


def save_temporal_outputs(temporal_df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    temporal_df.to_csv(PROCESSED_DIR / "etapa1_temporal.csv", index=False)
    temporal_df.to_csv(PROCESSED_DIR / "temporal_model_input.csv", index=False)


def save_outputs(
    temporal_df: pd.DataFrame,
    energy_df: pd.DataFrame,
    energy_sensitivity_df: pd.DataFrame,
    gis_validation_df: pd.DataFrame,
    gis_df: pd.DataFrame,
) -> None:
    save_temporal_outputs(temporal_df)
    energy_df.to_csv(PROCESSED_DIR / "etapa2_energetico.csv", index=False)
    energy_df.to_csv(PROCESSED_DIR / "demanda_energetica.csv", index=False)
    if not energy_sensitivity_df.empty:
        energy_sensitivity_df.to_csv(PROCESSED_DIR / "demanda_energetica_escenarios.csv", index=False)
    gis_df.to_csv(PROCESSED_DIR / "etapa3_gis.csv", index=False)
    gis_df.to_csv(PROCESSED_DIR / "priorizacion_territorial.csv", index=False)
    if not gis_validation_df.empty:
        gis_validation_df.to_csv(PROCESSED_DIR / "validacion_etapa3.csv", index=False)

    geo_df = gis_df.dropna(subset=["latitud", "longitud"]).copy()
    if not geo_df.empty:
        geo_df = gpd.GeoDataFrame(
            geo_df,
            geometry=gpd.points_from_xy(geo_df["longitud"], geo_df["latitud"]),
            crs="EPSG:4326",
        )
        geo_df.to_file(PROCESSED_DIR / "priorizacion_territorial.geojson", driver="GeoJSON")


def run_pipeline(
    simultaneidad: float = DEFAULT_SIMULTANEIDAD,
    forecast_horizons: list[int] | None = None,
) -> None:
    master_df = load_master_dataset()
    temporal_df = build_temporal_table(master_df)
    save_temporal_outputs(temporal_df)
    run_baseline(forecast_horizons=get_forecast_horizons(forecast_horizons))
    energy_df = build_energy_table(temporal_df, simultaneidad=simultaneidad)
    energy_sensitivity_df = build_energy_sensitivity_table(
        energy_df,
        simultaneidad_scenarios=get_simultaneidad_scenarios(),
    )
    hydraulic_df = load_hydraulic_layer()
    weights = get_weights()
    gis_df = build_gis_table(energy_df, hydraulic_df, weights=weights)
    gis_validation_df = build_gis_validation_table(gis_df, weights=weights)
    save_outputs(temporal_df, energy_df, energy_sensitivity_df, gis_validation_df, gis_df)


def main() -> None:
    args = parse_args()
    run_pipeline(
        simultaneidad=get_simultaneidad(args.scenario, override=args.simultaneidad),
        forecast_horizons=get_forecast_horizons(args.forecast_horizons),
    )
    print("Tablas procesadas generadas en data/processed:")
    print("- etapa1_temporal.csv")
    print("- etapa2_energetico.csv")
    print("- etapa3_gis.csv")


if __name__ == "__main__":
    main()
