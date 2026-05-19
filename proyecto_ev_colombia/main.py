import argparse

from src.bootstrap_data import copy_raw_files
from src.build_phase_tables import run_pipeline
from src.load_data import main as load_to_postgres
from src.maps.generate_maps import generate_all_maps
from src.project_config import get_forecast_horizons, get_simultaneidad


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orquesta el pipeline local del proyecto.")
    parser.add_argument(
        "--load-postgres",
        action="store_true",
        help="Carga las tablas crudas a PostgreSQL además de construir las tablas procesadas.",
    )
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="Omite la exportacion de mapas HTML de la ETAPA 3.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Escenario configurado en config/scenarios.yaml.",
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


if __name__ == "__main__":
    args = parse_args()
    copy_raw_files()
    load_to_postgres()
    run_pipeline(
        simultaneidad=get_simultaneidad(args.scenario, override=args.simultaneidad),
        forecast_horizons=get_forecast_horizons(args.forecast_horizons),
    )
    if not args.skip_maps:
        generate_all_maps()
