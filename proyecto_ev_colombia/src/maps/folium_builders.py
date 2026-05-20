from __future__ import annotations

import json

import folium
from branca.element import Element
from branca.colormap import linear
from folium.plugins import HeatMap, MarkerCluster

from src.gis.loaders import get_maps_config


def add_map_context_panel(
    base_map: folium.Map,
    title: str,
    subtitle: str,
    unit_label: str,
    color_meaning: str,
) -> None:
    panel_html = f"""
    <div style="position: fixed; top: 22px; left: 50px; z-index: 9999; width: 380px; background: rgba(255,255,255,0.96); border: 1px solid #d2d2d2; border-radius: 12px; box-shadow: 0 3px 14px rgba(0,0,0,0.16); padding: 14px 16px; font-family: Arial, sans-serif;">
      <div style="font-size: 18px; font-weight: 700; color: #222; margin-bottom: 4px;">{title}</div>
      <div style="font-size: 13px; color: #4f4f4f; margin-bottom: 10px; line-height: 1.35;">{subtitle}</div>
      <div style="font-size: 12px; color: #333; margin-bottom: 6px;"><b>Unidad:</b> {unit_label}</div>
      <div style="font-size: 12px; color: #333; margin-bottom: 6px;"><b>Lectura del color:</b> {color_meaning}</div>
      <div style="font-size: 12px; color: #666;">Todos los mapas analíticos usan el mismo criterio visual: color por departamento, gris si no hay dato.</div>
    </div>
    """
    base_map.get_root().html.add_child(Element(panel_html))


def add_symbol_legend_panel(
    base_map: folium.Map,
    title: str,
    items: list[tuple[str, str]],
    position: str = "topright",
) -> None:
    if not items:
        return

    position_css = {
        "topright": "top: 22px; right: 24px;",
        "bottomleft": "bottom: 24px; left: 24px;",
        "bottomright": "bottom: 24px; right: 24px;",
    }.get(position, "top: 22px; right: 24px;")

    legend_items = "".join(
        f"<div style=\"display:flex; align-items:center; gap:8px; margin-bottom:6px;\">"
        f"<span style=\"display:inline-block; width:12px; height:12px; border-radius:999px; background:{color}; border:1px solid rgba(0,0,0,0.18);\"></span>"
        f"<span>{label}</span></div>"
        for label, color in items
    )
    legend_html = f"""
    <div style="position: fixed; {position_css} z-index: 9999; width: 260px; background: rgba(255,255,255,0.96); border: 1px solid #d2d2d2; border-radius: 12px; box-shadow: 0 3px 14px rgba(0,0,0,0.16); padding: 12px 14px; font-family: Arial, sans-serif;">
      <div style="font-size: 14px; font-weight: 700; color: #222; margin-bottom: 8px;">{title}</div>
      <div style="font-size: 12px; color: #444; line-height: 1.4;">{legend_items}</div>
    </div>
    """
    base_map.get_root().html.add_child(Element(legend_html))


def _format_metric_value(value, unit_suffix: str, decimals: int = 2) -> str:
    numeric_value = float(value or 0)
    formatted_value = f"{numeric_value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted_value} {unit_suffix}".strip()



def make_base_map() -> folium.Map:
    config = get_maps_config().get("base_map", {})
    return folium.Map(
        location=[config.get("center_lat", 4.5709), config.get("center_lon", -74.2973)],
        zoom_start=config.get("zoom_start", 6),
        tiles=config.get("tiles", "cartodbpositron"),
    )


def _display_department_label(label_text: str) -> str:
    cleaned = str(label_text).strip().upper()
    replacements = {
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA": "SAN ANDRES",
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRES",
        "BOGOTA D.C.": "BOGOTA",
        "VALLE DEL CAUCA": "VALLE",
        "NORTE DE SANTANDER": "N. SANTANDER",
    }
    return replacements.get(cleaned, cleaned)


def add_department_labels(
    base_map: folium.Map,
    geo_df,
    label_column: str = "departamento",
    layer_name: str = "Etiquetas departamentales",
) -> None:
    return



def _priority_color(priority_category: str) -> str:
    color_map = {
        "ALTA": "#d73027",
        "MEDIA": "#fee08b",
        "BAJA": "#1a9850",
    }
    return color_map.get(str(priority_category).upper(), "#4575b4")



