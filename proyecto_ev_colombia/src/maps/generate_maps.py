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
    add_symbol_legend_panel,
    add_year_slider_choropleth,
    make_base_map,
)

MAPS_DIR = PROJECT_ROOT / "maps"


def _save_maps_index(outputs: dict[str, Path]) -> Path:
    index_path = MAPS_DIR / "index.html"
    map_catalog = [
        {
            "key": "future_demand_choropleth",
            "title": "1. Mapa de demanda futura",
            "description": "Empieza por este mapa si quieres ver los anos proyectados. Es el unico mapa temporal del atlas.",
            "purpose": "Responde como cambia la demanda EV entre historico y proyeccion.",
            "look_for": "Busca los botones 2027, 2032, 2037, 2042 y 2052 y cambia entre anos.",
            "badge": "Mapa temporal",
        },
        {
            "key": "pressure_choropleth",
            "title": "2. Mapa de presion energetica",
            "description": "Sirve para ver donde se concentra el consumo energetico agregado del parque EV modelado.",
            "purpose": "Responde que departamentos cargan mas presion energetica.",
            "look_for": "Rojo intenso = consumo energetico mas alto.",
            "badge": "Energia",
        },
        {
            "key": "territorial_priority_choropleth",
            "title": "3. Mapa de prioridad territorial",
            "description": "Es el mapa final del ranking multicriterio y combina demanda, crecimiento y brecha hidraulica.",
            "purpose": "Responde que territorios deberian priorizarse primero.",
            "look_for": "Rojo = mayor prioridad territorial.",
            "badge": "Decision",
        },
        {
            "key": "hydraulic",
            "title": "4. Mapa de activos hidraulicos",
            "description": "Ubica el soporte hidraulico observado para contrastarlo con la priorizacion territorial.",
            "purpose": "Responde donde ya hay activos hidraulicos observados.",
            "look_for": "Marcadores verdes = activos hidraulicos.",
            "badge": "Soporte",
        },
        {
            "key": "priority",
            "title": "5. Mapa general de prioridad",
            "description": "Vista combinada del ranking territorial con apoyo de activos y capas auxiliares.",
            "purpose": "Responde la foto general del sistema en una sola vista.",
            "look_for": "Usalo solo despues de entender los mapas 1, 2 y 3.",
            "badge": "Resumen",
        },
        {
            "key": "demand",
            "title": "6. Mapa de calor de demanda",
            "description": "Mapa exploratorio para ver concentraciones espaciales; no es el mejor mapa para empezar.",
            "purpose": "Responde donde se acumula visualmente la demanda proyectada.",
            "look_for": "Nucleos rojos = concentraciones relativas mayores.",
            "badge": "Exploratorio",
        },
    ]

    cards_html = []
    for item in map_catalog:
        output_path = outputs.get(item["key"])
        if not output_path:
            continue
        relative_path = output_path.name
        cards_html.append(
            f"""
            <article class="map-card">
                <div class="map-header-row">
                <span class="map-badge">{item['badge']}</span>
                <h2>{item['title']}</h2>
                </div>
                <p class="map-description">{item['description']}</p>
                <div class="map-meta-block">
                <div><strong>Para que sirve:</strong> {item['purpose']}</div>
                <div><strong>Que mirar:</strong> {item['look_for']}</div>
                </div>
                <div class="map-actions">
                <a class="map-link" href="{relative_path}" target="_blank" rel="noreferrer">Abrir mapa</a>
                </div>
            </article>
            """.strip()
        )

        index_html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Atlas EV Colombia</title>
    <style>
        :root {{
            --bg: #f2efe8;
            --panel: rgba(255,255,255,0.88);
            --ink: #1d2a33;
            --muted: #56636b;
            --accent: #b6541f;
            --accent-dark: #7f3510;
            --border: rgba(29, 42, 51, 0.12);
            --shadow: 0 20px 45px rgba(37, 47, 56, 0.12);
        }}

        * {{ box-sizing: border-box; }}
        html, body {{ margin: 0; padding: 0; background: radial-gradient(circle at top, #f8f3e8 0%, var(--bg) 55%, #e7e1d4 100%); color: var(--ink); font-family: Georgia, 'Times New Roman', serif; }}
        body {{ padding: 32px 20px 56px; }}
        .shell {{ max-width: 1400px; margin: 0 auto; }}
        .hero {{ background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,245,238,0.78)); border: 1px solid var(--border); border-radius: 28px; padding: 28px; box-shadow: var(--shadow); margin-bottom: 24px; }}
        .eyebrow {{ font-size: 13px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent-dark); margin-bottom: 10px; }}
        h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.02; }}
        .lead {{ margin: 0; max-width: 980px; color: var(--muted); font-size: 1.06rem; line-height: 1.6; }}
        .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
        .chip {{ border: 1px solid rgba(182,84,31,0.18); background: rgba(255,248,242,0.95); color: var(--accent-dark); border-radius: 999px; padding: 7px 12px; font-size: 13px; }}
        .callout {{ margin-top: 18px; background: rgba(29,42,51,0.92); color: #fff9f3; border-radius: 18px; padding: 16px 18px; line-height: 1.6; }}
        .grid {{ display: grid; gap: 18px; }}
        .map-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 24px; padding: 20px; box-shadow: var(--shadow); }}
        .map-header-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}
        .map-header-row h2 {{ margin: 0; font-size: 1.4rem; }}
        .map-badge {{ display: inline-flex; align-items: center; border-radius: 999px; background: #fff2e9; color: var(--accent-dark); border: 1px solid rgba(182,84,31,0.18); padding: 6px 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }}
        .map-description {{ margin: 0 0 14px; color: var(--muted); line-height: 1.6; font-size: 1rem; }}
        .map-meta-block {{ display: grid; gap: 8px; margin-bottom: 16px; color: #33414a; line-height: 1.55; }}
        .map-actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .map-link {{ align-self: flex-start; text-decoration: none; background: var(--accent); color: #fff; padding: 10px 14px; border-radius: 999px; font-size: 14px; }}
        .map-link:hover {{ background: var(--accent-dark); }}
    </style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div class="eyebrow">Pipeline EV + PARATEC</div>
            <h1>Atlas operativo de mapas</h1>
            <p class="lead">Esta portada organiza la salida cartografica del pipeline base para que no tengas que abrir archivos HTML sueltos uno por uno. Desde aqui puedes revisar presion energetica, demanda futura por anio, activos hidraulicos y el ranking territorial final.</p>
            <div class="meta">
                <span class="chip">Fuente operativa: MySQL local</span>
                <span class="chip">Horizontes proyectados: 2027, 2032, 2037, 2042, 2052</span>
                <span class="chip">Entregable base: ETAPA 1 + ETAPA 2 + ETAPA 3</span>
            </div>
            <div class="callout">
                <strong>Ruta recomendada:</strong> abre primero <em>Mapa de demanda futura</em> para ver los anos proyectados. Luego abre <em>Mapa de presion energetica</em> y termina con <em>Mapa de prioridad territorial</em>. Los otros mapas son de apoyo y exploracion.
            </div>
        </section>
        <section class="grid">
            {chr(10).join(cards_html)}
        </section>
    </div>
</body>
</html>
        """.strip()
        index_path.write_text(index_html, encoding="utf-8")
        return index_path



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
    add_map_context_panel(
        priority_map,
        title="Mapa general de prioridad",
        subtitle="Usa este mapa como vista de arranque: el color del departamento resume prioridad y las capas adicionales muestran activos y puntos de prioridad.",
        unit_label="indice territorial + apoyo visual de activos",
        color_meaning="amarillo = menor prioridad, rojo = mayor prioridad",
    )
    add_priority_choropleth(priority_map, boundaries_gdf, priority_df)
    add_priority_markers(priority_map, priority_gdf)
    if not hydraulic_gdf.empty:
        add_hydraulic_cluster(priority_map, hydraulic_gdf)
    add_symbol_legend_panel(
        priority_map,
        title="Como leer este mapa",
        items=[
            ("Rojo oscuro: territorio mas prioritario", "#d73027"),
            ("Amarillo: prioridad intermedia o baja", "#fee08b"),
            ("Verde: referencia de activos hidraulicos", "#3c9d3c"),
        ],
    )
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
    add_map_context_panel(
        demand_map,
        title="Mapa de calor de demanda",
        subtitle="Muestra concentraciones territoriales de demanda futura. Sirve para detectar donde se acumula la presion, no para leer un ranking departamental exacto.",
        unit_label="intensidad relativa de demanda proyectada",
        color_meaning="azul = menor concentracion, rojo = nucleo de mayor demanda",
    )
    if not demand_gdf.empty:
        add_demand_heatmap(demand_map, demand_gdf)
        add_pressure_layer(demand_map, demand_gdf)
    add_symbol_legend_panel(
        demand_map,
        title="Como leer este mapa",
        items=[
            ("Rojo del heatmap: concentracion alta de demanda", "#e31a1c"),
            ("Azul del heatmap: concentracion baja de demanda", "#6a5cff"),
            ("Circulos naranjas: huella aproximada de presion", "#ff7f00"),
        ],
    )
    folium.LayerControl(collapsed=False).add_to(demand_map)
    return _save_map(demand_map, config.get("outputs", {}).get("demand_map", "mapa_demanda.html"))



def build_hydraulic_map():
    config = get_maps_config()
    hydraulic_gdf = load_hydraulic_points()
    priority_gdf = load_priority_geodataframe()

    hydraulic_map = make_base_map()
    add_map_context_panel(
        hydraulic_map,
        title="Mapa de activos hidraulicos",
        subtitle="Este mapa sirve para ubicar el soporte hidraulico observado. No muestra demanda por color de fondo, solo activos y puntos complementarios de prioridad.",
        unit_label="ubicacion de activos y puntos de referencia",
        color_meaning="verde = activo hidraulico, otros puntos = apoyo de priorizacion",
    )
    if not hydraulic_gdf.empty:
        add_hydraulic_cluster(hydraulic_map, hydraulic_gdf)
    if not priority_gdf.empty:
        add_priority_markers(hydraulic_map, priority_gdf)
    add_symbol_legend_panel(
        hydraulic_map,
        title="Como leer este mapa",
        items=[
            ("Verde: activo hidraulico observado", "#3c9d3c"),
            ("Amarillo/rojo: punto de prioridad territorial", "#f1b82d"),
        ],
    )
    folium.LayerControl(collapsed=False).add_to(hydraulic_map)
    return _save_map(hydraulic_map, config.get("outputs", {}).get("hydraulic_map", "mapa_hidraulicas.html"))



def generate_all_maps() -> dict[str, Path]:
    priority_path = build_priority_map()
    demand_path = build_demand_map()
    hydraulic_path = build_hydraulic_map()
    pressure_choropleth_path = build_pressure_choropleth_map()
    future_demand_choropleth_path = build_future_demand_choropleth_map()
    territorial_priority_choropleth_path = build_territorial_priority_choropleth_map()
    outputs = {
        "priority": priority_path,
        "demand": demand_path,
        "hydraulic": hydraulic_path,
        "pressure_choropleth": pressure_choropleth_path,
        "future_demand_choropleth": future_demand_choropleth_path,
        "territorial_priority_choropleth": territorial_priority_choropleth_path,
    }
    outputs["index"] = _save_maps_index(outputs)
    return outputs


def main() -> None:
    outputs = generate_all_maps()
    print(f"Mapa prioridad exportado en: {outputs['priority']}")
    print(f"Mapa demanda exportado en: {outputs['demand']}")
    print(f"Mapa hidraulicas exportado en: {outputs['hydraulic']}")
    print(f"Mapa presion energetica exportado en: {outputs['pressure_choropleth']}")
    print(f"Mapa demanda futura exportado en: {outputs['future_demand_choropleth']}")
    print(f"Mapa prioridad territorial exportado en: {outputs['territorial_priority_choropleth']}")
    print(f"Indice de mapas exportado en: {outputs['index']}")


if __name__ == "__main__":
    main()
