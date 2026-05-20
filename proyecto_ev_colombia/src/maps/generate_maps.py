from __future__ import annotations

import json
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
    add_demand_heatmap,
    add_hydraulic_cluster,
    add_metric_choropleth,
    add_priority_choropleth,
    add_priority_markers,
    add_year_slider_choropleth,
    make_base_map,
)

MAPS_DIR = PROJECT_ROOT / "maps"


def _save_maps_index(outputs: dict[str, Path]) -> Path:
    index_path = MAPS_DIR / "index.html"
    view_catalog = [
        {
            "key": "future_demand_choropleth",
            "tab": "Demanda futura",
            "title": "Demanda futura por anio",
            "description": "Vista principal para recorrer historico y proyeccion de la demanda EV departamental.",
            "purpose": "Comparar anos y detectar donde se concentra la demanda futura.",
            "controls": "year",
            "default_year": 2052,
            "projected_years": [2027, 2032, 2037, 2042, 2052],
        },
        {
            "key": "pressure_choropleth",
            "tab": "Presion energetica",
            "title": "Presion energetica",
            "description": "Coropletico departamental del consumo energetico agregado del parque EV modelado.",
            "purpose": "Ver que departamentos concentran mayor carga energetica.",
            "controls": "none",
        },
        {
            "key": "territorial_priority_choropleth",
            "tab": "Prioridad territorial",
            "title": "Prioridad territorial final",
            "description": "Ranking multicriterio final con demanda, crecimiento EV y brecha hidraulica.",
            "purpose": "Identificar que territorios deberian priorizarse primero.",
            "controls": "none",
        },
        {
            "key": "hydraulic",
            "tab": "Soporte hidraulico",
            "title": "Soporte hidraulico observado",
            "description": "Capa de consulta para ubicar activos hidraulicos observados.",
            "purpose": "Contrastar la prioridad final con la infraestructura hidraulica existente.",
            "controls": "none",
        },
    ]

    secondary_catalog = [
        {
            "key": "priority",
            "title": "Vista combinada",
            "description": "Cruza el ranking territorial con activos hidraulicos como apoyo exploratorio.",
        },
        {
            "key": "demand",
            "title": "Concentracion espacial de demanda",
            "description": "Heatmap exploratorio para ver nucleos relativos de demanda proyectada.",
        },
    ]

    resolved_views = []
    for item in view_catalog:
        output_path = outputs.get(item["key"])
        if not output_path:
            continue
        view_data = dict(item)
        view_data["path"] = output_path.name
        resolved_views.append(view_data)

    secondary_cards = []
    for item in secondary_catalog:
        output_path = outputs.get(item["key"])
        if not output_path:
            continue
        secondary_cards.append(
            f"""
            <article class="secondary-card">
                <h3>{item['title']}</h3>
                <p>{item['description']}</p>
                <a class="secondary-link" href="{output_path.name}" target="_blank" rel="noreferrer">Abrir mapa</a>
            </article>
            """.strip()
        )

    views_json = json.dumps(resolved_views, ensure_ascii=True)

    index_html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Visor EV Colombia</title>
    <style>
        :root {{
            --bg: #ebe6d8;
            --panel: rgba(255,255,255,0.92);
            --panel-strong: rgba(248, 244, 236, 0.98);
            --ink: #1e2a31;
            --muted: #5c676d;
            --accent: #a64b1a;
            --accent-dark: #733111;
            --accent-soft: #f7e5d8;
            --border: rgba(30, 42, 49, 0.13);
            --shadow: 0 18px 40px rgba(32, 42, 49, 0.14);
        }}

        * {{ box-sizing: border-box; }}
        html, body {{ margin: 0; padding: 0; background: linear-gradient(180deg, #f6f0e3 0%, var(--bg) 100%); color: var(--ink); font-family: 'Avenir Next', 'Segoe UI', sans-serif; }}
        body {{ min-height: 100vh; }}
        .shell {{ width: min(1560px, calc(100vw - 28px)); margin: 14px auto; display: grid; gap: 14px; }}
        .hero {{ background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(249,239,228,0.88)); border: 1px solid var(--border); border-radius: 26px; padding: 22px 24px; box-shadow: var(--shadow); }}
        .eyebrow {{ font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent-dark); margin-bottom: 8px; font-weight: 700; }}
        h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 3vw, 3.2rem); line-height: 1.02; font-family: Georgia, 'Times New Roman', serif; }}
        .lead {{ margin: 0; max-width: 1080px; color: var(--muted); font-size: 1rem; line-height: 1.55; }}
        .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
        .chip {{ border: 1px solid rgba(166, 75, 26, 0.16); background: rgba(255, 248, 242, 0.98); color: var(--accent-dark); border-radius: 999px; padding: 7px 12px; font-size: 12px; font-weight: 600; }}
        .layout {{ display: grid; grid-template-columns: minmax(0, 1.8fr) minmax(300px, 0.72fr); gap: 14px; align-items: start; }}
        .viewer-panel, .info-panel, .secondary-panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 26px; box-shadow: var(--shadow); }}
        .viewer-panel {{ overflow: hidden; }}
        .tabs {{ display: flex; flex-wrap: wrap; gap: 10px; padding: 16px 18px 12px; border-bottom: 1px solid var(--border); background: rgba(255,255,255,0.62); }}
        .tab-button {{ border: 1px solid rgba(166,75,26,0.16); background: #fff; color: var(--ink); border-radius: 999px; padding: 10px 14px; cursor: pointer; font-size: 14px; font-weight: 700; transition: 0.18s ease; }}
        .tab-button:hover {{ border-color: rgba(166,75,26,0.45); color: var(--accent-dark); }}
        .tab-button.active {{ background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06); }}
        .toolbar {{ padding: 14px 18px; background: var(--panel-strong); border-bottom: 1px solid var(--border); display: grid; gap: 12px; }}
        .toolbar-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
        .toolbar-label {{ font-size: 12px; font-weight: 800; color: var(--accent-dark); text-transform: uppercase; letter-spacing: 0.08em; }}
        .toolbar-note {{ font-size: 13px; color: var(--muted); }}
        .year-select {{ border: 1px solid rgba(30,42,49,0.18); background: #fff; border-radius: 12px; padding: 10px 12px; font-size: 14px; color: var(--ink); min-width: 140px; }}
        .pill-button {{ border: 1px solid rgba(166,75,26,0.18); background: #fff9f5; color: var(--accent-dark); border-radius: 999px; padding: 8px 12px; cursor: pointer; font-size: 13px; font-weight: 700; transition: 0.18s ease; }}
        .pill-button:hover {{ border-color: rgba(166,75,26,0.5); }}
        .pill-button.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
        .open-link {{ text-decoration: none; color: #fff; background: var(--accent-dark); border-radius: 999px; padding: 10px 14px; font-size: 13px; font-weight: 700; }}
        .map-frame {{ width: 100%; height: min(74vh, 920px); border: 0; display: block; background: #d9e2e8; }}
        .info-panel {{ padding: 20px; position: sticky; top: 14px; }}
        .info-panel h2 {{ margin: 0 0 8px; font-size: 1.35rem; font-family: Georgia, 'Times New Roman', serif; }}
        .info-panel p {{ margin: 0 0 12px; color: var(--muted); line-height: 1.6; font-size: 0.97rem; }}
        .info-kicker {{ font-size: 12px; font-weight: 800; color: var(--accent-dark); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }}
        .info-block {{ padding: 14px; border: 1px solid rgba(30,42,49,0.1); border-radius: 18px; background: rgba(255,255,255,0.7); margin-top: 14px; }}
        .info-block strong {{ display: block; margin-bottom: 6px; font-size: 13px; color: var(--ink); }}
        .secondary-panel {{ padding: 18px 20px; }}
        .secondary-panel h3 {{ margin: 0 0 6px; font-size: 1.05rem; }}
        .secondary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; margin-top: 14px; }}
        .secondary-card {{ padding: 16px; border-radius: 18px; border: 1px solid rgba(30,42,49,0.1); background: rgba(255,255,255,0.72); }}
        .secondary-card p {{ margin: 0 0 12px; color: var(--muted); line-height: 1.55; font-size: 0.95rem; }}
        .secondary-link {{ text-decoration: none; color: var(--accent-dark); font-weight: 700; }}
        .status-inline {{ font-size: 12px; color: var(--muted); padding: 8px 10px; background: rgba(255,255,255,0.72); border: 1px dashed rgba(30,42,49,0.14); border-radius: 12px; }}
        @media (max-width: 1180px) {{ .layout {{ grid-template-columns: 1fr; }} .info-panel {{ position: static; }} }}
        @media (max-width: 760px) {{ .shell {{ width: min(100vw - 14px, 100%); margin: 7px auto; }} .hero, .info-panel, .secondary-panel {{ border-radius: 20px; }} .viewer-panel {{ border-radius: 22px; }} .map-frame {{ height: 66vh; }} }}
    </style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div class="eyebrow">Pipeline EV + PARATEC</div>
            <h1>Visor Operativo EV Colombia</h1>
            <p class="lead">La vista principal corresponde a un mapa coropletico construido para visualizar la evolucion territorial de la movilidad electrica y su impacto energetico en Colombia. El desarrollo del visor se estructuro en tres fases analiticas integradas dentro del pipeline del proyecto. En la primera fase se realizo la recoleccion y consolidacion de datos abiertos relacionados con vehiculos electricos registrados en el pais. Posteriormente, los datos fueron enriquecidos con variables tecnicas asociadas a baterias, autonomia, consumo energetico y sistemas de carga. Finalmente, se implementaron modelos predictivos y analisis geoespacial para estimar demanda futura, identificar posibles zonas de presion sobre la red electrica y priorizar territorios estrategicos para infraestructura de carga. Cada departamento se representa mediante una escala de color que permite interpretar rapidamente la magnitud de la demanda proyectada y explorar los resultados generados por los modelos de inteligencia artificial, analisis energetico y cartografia GIS desarrollados durante el proyecto.</p>
            <div class="meta">
                <span class="chip">Fuente operativa: MySQL local</span>
                <span class="chip">Horizontes proyectados: 2027, 2032, 2037, 2042, 2052</span>
                <span class="chip">Entregable base: ETAPA 1 + ETAPA 2 + ETAPA 3</span>
            </div>
        </section>

        <section class="layout">
            <div class="viewer-panel">
                <div id="tab-bar" class="tabs"></div>
                <div id="toolbar" class="toolbar"></div>
                <iframe id="map-frame" class="map-frame" title="Visor EV Colombia"></iframe>
            </div>

            <aside class="info-panel">
                <div class="info-kicker">Vista activa</div>
                <h2 id="view-title"></h2>
                <p id="view-description"></p>
                <div class="info-block">
                    <strong>Para que sirve</strong>
                    <p id="view-purpose"></p>
                </div>
                <div class="info-block">
                    <strong>Lectura operativa</strong>
                    <p id="view-reading"></p>
                </div>
                <div class="info-block">
                    <strong>Acceso directo</strong>
                    <a id="open-standalone" class="open-link" href="#" target="_blank" rel="noreferrer">Abrir mapa completo</a>
                </div>
            </aside>
        </section>

        <section class="secondary-panel">
            <h3>Capas exploratorias</h3>
            <p class="toolbar-note">Estas vistas siguen disponibles, pero ya no dominan la entrada al producto. Quedan como apoyo analitico.</p>
            <div class="secondary-grid">
                {chr(10).join(secondary_cards)}
            </div>
        </section>
    </div>

    <script>
        (function() {{
            var views = {views_json};
            if (!views.length) {{
                return;
            }}

            var readingByView = {{
                future_demand_choropleth: 'Usa esta vista para recorrer historico y proyeccion. El control de ano de este visor sincroniza la apertura del mapa principal.',
                pressure_choropleth: 'Usa esta vista para leer carga energetica agregada por departamento y comparar territorios de mayor presion.',
                territorial_priority_choropleth: 'Usa esta vista para la decision final de priorizacion territorial, no para explorar capas auxiliares.',
                hydraulic: 'Usa esta vista como contraste espacial de soporte hidraulico observado.'
            }};

            var tabBar = document.getElementById('tab-bar');
            var toolbar = document.getElementById('toolbar');
            var frame = document.getElementById('map-frame');
            var titleEl = document.getElementById('view-title');
            var descriptionEl = document.getElementById('view-description');
            var purposeEl = document.getElementById('view-purpose');
            var readingEl = document.getElementById('view-reading');
            var openStandalone = document.getElementById('open-standalone');
            var activeViewKey = views[0].key;
            var selectedYear = views[0].default_year || 2052;
            var loadedViewKey = null;
            var loadedFrameUrl = null;

            function getViewByKey(viewKey) {{
                return views.find(function(view) {{ return view.key === viewKey; }}) || views[0];
            }}

            function buildViewUrl(view) {{
                if (view.key === 'future_demand_choropleth') {{
                    return view.path + '?year=' + encodeURIComponent(String(selectedYear));
                }}
                return view.path;
            }}

            function renderTabs() {{
                tabBar.innerHTML = '';
                views.forEach(function(view) {{
                    var button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'tab-button' + (view.key === activeViewKey ? ' active' : '');
                    button.textContent = view.tab;
                    button.addEventListener('click', function() {{
                        activeViewKey = view.key;
                        render();
                    }});
                    tabBar.appendChild(button);
                }});
            }}

            function buildYearToolbar(view) {{
                var wrap = document.createElement('div');
                var labelRow = document.createElement('div');
                labelRow.className = 'toolbar-row';
                labelRow.innerHTML = '<span class="toolbar-label">Ano</span><span class="status-inline">Aplica a la vista de demanda futura.</span>';
                wrap.appendChild(labelRow);

                var controlRow = document.createElement('div');
                controlRow.className = 'toolbar-row';
                var select = document.createElement('select');
                select.className = 'year-select';
                [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2027, 2032, 2037, 2042, 2052].forEach(function(year) {{
                    var option = document.createElement('option');
                    option.value = String(year);
                    option.textContent = String(year);
                    option.selected = Number(year) === Number(selectedYear);
                    select.appendChild(option);
                }});
                select.addEventListener('change', function(event) {{
                    selectedYear = Number(event.target.value);
                    syncActiveView();
                    syncToolbarState();
                }});
                controlRow.appendChild(select);

                (view.projected_years || []).forEach(function(year) {{
                    var button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'pill-button' + (Number(year) === Number(selectedYear) ? ' active' : '');
                    button.textContent = String(year);
                    button.dataset.year = String(year);
                    button.addEventListener('click', function() {{
                        selectedYear = Number(year);
                        syncActiveView();
                        syncToolbarState();
                    }});
                    controlRow.appendChild(button);
                }});
                wrap.appendChild(controlRow);
                return wrap;
            }}

            function buildDefaultToolbar() {{
                var note = document.createElement('div');
                note.className = 'toolbar-row';
                note.innerHTML = '<span class="toolbar-label">Vista activa</span><span class="status-inline">En esta iteracion el filtro sincronizado queda implementado primero para demanda futura. Las demas vistas ya entran por tabs y acceso unificado.</span>';
                return note;
            }}

            function renderToolbar(view) {{
                toolbar.innerHTML = '';
                if (view.controls === 'year') {{
                    toolbar.appendChild(buildYearToolbar(view));
                    return;
                }}
                toolbar.appendChild(buildDefaultToolbar());
            }}

            function setFrameSource(view) {{
                var nextUrl = buildViewUrl(view);
                frame.src = nextUrl;
                openStandalone.href = nextUrl;
                loadedViewKey = view.key;
                loadedFrameUrl = nextUrl;
            }}

            function syncFutureDemandYear() {{
                if (activeViewKey !== 'future_demand_choropleth') {{
                    return false;
                }}
                try {{
                    if (frame.contentWindow && typeof frame.contentWindow.setDemandMapYear === 'function') {{
                        return frame.contentWindow.setDemandMapYear(selectedYear) === true;
                    }}
                }} catch (error) {{
                    return false;
                }}
                return false;
            }}

            function syncActiveView() {{
                var activeView = getViewByKey(activeViewKey);
                var nextUrl = buildViewUrl(activeView);
                openStandalone.href = nextUrl;

                if (activeView.key === 'future_demand_choropleth' && loadedViewKey === activeView.key && syncFutureDemandYear()) {{
                    loadedFrameUrl = nextUrl;
                    return;
                }}

                if (loadedViewKey !== activeView.key) {{
                    setFrameSource(activeView);
                    return;
                }}

                if (loadedFrameUrl !== nextUrl) {{
                    setFrameSource(activeView);
                }}
            }}

            function syncToolbarState() {{
                var select = toolbar.querySelector('.year-select');
                if (select) {{
                    select.value = String(selectedYear);
                }}
                toolbar.querySelectorAll('.pill-button').forEach(function(button) {{
                    button.classList.toggle('active', Number(button.dataset.year) === Number(selectedYear));
                }});
            }}

            function renderInfo(view) {{
                titleEl.textContent = view.title;
                descriptionEl.textContent = view.description;
                purposeEl.textContent = view.purpose;
                readingEl.textContent = readingByView[view.key] || 'Vista de apoyo analitico del proyecto.';
            }}

            function render() {{
                var activeView = getViewByKey(activeViewKey);
                renderTabs();
                renderToolbar(activeView);
                renderInfo(activeView);
                syncActiveView();
                syncToolbarState();
            }}

            frame.addEventListener('load', function() {{
                loadedViewKey = activeViewKey;
                loadedFrameUrl = buildViewUrl(getViewByKey(activeViewKey));
                if (activeViewKey === 'future_demand_choropleth') {{
                    syncFutureDemandYear();
                }}
            }});

            render();
        }})();
    </script>
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
    add_priority_choropleth(priority_map, boundaries_gdf, priority_df)
    add_priority_markers(priority_map, priority_gdf)
    if not hydraulic_gdf.empty:
        add_hydraulic_cluster(priority_map, hydraulic_gdf, show=False)
    folium.LayerControl(collapsed=False).add_to(priority_map)
    return _save_map(priority_map, config.get("outputs", {}).get("priority_map", "mapa_prioridad.html"))


def build_pressure_choropleth_map():
    config = get_maps_config()
    merged_gdf = load_department_metrics_geodataframe()
    pressure_map = make_base_map()
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