def add_priority_choropleth(base_map: folium.Map, boundaries_gdf, priority_df) -> None:
    merged = boundaries_gdf.merge(priority_df, on="departamento", how="left")
    colormap = linear.YlOrRd_09.scale(0, max(1.0, merged["indice_prioridad_territorial"].fillna(0).max()))
    colormap.caption = "Indice de prioridad territorial"

    def style_function(feature):
        value = feature["properties"].get("indice_prioridad_territorial")
        if value is None:
            return {"fillColor": "#d9d9d9", "color": "#555", "weight": 0.5, "fillOpacity": 0.2}
        return {
            "fillColor": colormap(value),
            "color": "#555",
            "weight": 0.8,
            "fillOpacity": 0.65,
        }

    popup = folium.GeoJsonPopup(
        fields=[
            "departamento",
            "demanda_futura",
            "cantidad_ev_modelada",
            "indice_prioridad_territorial",
            "ranking_prioridad",
            "categoria_prioridad",
        ],
        aliases=[
            "Departamento",
            "Demanda futura",
            "EV modelados",
            "Indice de prioridad",
            "Ranking",
            "Categoria",
        ],
        localize=True,
        labels=True,
    )

    tooltip = folium.GeoJsonTooltip(
        fields=["departamento", "categoria_prioridad", "ranking_prioridad"],
        aliases=["Departamento", "Categoria", "Ranking"],
        sticky=False,
    )

    folium.GeoJson(
        merged,
        name="Coropletico prioridad territorial",
        style_function=style_function,
        popup=popup,
        tooltip=tooltip,
    ).add_to(base_map)
    add_department_labels(base_map, merged)
    colormap.add_to(base_map)


def add_metric_choropleth(
    base_map: folium.Map,
    merged_gdf,
    metric_column: str,
    metric_label: str,
    metric_unit: str,
    tooltip_fields: list[str],
    tooltip_aliases: list[str],
) -> None:
    display_gdf = merged_gdf.copy()
    max_value = max(1.0, display_gdf[metric_column].fillna(0).max())
    colormap = linear.YlOrRd_09.scale(0, max_value)
    colormap.caption = f"{metric_label} [{metric_unit}]"

    display_gdf[f"{metric_column}_display"] = display_gdf[metric_column].apply(
        lambda value: _format_metric_value(value, metric_unit, 2)
    )
    display_gdf["demanda_futura_display"] = display_gdf["demanda_futura"].apply(
        lambda value: _format_metric_value(value, "kW", 2)
    )
    display_gdf["consumo_energetico_display"] = display_gdf["consumo_energetico"].apply(
        lambda value: _format_metric_value(value, "kWh", 2)
    )
    display_gdf["cantidad_ev_modelada_display"] = display_gdf["cantidad_ev_modelada"].apply(
        lambda value: _format_metric_value(value, "vehiculos", 0)
    )
    display_gdf["indice_prioridad_display"] = display_gdf["indice_prioridad_territorial"].apply(
        lambda value: _format_metric_value(value, "indice", 3)
    )

    def style_function(feature):
        value = feature["properties"].get(metric_column)
        if value is None:
            return {"fillColor": "#d9d9d9", "color": "#555", "weight": 0.5, "fillOpacity": 0.2}
        return {
            "fillColor": colormap(value),
            "color": "#555",
            "weight": 0.8,
            "fillOpacity": 0.70,
        }

    tooltip = folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        sticky=False,
    )

    popup = folium.GeoJsonPopup(
        fields=[
            "departamento",
            f"{metric_column}_display",
            "demanda_futura_display",
            "consumo_energetico_display",
            "cantidad_ev_modelada_display",
            "indice_prioridad_display",
            "ranking_prioridad",
            "categoria_prioridad",
        ],
        aliases=[
            "Departamento",
            metric_label,
            "Demanda futura",
            "Consumo energetico",
            "EV modelados",
            "Indice de prioridad",
            "Ranking",
            "Categoria",
        ],
        labels=True,
        localize=False,
    )

    geojson = folium.GeoJson(
        display_gdf,
        name=metric_label,
        style_function=style_function,
        popup=popup,
        tooltip=tooltip,
    )
    geojson.add_to(base_map)

    add_department_labels(base_map, display_gdf)
    colormap.add_to(base_map)


