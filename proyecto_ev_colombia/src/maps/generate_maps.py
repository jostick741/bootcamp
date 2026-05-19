from __future__ import annotations

from pathlib import Path
import sys

import folium

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.gis.loaders import (
    load_department_metrics_geodataframe,
    load_department_yearly_demand_data,
    get_maps_config,
    load_department_boundaries,
    load_demand_points,
    load_hydraulic_points,
    load_priority_data,
    load_priority_geodataframe,
)
from src.maps.folium_builders import (
    add_map_context_panel,
    add_demand_heatmap,
    add_hydraulic_cluster,
    add_metric_choropleth,
    add_pressure_layer,
    add_priority_choropleth,
    add_priority_markers,
    add_year_slider_choropleth,
    make_base_map,
)

MAPS_DIR = PROJECT_ROOT / "maps"



def _save_map(map_object: folium.Map, file_name: str) -> Path:
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MAPS_DIR / file_name
    map_object.save(str(output_path))
    return output_path



def build_priority_map():
    config = get_maps_config()
    priority_df = load_priority_data()
    priority_gdf = load_priority_geodataframe()
    boundaries_gdf = load_department_boundaries()
    hydraulic_gdf = load_hydraulic_points()

    priority_map = make_base_map()
    add_priority_choropleth(priority_map, boundaries_gdf, priority_df)
    add_priority_markers(priority_map, priority_gdf)
    if not hydraulic_gdf.empty:
        add_hydraulic_cluster(priority_map, hydraulic_gdf)
    folium.LayerControl(collapsed=False).add_to(priority_map)
    return _save_map(priority_map, config.get("outputs", {}).get("priority_map", "mapa_prioridad.html"))


def build_pressure_choropleth_map():
    config = get_maps_config()
    merged_gdf = load_department_metrics_geodataframe()
    pressure_map = make_base_map()
    add_map_context_panel(
        pressure_map,
        title="Mapa departamental de presion energetica",
        subtitle="Cada departamento se colorea por su consumo energetico agregado asociado al parque EV modelado.",
        unit_label="kWh agregados",
        color_meaning="amarillo = menor consumo, rojo = mayor consumo",
    )
    add_metric_choropleth(
        pressure_map,
        merged_gdf,
        metric_column="consumo_energetico",
        metric_label="Presion energetica",
        metric_unit="kWh",
        tooltip_fields=["departamento", "consumo_energetico", "categoria_prioridad"],
        tooltip_aliases=["Departamento", "Presion energetica [kWh]", "Categoria"],
    )
    folium.LayerControl(collapsed=False).add_to(pressure_map)
    return _save_map(
        pressure_map,
        config.get("outputs", {}).get("pressure_choropleth_map", "mapa_presion_energetica.html"),
    )


def build_future_demand_choropleth_map():
    config = get_maps_config()
    boundaries_gdf = load_department_boundaries()
    yearly_demand_df = load_department_yearly_demand_data()
    demand_map = make_base_map()
    add_map_context_panel(
        demand_map,
        title="Mapa departamental de demanda futura",
        subtitle="El slider cambia el anio y recolorea cada departamento con la demanda simultanea estimada por adopcion EV.",
        unit_label="kW simultaneos",
        color_meaning="amarillo = menor demanda, rojo = mayor demanda",
    )
    add_year_slider_choropleth(
        demand_map,
        boundaries_gdf,
        yearly_demand_df,
        metric_column="demanda_futura",
        metric_label="Demanda futura",
        metric_unit="kW",
    )
    folium.LayerControl(collapsed=False).add_to(demand_map)
    return _save_map(
        demand_map,
        config.get("outputs", {}).get("future_demand_choropleth_map", "mapa_demanda_futura.html"),
    )


def build_territorial_priority_choropleth_map():
    config = get_maps_config()
    merged_gdf = load_department_metrics_geodataframe()
    priority_map = make_base_map()
    add_map_context_panel(
        priority_map,
        title="Mapa departamental de prioridad territorial",
        subtitle="Indice multicriterio para priorizar territorios con mayor presion y menor soporte relativo de infraestructura.",
        unit_label="indice compuesto de 0 a 1",
        color_meaning="amarillo = menor prioridad, rojo = mayor prioridad",
    )
    add_metric_choropleth(
        priority_map,
        merged_gdf,
        metric_column="indice_prioridad_territorial",
        metric_label="Indice de prioridad territorial",
        metric_unit="indice 0-1",
        tooltip_fields=["departamento", "indice_prioridad_territorial", "ranking_prioridad"],
        tooltip_aliases=["Departamento", "Indice de prioridad [0-1]", "Ranking"],
    )
    folium.LayerControl(collapsed=False).add_to(priority_map)
    return _save_map(
        priority_map,
        config.get("outputs", {}).get("territorial_priority_choropleth_map", "mapa_prioridad_territorial.html"),
    )



def build_demand_map():
    config = get_maps_config()
    demand_gdf = load_demand_points()

    demand_map = make_base_map()
    if not demand_gdf.empty:
        add_demand_heatmap(demand_map, demand_gdf)
        add_pressure_layer(demand_map, demand_gdf)
    folium.LayerControl(collapsed=False).add_to(demand_map)
    return _save_map(demand_map, config.get("outputs", {}).get("demand_map", "mapa_demanda.html"))



def build_hydraulic_map():
    config = get_maps_config()
    hydraulic_gdf = load_hydraulic_points()
    priority_gdf = load_priority_geodataframe()

    hydraulic_map = make_base_map()
    if not hydraulic_gdf.empty:
        add_hydraulic_cluster(hydraulic_map, hydraulic_gdf)
    if not priority_gdf.empty:
        add_priority_markers(hydraulic_map, priority_gdf)
    folium.LayerControl(collapsed=False).add_to(hydraulic_map)
    return _save_map(hydraulic_map, config.get("outputs", {}).get("hydraulic_map", "mapa_hidraulicas.html"))



def generate_all_maps() -> dict[str, Path]:
    priority_path = build_priority_map()
    demand_path = build_demand_map()
    hydraulic_path = build_hydraulic_map()
    pressure_choropleth_path = build_pressure_choropleth_map()
    future_demand_choropleth_path = build_future_demand_choropleth_map()
    territorial_priority_choropleth_path = build_territorial_priority_choropleth_map()
    return {
        "priority": priority_path,
        "demand": demand_path,
        "hydraulic": hydraulic_path,
        "pressure_choropleth": pressure_choropleth_path,
        "future_demand_choropleth": future_demand_choropleth_path,
        "territorial_priority_choropleth": territorial_priority_choropleth_path,
    }


def main() -> None:
    outputs = generate_all_maps()
    print(f"Mapa prioridad exportado en: {outputs['priority']}")
    print(f"Mapa demanda exportado en: {outputs['demand']}")
    print(f"Mapa hidraulicas exportado en: {outputs['hydraulic']}")
    print(f"Mapa presion energetica exportado en: {outputs['pressure_choropleth']}")
    print(f"Mapa demanda futura exportado en: {outputs['future_demand_choropleth']}")
    print(f"Mapa prioridad territorial exportado en: {outputs['territorial_priority_choropleth']}")


if __name__ == "__main__":
    main()
