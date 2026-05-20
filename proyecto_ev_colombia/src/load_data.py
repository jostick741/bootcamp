from __future__ import annotations

import os
from pathlib import Path
import re
import unicodedata

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
DEFAULT_DATABASE_URL = "mysql+pymysql://root@127.0.0.1/proyecto_ev_colombia"

DATASETS = {
    "vehiculos_ev": {
        "file_name": "datos_abiertos_EV_colombia_realista.xlsx",
        "read_excel_kwargs": {},
        "column_mapping": {},
        "required_columns": [],
    },
    "infraestructura_generacion": {
        "file_name": "infraestructura_generacion_86_registros.xlsx",
        "read_excel_kwargs": {},
        "column_mapping": {
            "tipo_generacion": "tipo_generacion",
            "latitud_aprox": "latitud_aprox",
            "longitud_aprox": "longitud_aprox",
            "nivel_infraestructura": "nivel_infraestructura",
            "uso_modelo_ia": "uso_modelo_ia",
            "prioridad_energetica": "prioridad_energetica",
        },
        "required_columns": [],
    },
    "activos_hidraulicos": {
        "file_name": "PARATEC_Phidráulica_18-05-2026.xlsx",
        "read_excel_kwargs": {"sheet_name": "Phidráulica", "header": 5},
        "column_mapping": {
            "nombre": "nombre_activo",
            "fecha_de_puesta_en_operacion_fpo": "fecha_puesta_en_operacion_fpo",
            "modo_de_operacion": "modo_operacion",
            "capacidad_efectiva_neta_mw": "capacidad_hidraulica",
            "rampas_si_no": "rampas_si_no",
            "unidades_hidraulicas": "unidades_hidraulicas",
            "factor_de_conversion_hidraulico_mw_m3_s": "factor_conversion_hidraulico_mw_m3_s",
            "clasificacion": "clasificacion",
            "minimo_obligatorio_si_no": "minimo_obligatorio_si_no",
            "arranque_autonomo_si_no": "arranque_autonomo_si_no",
            "subarea": "subarea",
            "tipo_de_proceso_productivo": "tipo_activo_hidraulico",
        },
        "required_columns": ["latitud", "longitud"],
    },
}

SQL_LOAD_TABLES = ["vehiculos_ev", "activos_hidraulicos"]
RESULT_TABLES = {
    "etapa1_temporal",
    "temporal_model_input",
    "etapa1_temporal_predicciones",
    "forecast_ev",
    "etapa2_energetico",
    "demanda_energetica",
    "demanda_energetica_escenarios",
    "etapa3_gis",
    "priorizacion_territorial",
    "validacion_etapa3",
}


def get_engine():
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_engine(database_url)


def _quote_identifier(engine, identifier: str) -> str:
    if engine.dialect.name == "mysql":
        return f"`{identifier}`"
    if engine.dialect.name == "postgresql":
        return f'"{identifier}"'
    return identifier


def ensure_database_exists() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        return

    if url.get_backend_name() == "mysql":
        server_engine = create_engine(url.set(database="mysql"))
        with server_engine.begin() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        server_engine.dispose()
        return

    if url.get_backend_name() == "postgresql":
        server_engine = create_engine(url.set(database="postgres"))
        with server_engine.begin() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        server_engine.dispose()


def ensure_result_tables_exist() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el esquema SQL: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in schema_sql.split(";") if statement.strip()]
    result_statements = [
        statement for statement in statements
        if any(f"CREATE TABLE IF NOT EXISTS {table_name}" in statement for table_name in RESULT_TABLES)
    ]

    engine = get_engine()
    with engine.begin() as connection:
        for statement in result_statements:
            connection.exec_driver_sql(statement)


def read_sql_source_table(table_name: str) -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql_table(table_name, engine)


def sql_table_exists(table_name: str) -> bool:
    engine = get_engine()
    inspector = inspect(engine)
    return inspector.has_table(table_name)


def read_sql_table_if_exists(table_name: str) -> pd.DataFrame | None:
    if not sql_table_exists(table_name):
        return None
    return read_sql_source_table(table_name)


def write_sql_table(dataframe: pd.DataFrame, table_name: str, if_exists: str = "replace") -> None:
    engine = get_engine()
    dataframe.to_sql(table_name, engine, if_exists=if_exists, index=False)


def refresh_sql_result_table(dataframe: pd.DataFrame, table_name: str) -> None:
    if table_name not in RESULT_TABLES:
        raise ValueError(f"La tabla '{table_name}' no está registrada como tabla de resultados.")

    ensure_database_exists()
    ensure_result_tables_exist()

    engine = get_engine()
    quoted_table = _quote_identifier(engine, table_name)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"DELETE FROM {quoted_table}")

    if not dataframe.empty:
        dataframe.to_sql(table_name, engine, if_exists="append", index=False)


def normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = []
    for column in dataframe.columns:
        text = str(column).strip().lower().replace(" ", "_")
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"[^a-z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        normalized_columns.append(text)
    dataframe.columns = normalized_columns
    return dataframe


def prepare_dataframe(table_name: str, dataset_config: dict[str, object]) -> pd.DataFrame:
    file_name = dataset_config["file_name"]
    file_path = RAW_DATA_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    dataframe = pd.read_excel(file_path, **dataset_config.get("read_excel_kwargs", {}))
    dataframe = normalize_columns(dataframe)

    column_mapping = dataset_config.get("column_mapping", {})
    if column_mapping:
        for source_column, alias_column in column_mapping.items():
            if source_column in dataframe.columns and alias_column not in dataframe.columns:
                dataframe[alias_column] = dataframe[source_column]

    for column_name in dataset_config.get("required_columns", []):
        if column_name not in dataframe.columns:
            dataframe[column_name] = pd.NA

    if table_name == "infraestructura_generacion":
        ordered_columns = [
            "id",
            "tipo_generacion",
            "departamento",
            "latitud_aprox",
            "longitud_aprox",
            "nivel_infraestructura",
            "uso_modelo_ia",
            "prioridad_energetica",
        ]
        existing_columns = [column for column in ordered_columns if column in dataframe.columns]
        dataframe = dataframe[existing_columns]

    if table_name == "activos_hidraulicos":
        alias_columns = [
            "nombre_activo",
            "fecha_puesta_en_operacion_fpo",
            "modo_operacion",
            "capacidad_hidraulica",
            "rampas_si_no",
            "factor_conversion_hidraulico_mw_m3_s",
            "minimo_obligatorio_si_no",
            "arranque_autonomo_si_no",
            "subarea",
            "tipo_activo_hidraulico",
        ]
        preferred_order = [
            "nombre_activo",
            "nombre",
            "operador",
            "estado",
            "fecha_puesta_en_operacion_fpo",
            "fecha_de_puesta_en_operacion_fpo",
            "modo_operacion",
            "modo_de_operacion",
            "tipo_activo_hidraulico",
            "tipo_de_proceso_productivo",
            "rampas_si_no",
            "rampas_si_no",
            "unidades_hidraulicas",
            "capacidad_hidraulica",
            "capacidad_efectiva_neta_mw",
            "factor_conversion_hidraulico_mw_m3_s",
            "factor_de_conversion_hidraulico_mw_m3_s",
            "clasificacion",
            "minimo_obligatorio_si_no",
            "minimo_obligatorio_si_no",
            "arranque_autonomo_si_no",
            "arranque_autonomo_si_no",
            "departamento",
            "municipio",
            "subarea",
            "latitud",
            "longitud",
        ]
        for alias_column in alias_columns:
            if alias_column not in dataframe.columns:
                dataframe[alias_column] = pd.NA

        ordered_existing = []
        for column in preferred_order:
            if column in dataframe.columns and column not in ordered_existing:
                ordered_existing.append(column)
        remaining_columns = [column for column in dataframe.columns if column not in ordered_existing]
        dataframe = dataframe[ordered_existing + remaining_columns]

    if table_name == "vehiculos_ev":
        preferred_order = [
            "combustible",
            "estado",
            "fecha_registro",
            "anio_registro",
            "clase",
            "departamento",
            "cantidad",
            "marca_ev_colombia",
            "fabricante_bateria_real",
            "tecnologia_bateria",
            "capacidad_kwh",
            "voltaje_v",
            "autonomia_km",
            "consumo_wh_km",
            "potencia_carga_dc_kw",
            "corriente_carga_a",
            "impacto_red",
            "transformador_kva",
        ]
        ordered_existing = [column for column in preferred_order if column in dataframe.columns]
        remaining_columns = [column for column in dataframe.columns if column not in ordered_existing]
        dataframe = dataframe[ordered_existing + remaining_columns]

    return dataframe


def load_excel_to_table(engine, table_name: str, dataset_config: dict[str, object]) -> None:
    file_name = dataset_config["file_name"]
    dataframe = prepare_dataframe(table_name, dataset_config)
    dataframe.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Tabla '{table_name}' cargada desde '{file_name}' con {len(dataframe)} registros.")



def main() -> None:
    ensure_database_exists()
    engine = get_engine()
    for table_name in SQL_LOAD_TABLES:
        dataset_config = DATASETS[table_name]
        load_excel_to_table(engine, table_name, dataset_config)


if __name__ == "__main__":
    main()
