from __future__ import annotations

from pathlib import Path
import unicodedata

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
GENERATION_MUNICIPAL_COORDS_PATH = RAW_DIR / "municipios_generacion_coords.csv"
GENERATION_MUNICIPAL_OVERRIDES_PATH = RAW_DIR / "infraestructura_generacion_municipios.csv"


def normalize_text_value(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def normalize_municipality_series(series: pd.Series) -> pd.Series:
    return series.apply(normalize_text_value)


def _normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = dataframe.copy()
    normalized.columns = [column.strip().lower().replace(" ", "_") for column in normalized.columns]
    return normalized


def load_generation_location_overrides() -> pd.DataFrame:
    empty_columns = ["id", "municipio", "latitud", "longitud", "precision_ubicacion", "detalle_ubicacion"]
    if not GENERATION_MUNICIPAL_OVERRIDES_PATH.exists():
        return pd.DataFrame(columns=empty_columns)

    overrides_df = pd.read_csv(GENERATION_MUNICIPAL_OVERRIDES_PATH)
    overrides_df = _normalize_columns(overrides_df)
    if "id" not in overrides_df.columns or "municipio" not in overrides_df.columns:
        return pd.DataFrame(columns=empty_columns)

    overrides_df = overrides_df[[column for column in overrides_df.columns if column in {"id", "municipio", "latitud", "longitud"}]].copy()
    overrides_df["id"] = pd.to_numeric(overrides_df["id"], errors="coerce")
    overrides_df = overrides_df.dropna(subset=["id"])
    overrides_df["id"] = overrides_df["id"].astype(int)
    overrides_df["municipio"] = overrides_df["municipio"].astype("string").str.strip()
    overrides_df = overrides_df[overrides_df["municipio"].notna() & (overrides_df["municipio"] != "")]
    overrides_df["municipio_normalizado"] = normalize_municipality_series(overrides_df["municipio"])

    if GENERATION_MUNICIPAL_COORDS_PATH.exists():
        coords_df = pd.read_csv(GENERATION_MUNICIPAL_COORDS_PATH)
        coords_df = _normalize_columns(coords_df)
        if {"municipio", "latitud", "longitud"}.issubset(coords_df.columns):
            coords_df = coords_df[["municipio", "latitud", "longitud"]].copy()
            coords_df["municipio_normalizado"] = normalize_municipality_series(coords_df["municipio"])
            coords_df["latitud"] = pd.to_numeric(coords_df["latitud"], errors="coerce")
            coords_df["longitud"] = pd.to_numeric(coords_df["longitud"], errors="coerce")
            overrides_df = overrides_df.merge(
                coords_df[["municipio_normalizado", "latitud", "longitud"]].rename(
                    columns={"latitud": "latitud_catalogo", "longitud": "longitud_catalogo"}
                ),
                on="municipio_normalizado",
                how="left",
            )
            overrides_df["latitud"] = pd.to_numeric(overrides_df.get("latitud"), errors="coerce")
            overrides_df["longitud"] = pd.to_numeric(overrides_df.get("longitud"), errors="coerce")
            overrides_df["latitud"] = overrides_df["latitud"].fillna(overrides_df["latitud_catalogo"])
            overrides_df["longitud"] = overrides_df["longitud"].fillna(overrides_df["longitud_catalogo"])

    overrides_df["precision_ubicacion"] = "coordenada_municipal_referenciada"
    overrides_df["detalle_ubicacion"] = (
        "Municipio referenciado manualmente y coordenada tomada del catalogo municipal de apoyo."
    )
    return overrides_df[["id", "municipio", "latitud", "longitud", "precision_ubicacion", "detalle_ubicacion"]]


def apply_generation_location_overrides(dataframe: pd.DataFrame) -> pd.DataFrame:
    enriched_df = dataframe.copy()
    if "id" in enriched_df.columns:
        enriched_df["id"] = pd.to_numeric(enriched_df["id"], errors="coerce")
    else:
        enriched_df["id"] = pd.NA

    enriched_df["municipio"] = "NO DISPONIBLE EN LA FUENTE"
    enriched_df["precision_ubicacion"] = "coordenada_aproximada_departamental"
    enriched_df["detalle_ubicacion"] = (
        "La fuente original no incluye municipio ni coordenada puntual de la planta; "
        "se usa una ubicacion aproximada asociada al departamento."
    )
    enriched_df["latitud"] = pd.to_numeric(enriched_df.get("latitud"), errors="coerce")
    enriched_df["longitud"] = pd.to_numeric(enriched_df.get("longitud"), errors="coerce")

    overrides_df = load_generation_location_overrides()
    if overrides_df.empty:
        return enriched_df

    enriched_df = enriched_df.merge(overrides_df, on="id", how="left", suffixes=("", "_override"))
    has_override = (
        enriched_df["municipio_override"].notna()
        & enriched_df["latitud_override"].notna()
        & enriched_df["longitud_override"].notna()
    )
    enriched_df.loc[has_override, "municipio"] = enriched_df.loc[has_override, "municipio_override"]
    enriched_df.loc[has_override, "latitud"] = enriched_df.loc[has_override, "latitud_override"]
    enriched_df.loc[has_override, "longitud"] = enriched_df.loc[has_override, "longitud_override"]
    enriched_df.loc[has_override, "precision_ubicacion"] = enriched_df.loc[has_override, "precision_ubicacion_override"]
    enriched_df.loc[has_override, "detalle_ubicacion"] = enriched_df.loc[has_override, "detalle_ubicacion_override"]

    override_columns = [
        "municipio_override",
        "latitud_override",
        "longitud_override",
        "precision_ubicacion_override",
        "detalle_ubicacion_override",
    ]
    return enriched_df.drop(columns=[column for column in override_columns if column in enriched_df.columns])
