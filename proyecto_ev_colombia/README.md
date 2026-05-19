# Proyecto EV Colombia

Pipeline local para pronosticar adopcion de vehiculos electricos en Colombia, traducir esa proyeccion a demanda energetica y priorizar territorios usando una capa hidraulica de soporte.

## Alcance oficial

El flujo base usa solo dos fuentes oficiales:

- `data/raw/datos_abiertos_EV_colombia_realista.xlsx`
  - fuente para ETAPA 1 y ETAPA 2
  - alimenta el modelo temporal y el modelo energetico
- `data/raw/PARATEC_Phidráulica_18-05-2026.xlsx`
  - fuente para ETAPA 3
  - alimenta la capa hidraulica para mapas y priorizacion territorial

`infraestructura_generacion_86_registros.xlsx` queda fuera del flujo base actual. Puede reincorporarse despues si se quiere ampliar el analisis a solar y termica.

## Flujo actual

1. Carga de Excel crudos a SQL.
2. ETAPA 1: forecast EV por `anio + departamento + tipo_vehiculo`.
3. ETAPA 2: calculo de `consumo_energetico` y `demanda_futura`.
4. ETAPA 3: priorizacion territorial con soporte hidraulico de PARATEC.
5. Exportacion de tablas procesadas y mapas HTML.

## Base de datos

La fuente operativa del pipeline es SQL, no los Excel directos.

- motor por defecto: MySQL local
- base por defecto: `proyecto_ev_colombia`
- URL por defecto: `mysql+pymysql://root@127.0.0.1/proyecto_ev_colombia`

Puedes sobrescribirla con la variable de entorno `DATABASE_URL`.

Tablas oficiales de carga:

- `vehiculos_ev`
- `activos_hidraulicos`

La carga SQL crea la base si no existe y reemplaza estas tablas en cada ejecucion.

## Estructura relevante

- `main.py`: orquestacion principal
- `src/load_data.py`: carga de Excel a SQL y acceso a tablas fuente
- `src/build_phase_tables.py`: construccion de ETAPA 1, ETAPA 2 y ETAPA 3
- `src/train_temporal_baseline.py`: entrenamiento del baseline temporal
- `src/gis/loaders.py`: carga geoespacial para mapas
- `src/maps/generate_maps.py`: exportacion de mapas HTML
- `config/scenarios.yaml`: escenarios de simultaneidad y horizontes
- `config/weights.yaml`: pesos del indice territorial

## Requisitos

- Python 3
- MySQL local accesible
- dependencias de `requirements.txt`

Instalacion recomendada:

```bash
python3 -m pip install -r requirements.txt
```

## Ejecucion

Desde la raiz de `proyecto_ev_colombia`:

```bash
python3 main.py --forecast-horizons 5 10 15 20 30
```

Opciones utiles:

```bash
python3 main.py --skip-maps
python3 main.py --scenario alto
python3 main.py --simultaneidad 0.4
python3 main.py --forecast-horizons 5 10 15 20 30
```

Notas:

- `main.py` copia archivos crudos a `data/raw/`, carga SQL y luego corre el pipeline.
- el flag `--load-postgres` quedo como legado de la version anterior y ya no define el flujo principal.

## Salidas principales

Tablas en `data/processed/`:

- `etapa1_temporal.csv`
- `etapa1_temporal_predicciones.csv`
- `forecast_ev.csv`
- `etapa2_energetico.csv`
- `demanda_energetica.csv`
- `etapa3_gis.csv`
- `priorizacion_territorial.csv`
- `priorizacion_territorial.geojson`

Mapas en `maps/`:

- `mapa_prioridad.html`
- `mapa_demanda.html`
- `mapa_hidraulicas.html`
- `mapa_presion_energetica.html`
- `mapa_demanda_futura.html`
- `mapa_prioridad_territorial.html`

## Validacion rapida

Verificar tablas SQL:

```bash
mysql -u root -D proyecto_ev_colombia -e "SHOW TABLES;"
mysql -u root -D proyecto_ev_colombia -e "SELECT COUNT(*) AS vehiculos_ev FROM vehiculos_ev;"
mysql -u root -D proyecto_ev_colombia -e "SELECT COUNT(*) AS activos_hidraulicos FROM activos_hidraulicos;"
```

Verificar sintaxis de modulos principales:

```bash
python3 -m py_compile src/load_data.py src/build_phase_tables.py src/gis/loaders.py src/maps/generate_maps.py main.py
```

## Estado metodologico

- ETAPA 1 usa forecasting supervisado con baseline temporal.
- ETAPA 2 usa un calculo tecnico parametrizado, no una caja negra pura.
- ETAPA 3 prioriza por demanda EV y soporte hidraulico territorial.
- La salida territorial debe interpretarse como priorizacion preliminar por departamento, no como ubicacion exacta de estacion.