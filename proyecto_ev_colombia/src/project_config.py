from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
SCENARIOS_PATH = CONFIG_DIR / "scenarios.yaml"
WEIGHTS_PATH = CONFIG_DIR / "weights.yaml"
DEFAULT_SIMULTANEIDAD = 0.3
DEFAULT_SIMULTANEIDAD_SCENARIOS = {
    "bajo": 0.2,
    "medio": 0.3,
    "alto": 0.5,
}
DEFAULT_FORECAST_HORIZONS = [5, 10, 15, 20, 30]
DEFAULT_WEIGHTS = {
    "demanda": 0.40,
    "crecimiento_ev": 0.30,
    "soporte_hidraulico": 0.15,
    "cobertura_hidraulica": 0.05,
}


def load_yaml_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle) or {}



def get_simultaneidad(scenario_name: str | None = None, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    config = load_yaml_config(SCENARIOS_PATH)
    simultaneidad_config = config.get("simultaneidad", {})
    selected_scenario = scenario_name or config.get("default_scenario")
    if selected_scenario in simultaneidad_config:
        return float(simultaneidad_config[selected_scenario])
    return DEFAULT_SIMULTANEIDAD


def get_forecast_horizons(override: list[int] | None = None) -> list[int]:
    if override:
        horizons = override
    else:
        config = load_yaml_config(SCENARIOS_PATH)
        horizons = config.get("forecast_horizons_anios", DEFAULT_FORECAST_HORIZONS)

    cleaned_horizons = sorted({int(value) for value in horizons if int(value) > 0})
    return cleaned_horizons or DEFAULT_FORECAST_HORIZONS


def get_simultaneidad_scenarios() -> dict[str, float]:
    config = load_yaml_config(SCENARIOS_PATH)
    simultaneidad_config = config.get("simultaneidad", {})

    if not simultaneidad_config:
        simultaneidad_config = DEFAULT_SIMULTANEIDAD_SCENARIOS

    return {
        str(key): float(value)
        for key, value in simultaneidad_config.items()
    }



def get_weights() -> dict[str, float]:
    config = load_yaml_config(WEIGHTS_PATH)
    weights = config.get("weights", {})
    return {
        key: float(weights.get(key, default_value))
        for key, default_value in DEFAULT_WEIGHTS.items()
    }