def add_year_slider_choropleth(
        base_map: folium.Map,
        boundaries_gdf,
        yearly_metrics_df,
        metric_column: str,
        metric_label: str,
    metric_unit: str,
) -> None:
        years = sorted(int(year) for year in yearly_metrics_df["anio"].dropna().unique())
        if not years:
                return

        metrics_df = yearly_metrics_df.copy()
        numeric_columns = [
                metric_column,
                "consumo_energetico",
                "cantidad_ev_modelada",
                "cantidad_ev_historica",
                "aumento_demanda",
                "aumento_demanda_pct",
        ]
        for column in numeric_columns:
                if column in metrics_df.columns:
                        metrics_df[column] = metrics_df[column].fillna(0)

        metric_values = metrics_df[metric_column].dropna() if metric_column in metrics_df.columns else []
        metric_min = float(metric_values.min()) if len(metric_values) else 0.0
        metric_max = float(metric_values.max()) if len(metric_values) else 0.0
        if metric_min == metric_max:
            metric_min = min(0.0, metric_min)
            metric_max = max(1.0, metric_max)

        historical_years = sorted(
            int(year)
            for year in metrics_df.loc[metrics_df["cantidad_ev_historica"] > 0, "anio"].dropna().unique()
        )
        max_historical_year = historical_years[-1] if historical_years else years[0]
        projected_years = [year for year in years if year > max_historical_year]

        department_metrics: dict[str, dict[str, dict[str, float]]] = {}
        for record in metrics_df.to_dict(orient="records"):
                department = record["departamento"]
                year_key = str(int(record["anio"]))
                department_metrics.setdefault(department, {})[year_key] = {
                        "demanda_futura": round(float(record.get("demanda_futura", 0) or 0), 2),
                        "consumo_energetico": round(float(record.get("consumo_energetico", 0) or 0), 2),
                        "cantidad_ev_modelada": round(float(record.get("cantidad_ev_modelada", 0) or 0), 2),
                        "cantidad_ev_historica": round(float(record.get("cantidad_ev_historica", 0) or 0), 2),
                        "aumento_demanda": round(float(record.get("aumento_demanda", 0) or 0), 2),
                        "aumento_demanda_pct": round(float(record.get("aumento_demanda_pct", 0) or 0) * 100, 2),
                }

        initial_year = years[-1]
        initial_metrics = metrics_df[metrics_df["anio"] == initial_year][["departamento", metric_column]].copy()
        initial_metric_map = dict(zip(initial_metrics["departamento"], initial_metrics[metric_column]))
        colormap = linear.YlOrRd_09.scale(metric_min, metric_max)
        colormap.caption = f"{metric_label} [{metric_unit}]"

        def style_function(feature):
                value = initial_metric_map.get(feature["properties"].get("departamento"))
                if value is None:
                        return {"fillColor": "#d9d9d9", "color": "#555", "weight": 0.8, "fillOpacity": 0.2}
                return {
                        "fillColor": colormap(value),
                        "color": "#555",
                        "weight": 0.8,
                        "fillOpacity": 0.75,
                }

        boundaries_layer = folium.GeoJson(
                boundaries_gdf[["departamento", "geometry"]],
                name=f"{metric_label} por anio",
                style_function=style_function,
        )
        boundaries_layer.add_to(base_map)
        colormap.add_to(base_map)

        map_name = base_map.get_name()
        layer_name = boundaries_layer.get_name()
        map_name_json = json.dumps(map_name)
        layer_name_json = json.dumps(layer_name)
        years_json = json.dumps(years)
        projected_years_json = json.dumps(projected_years)
        metrics_json = json.dumps(department_metrics, ensure_ascii=True)
        metric_key_json = json.dumps(metric_column)
        metric_label_json = json.dumps(metric_label)
        metric_unit_json = json.dumps(metric_unit)
        department_positions = {}
        for _, row in boundaries_gdf[["departamento", "geometry"]].iterrows():
            label_point = row["geometry"].representative_point()
            department_positions[row["departamento"]] = {
                "lat": round(float(label_point.y), 6),
                "lon": round(float(label_point.x), 6),
                "shortLabel": _display_department_label(row["departamento"]),
            }
        department_positions_json = json.dumps(department_positions, ensure_ascii=True)

        control_html = f"""
        <div id="year-slider-control" style="position: fixed; left: 24px; top: 24px; z-index: 9999; width: 300px; background: rgba(255,252,247,0.95); border: 1px solid rgba(166, 75, 26, 0.18); border-radius: 16px; box-shadow: 0 10px 24px rgba(55,38,24,0.16); padding: 12px 14px; font-family: Arial, sans-serif; backdrop-filter: blur(8px);">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px;">
                <div>
                    <div style="font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: #8f4a1c; font-weight: 700; margin-bottom: 3px;">Demanda futura</div>
                    <div id="year-slider-context" style="font-size: 12px; color: #6c6258; line-height: 1.3;">Horizonte visible del mapa</div>
                </div>
                <div id="year-slider-badge" style="min-width: 62px; text-align: center; border-radius: 999px; background: linear-gradient(135deg, #bf5a24, #8f3b14); color: #fff; padding: 7px 10px; font-size: 15px; font-weight: 700; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.12);"></div>
            </div>
            <div id="projected-year-buttons" style="display: flex; flex-wrap: wrap; gap: 6px;"></div>
            <div id="year-slider-value" style="margin-top: 8px; font-size: 12px; color: #6c6258; line-height: 1.35;"></div>
        </div>
        """
        base_map.get_root().html.add_child(Element(control_html))

        control_script = f"""
        (function() {{
            var mapObjectName = {map_name_json};
            var demandLayerName = {layer_name_json};
            var availableYears = {years_json};
            var projectedYears = {projected_years_json};
            var departmentMetrics = {metrics_json};
            var selectedMetricKey = {metric_key_json};
            var selectedMetricLabel = {metric_label_json};
            var selectedMetricUnit = {metric_unit_json};
            var metricMin = {metric_min};
            var metricMax = {metric_max};
            var palette = ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"];
            var currentYear = availableYears[availableYears.length - 1];
            var yearValue = document.getElementById("year-slider-value");
            var yearBadge = document.getElementById("year-slider-badge");
            var yearContext = document.getElementById("year-slider-context");
            var projectedYearButtons = document.getElementById("projected-year-buttons");
            var initialYearParam = null;
            var departmentPositions = {department_positions_json};
            var mapObject = null;
            var demandLayer = null;
            var departmentValueLayer = null;
            var departmentValueMarkers = {{}};
            var initializationAttempts = 0;
            var maxInitializationAttempts = 120;
            var isEmbedded = false;

            try {{
                initialYearParam = new URLSearchParams(window.location.search).get('year');
            }} catch (error) {{
                initialYearParam = null;
            }}

            try {{
                isEmbedded = window.self !== window.top;
            }} catch (error) {{
                isEmbedded = true;
            }}

            function formatNumber(value, maximumFractionDigits) {{
                return new Intl.NumberFormat("es-CO", {{
                    minimumFractionDigits: 0,
                    maximumFractionDigits: maximumFractionDigits
                }}).format(value || 0);
            }}

            function getMetricRecord(department) {{
                var metricsByYear = departmentMetrics[department] || {{}};
                return metricsByYear[String(currentYear)] || null;
            }}

            function getColor(value) {{
                if (value === null || value === undefined) {{
                    return "#d9d9d9";
                }}
                if (metricMax <= metricMin) {{
                    return palette[palette.length - 1];
                }}
                var ratio = Math.max(0, Math.min(1, (value - metricMin) / (metricMax - metricMin)));
                var index = Math.min(palette.length - 1, Math.round(ratio * (palette.length - 1)));
                return palette[index];
            }}

            function getFeatureStyle(feature) {{
                var department = feature.properties.departamento;
                var metricRecord = getMetricRecord(department);
                var value = metricRecord ? metricRecord[selectedMetricKey] : null;
                return {{
                    fillColor: getColor(value),
                    color: "#555",
                    weight: 0.8,
                    fillOpacity: value === null ? 0.2 : 0.78
                }};
            }}

            function buildInfoHtml(department) {{
                if (!department) {{
                    return '';
                }}
                var metricRecord = getMetricRecord(department);
                if (!metricRecord) {{
                    return '';
                }}
                var increase = metricRecord.aumento_demanda;
                var increasePct = metricRecord.aumento_demanda_pct;
                var increaseColor = increase >= 0 ? '#c0392b' : '#1f7a1f';
                return '' +
                    '<div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">' + department + '</div>' +
                    '<div style="font-size: 13px; margin-bottom: 6px;">Anio: <b>' + currentYear + '</b></div>' +
                        '<div style="font-size: 13px; margin-bottom: 6px;">' + selectedMetricLabel + ': <b>' + formatNumber(metricRecord[selectedMetricKey], 2) + ' ' + selectedMetricUnit + '</b></div>' +
                        '<div style="font-size: 13px; margin-bottom: 6px;">Consumo energetico: <b>' + formatNumber(metricRecord.consumo_energetico, 2) + ' kWh</b></div>' +
                        '<div style="font-size: 13px; margin-bottom: 6px;">EV modelados: <b>' + formatNumber(metricRecord.cantidad_ev_modelada, 0) + ' vehiculos</b></div>' +
                        '<div style="font-size: 13px; margin-bottom: 6px; color: ' + increaseColor + ';">Aumento vs anio previo: <b>' + formatNumber(increase, 2) + ' ' + selectedMetricUnit + '</b> (' + formatNumber(increasePct, 2) + '%)</div>';
            }}

            function syncProjectedYearButtons() {{
                if (!projectedYearButtons) {{
                    return;
                }}
                projectedYearButtons.innerHTML = '';
                if (!projectedYears.length) {{
                    projectedYearButtons.innerHTML = '<span style="font-size: 12px; color: #777;">No hay anos proyectados visibles.</span>';
                    return;
                }}
                if (isEmbedded) {{
                    projectedYearButtons.style.display = 'none';
                    if (yearContext) {{
                        yearContext.textContent = 'Controlado desde la barra superior del visor';
                    }}
                    return;
                }}
                projectedYearButtons.style.display = 'flex';
                if (yearContext) {{
                    yearContext.textContent = 'Selecciona un horizonte proyectado';
                }}
                projectedYears.forEach(function(year) {{
                    var button = document.createElement('button');
                    button.type = 'button';
                    button.textContent = String(year);
                    button.style.border = '1px solid rgba(191, 90, 36, 0.28)';
                    button.style.borderRadius = '999px';
                    button.style.padding = '5px 10px';
                    button.style.fontSize = '12px';
                    button.style.fontWeight = '700';
                    button.style.cursor = 'pointer';
                    button.style.background = year === currentYear ? 'linear-gradient(135deg, #c96b2c, #944016)' : '#fff8f1';
                    button.style.color = year === currentYear ? '#ffffff' : '#7a3d12';
                    button.style.boxShadow = year === currentYear ? '0 6px 14px rgba(148,64,22,0.22)' : 'none';
                    button.addEventListener('click', function() {{
                        currentYear = year;
                        updateMapForYear();
                    }});
                    projectedYearButtons.appendChild(button);
                }});
            }}

            function buildPopupHtml(department) {{
                return buildInfoHtml(department);
            }}

            function buildDepartmentValueHtml(department) {{
                var positionRecord = departmentPositions[department] || {{}};
                var metricRecord = getMetricRecord(department);
                var value = metricRecord ? metricRecord[selectedMetricKey] : 0;
                var labelBorderOpacity = 0.24;
                var labelBackgroundOpacity = 0.94;
                var valueTextColor = '#8f2d12';
                return '' +
                    '<div style="transform: translate(-50%, -50%); white-space: nowrap; text-align: center;">' +
                        '<div style="font-size: 10px; font-weight: 800; color: #1f2a30; background: rgba(255,255,255,0.82); border: 1px solid rgba(31,42,48,0.14); border-radius: 999px; padding: 1px 6px; display: inline-block; margin-bottom: 3px;">' +
                            positionRecord.shortLabel +
                        '</div>' +
                        '<div style="font-size: 11px; font-weight: 800; color: ' + valueTextColor + '; background: rgba(255,248,242,' + labelBackgroundOpacity.toFixed(2) + '); border: 1px solid rgba(166,75,26,' + labelBorderOpacity.toFixed(2) + '); border-radius: 8px; padding: 2px 6px; display: inline-block; box-shadow: 0 1px 4px rgba(0,0,0,0.10);">' +
                            formatNumber(value, 2) + ' ' + selectedMetricUnit +
                        '</div>' +
                    '</div>';
            }}

            function syncDepartmentValueLabels() {{
                if (!departmentValueLayer) {{
                    return;
                }}
                Object.keys(departmentPositions).forEach(function(department) {{
                    var positionRecord = departmentPositions[department];
                    var html = buildDepartmentValueHtml(department);
                    var icon = L.divIcon({{
                        className: 'department-value-label',
                        html: html,
                        iconSize: null,
                    }});

                    if (!departmentValueMarkers[department]) {{
                        departmentValueMarkers[department] = L.marker([positionRecord.lat, positionRecord.lon], {{
                            icon: icon,
                            interactive: false,
                            keyboard: false,
                            zIndexOffset: 1000,
                        }}).addTo(departmentValueLayer);
                        return;
                    }}

                    departmentValueMarkers[department].setIcon(icon);
                }});
            }}

            function applyYear(nextYear) {{
                if (availableYears.indexOf(nextYear) === -1) {{
                    return false;
                }}
                currentYear = nextYear;
                updateMapForYear();
                if (window.history && typeof window.history.replaceState === 'function') {{
                    var nextUrl = new URL(window.location.href);
                    nextUrl.searchParams.set('year', String(nextYear));
                    window.history.replaceState(null, '', nextUrl.toString());
                }}
                return true;
            }}

            function updateMapForYear() {{
                if (!demandLayer || !departmentValueLayer) {{
                    return;
                }}
                if (yearBadge) {{
                    yearBadge.textContent = String(currentYear);
                }}
                if (yearValue) {{
                    yearValue.textContent = isEmbedded ? 'El cambio de ano se sincroniza desde el visor principal.' : 'Explora el mapa por ano sin salir de esta vista.';
                }}
                syncProjectedYearButtons();
                syncDepartmentValueLabels();
                demandLayer.eachLayer(function(layer) {{
                    layer.setStyle(getFeatureStyle(layer.feature));
                    if (layer.getPopup()) {{
                        layer.closePopup();
                        layer.setPopupContent(buildPopupHtml(layer.feature.properties.departamento));
                    }}
                }});
            }}

            function bindLayerInteractions() {{
                demandLayer.eachLayer(function(layer) {{
                    var department = layer.feature.properties.departamento;
                    layer.bindPopup(buildPopupHtml(department), {{maxWidth: 300}});
                    layer.on('mouseover', function(event) {{
                        event.target.setStyle({{weight: 2, color: '#111'}});
                    }});
                    layer.on('mouseout', function(event) {{
                        event.target.setStyle(getFeatureStyle(event.target.feature));
                    }});
                    layer.on('click', function(event) {{
                        event.target.setPopupContent(buildPopupHtml(department));
                    }});
                }});
            }}

            function resolveDemandMapObjects() {{
                mapObject = window[mapObjectName] || null;
                demandLayer = window[demandLayerName] || null;

                if (!mapObject || !demandLayer || typeof demandLayer.eachLayer !== 'function') {{
                    return false;
                }}

                if (!departmentValueLayer) {{
                    departmentValueLayer = L.layerGroup().addTo(mapObject);
                }}

                return true;
            }}

            function initializeDemandMap() {{
                if (!resolveDemandMapObjects()) {{
                    initializationAttempts += 1;
                    if (initializationAttempts >= maxInitializationAttempts) {{
                        console.error('No fue posible inicializar el mapa de demanda futura a tiempo.');
                        return;
                    }}
                    window.setTimeout(initializeDemandMap, 50);
                    return;
                }}

                bindLayerInteractions();

                window.setDemandMapYear = function(nextYear) {{
                    return applyYear(Number(nextYear));
                }};

                window.getDemandMapAvailableYears = function() {{
                    return availableYears.slice();
                }};

                if (initialYearParam !== null) {{
                    applyYear(Number(initialYearParam));
                    return;
                }}

                updateMapForYear();
            }}

            initializeDemandMap();
        }})();
        """
        base_map.get_root().script.add_child(Element(control_script))
        return



