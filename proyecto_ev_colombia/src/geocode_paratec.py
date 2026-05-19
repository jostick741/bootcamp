from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from sqlalchemy import create_engine

try:
    from .load_data import DATASETS, prepare_dataframe
except ImportError:
    from load_data import DATASETS, prepare_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CACHE_PATH = PROCESSED_DIR / "paratec_geocoding_cache.json"
OUTPUT_PATH = PROCESSED_DIR / "activos_hidraulicos_geocoded.csv"
DEFAULT_DATABASE_URL = "mysql+pymysql://root@127.0.0.1/proyecto_ev_colombia"
DEFAULT_USER_AGENT = "proyecto_ev_colombia_paratec_geocoder"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Completa coordenadas para PARATEC usando municipio y departamento."
    )
    parser.add_argument("--limit", type=int, default=None, help="Limita la cantidad de filas a procesar.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Construye consultas sin llamar al geocodificador ni escribir resultados.",
    )
    parser.add_argument(
        "--to-postgres",
        action="store_true",
        help="Guarda la salida geocodificada en la tabla activos_hidraulicos_geocoded.",
    )
    return parser.parse_args()


def load_cache() -> dict[str, dict[str, Any]]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, dict[str, Any]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_queries(row: pd.Series) -> list[str]:
    nombre = clean_text(row.get("nombre_activo"))
    municipio = clean_text(row.get("municipio"))
    departamento = clean_text(row.get("departamento"))
    subarea = clean_text(row.get("subarea"))

    queries = [
        f"{nombre}, {municipio}, {departamento}, Colombia",
        f"{municipio}, {departamento}, Colombia",
        f"{subarea}, {departamento}, Colombia" if subarea else "",
        f"{departamento}, Colombia",
    ]
    deduped_queries: list[str] = []
    for query in queries:
        normalized_query = query.strip(", ")
        if normalized_query and normalized_query not in deduped_queries:
            deduped_queries.append(normalized_query)
    return deduped_queries


def geocode_query(
    geocode: RateLimiter,
    query: str,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if query in cache:
        cached_result = cache[query]
        return cached_result if cached_result.get("latitud") is not None else None

    location = geocode(query)
    if location is None:
        cache[query] = {"latitud": None, "longitud": None, "display_name": None}
        return None

    result = {
        "latitud": location.latitude,
        "longitud": location.longitude,
        "display_name": location.address,
    }
    cache[query] = result
    return result


def get_engine():
    return create_engine(DEFAULT_DATABASE_URL)


def geocode_dataframe(
    dataframe: pd.DataFrame,
    limit: int | None = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    dataframe = dataframe.copy()
    if "latitud" not in dataframe.columns:
        dataframe["latitud"] = pd.NA
    if "longitud" not in dataframe.columns:
        dataframe["longitud"] = pd.NA
    dataframe["geocoding_query"] = pd.NA
    dataframe["geocoding_source"] = pd.NA

    cache = load_cache()
    geolocator = Nominatim(user_agent=DEFAULT_USER_AGENT)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, swallow_exceptions=True)

    processed_rows = 0
    for index, row in dataframe.iterrows():
        if limit is not None and processed_rows >= limit:
            break
        if pd.notna(row.get("latitud")) and pd.notna(row.get("longitud")):
            continue

        queries = build_queries(row)
        if dry_run:
            dataframe.at[index, "geocoding_query"] = queries[0] if queries else pd.NA
            dataframe.at[index, "geocoding_source"] = "dry_run"
            processed_rows += 1
            continue

        for query in queries:
            result = geocode_query(geocode, query, cache)
            if result is None:
                continue
            dataframe.at[index, "latitud"] = result["latitud"]
            dataframe.at[index, "longitud"] = result["longitud"]
            dataframe.at[index, "geocoding_query"] = query
            dataframe.at[index, "geocoding_source"] = result["display_name"]
            break

        processed_rows += 1

    if not dry_run:
        save_cache(cache)
    return dataframe


def main() -> None:
    args = parse_args()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dataframe = prepare_dataframe("activos_hidraulicos", DATASETS["activos_hidraulicos"])
    geocoded_dataframe = geocode_dataframe(dataframe, limit=args.limit, dry_run=args.dry_run)

    if args.dry_run:
        preview_columns = [column for column in ["nombre_activo", "municipio", "departamento", "geocoding_query"] if column in geocoded_dataframe.columns]
        print(geocoded_dataframe[preview_columns].head(args.limit or 5).to_string(index=False))
        return

    geocoded_dataframe.to_csv(OUTPUT_PATH, index=False)
    print(f"Archivo geocodificado guardado en: {OUTPUT_PATH}")

    if args.to_postgres:
        engine = get_engine()
        geocoded_dataframe.to_sql("activos_hidraulicos_geocoded", engine, if_exists="replace", index=False)
        print("Tabla 'activos_hidraulicos_geocoded' cargada en PostgreSQL.")


if __name__ == "__main__":
    main()