def add_priority_markers(base_map: folium.Map, priority_gdf) -> None:
    feature_group = folium.FeatureGroup(name="Prioridad territorial", show=False)
    for _, row in priority_gdf.iterrows():
        popup_html = (
            f"<b>{row['departamento']}</b><br>"
            f"Indice: {row.get('indice_prioridad_territorial', 0):.3f}<br>"
            f"Ranking: {int(row.get('ranking_prioridad', 0))}<br>"
            f"Categoria: {row.get('categoria_prioridad', 'N/A')}<br>"
            f"Demanda futura: {row.get('demanda_futura', 0):.2f}"
        )
        folium.CircleMarker(
            location=[row["latitud"], row["longitud"]],
            radius=7,
            color=_priority_color(row.get("categoria_prioridad", "MEDIA")),
            fill=True,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(feature_group)
    feature_group.add_to(base_map)



def add_demand_heatmap(base_map: folium.Map, demand_gdf) -> None:
    visual = get_maps_config().get("visual", {})
    heat_data = [
        [row["latitud"], row["longitud"], row.get("demanda_futura", 0)]
        for _, row in demand_gdf.iterrows()
    ]
    HeatMap(
        heat_data,
        name="Heatmap demanda futura",
        radius=visual.get("heat_radius", 25),
        blur=visual.get("heat_blur", 18),
        min_opacity=0.3,
    ).add_to(base_map)



def add_generation_cluster(base_map: folium.Map, generation_gdf) -> None:
    cluster = MarkerCluster(name="Infraestructura generacion aproximada", show=True)
    for _, row in generation_gdf.iterrows():
        popup_html = (
            f"<b>{row.get('tipo_generacion', row.get('tipo_infraestructura', 'Infraestructura'))}</b><br>"
            f"Departamento: {row.get('departamento', 'N/A')}<br>"
            f"Municipio: {row.get('municipio', 'NO DISPONIBLE')}<br>"
            f"Prioridad energetica: {row.get('prioridad_energetica', 'N/A')}<br>"
            f"Tipo de ubicacion: {row.get('precision_ubicacion', 'N/A')}<br>"
            f"Latitud usada: {float(row.get('latitud', 0) or 0):.4f}<br>"
            f"Longitud usada: {float(row.get('longitud', 0) or 0):.4f}<br>"
            f"<span style='color:#666;'>La fuente no trae municipio ni coordenada exacta de planta.</span>"
        )
        folium.Marker(
            location=[row["latitud"], row["longitud"]],
            popup=folium.Popup(popup_html, max_width=280),
            icon=folium.Icon(color="blue", icon="flash", prefix="fa"),
        ).add_to(cluster)
    cluster.add_to(base_map)



def add_hydraulic_cluster(base_map: folium.Map, hydraulic_gdf, show: bool = True) -> None:
    cluster = MarkerCluster(name="Activos hidraulicos", show=show)
    for _, row in hydraulic_gdf.iterrows():
        popup_html = (
            f"<b>{row.get('nombre_activo', 'Activo hidraulico')}</b><br>"
            f"Departamento: {row.get('departamento', 'N/A')}<br>"
            f"Municipio: {row.get('municipio', 'N/A')}<br>"
            f"Capacidad hidraulica: {row.get('capacidad_hidraulica', 0)}"
        )
        folium.Marker(
            location=[row["latitud"], row["longitud"]],
            popup=folium.Popup(popup_html, max_width=280),
            icon=folium.Icon(color="green", icon="tint", prefix="fa"),
        ).add_to(cluster)
    cluster.add_to(base_map)



def add_pressure_layer(base_map: folium.Map, demand_gdf) -> None:
    pressure_group = folium.FeatureGroup(name="Presion energetica", show=False)
    for _, row in demand_gdf.iterrows():
        folium.Circle(
            location=[row["latitud"], row["longitud"]],
            radius=max(float(row.get("demanda_futura", 0)) * 2, 5000),
            color="#ff7f00",
            fill=True,
            fill_opacity=0.15,
            popup=folium.Popup(
                (
                    f"<b>{row.get('departamento', 'N/A')}</b><br>"
                    f"Demanda futura: {row.get('demanda_futura', 0):.2f}<br>"
                    f"Consumo energetico: {row.get('consumo_energetico', 0):.2f}"
                ),
                max_width=280,
            ),
        ).add_to(pressure_group)
    pressure_group.add_to(base_map)
