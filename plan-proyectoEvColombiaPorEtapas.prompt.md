## Plan: Pipeline EV + PARATEC

La forma correcta de plantearlo, con el alcance ya aclarado, es esta: [proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx](proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx) queda como la fuente oficial para ETAPA 1 y ETAPA 2, y [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) queda como la fuente oficial para ETAPA 3. Asi el proyecto se sostiene metodologicamente, evita relaciones forzadas y mantiene un pipeline defendible de forecast EV, modelo energetico y analisis espacial.

**Objetivo central del proyecto**

El objetivo real del proyecto no es construir una plataforma GIS gigante, ni un data warehouse empresarial, ni modelar todo el SIN. El objetivo central es construir un pipeline hibrido y defendible que combine IA, ingenieria energetica y analisis espacial para priorizar territorios asociados al crecimiento futuro de vehiculos electricos.

Ese objetivo se concreta asi:
1. ETAPA 1: predecir crecimiento EV futuro usando `anio`, `departamento`, `tipo_vehiculo` y `cantidad_ev`.
2. ETAPA 2: transformar la proyeccion EV en `demanda_futura` y `consumo_energetico` usando `kwh_promedio`, `potencia_carga` y `simultaneidad`.
3. ETAPA 3: visualizar y priorizar territorialmente la demanda proyectada usando la capa hidraulica de PARATEC como soporte espacial y energetico.

**Principio de alcance**

La prioridad es mantener simplicidad metodologica. El valor del proyecto esta en el pipeline analitico y no en complejidad arquitectonica. Por eso no se requiere arquitectura empresarial, big data, nube distribuida ni microservicios.

**Stack ideal para este alcance**

| Componente | Tecnologia recomendada |
| --- | --- |
| Datos iniciales | Excel o CSV |
| Integracion operativa | MySQL local |
| IA | Python |
| GIS analitico | GeoPandas y Folium |
| Visualizacion cartografica | QGIS |

**Rol real de SQL y MySQL**

SQL no es el objetivo del proyecto, pero si es la fuente operativa oficial del pipeline. Los Excel se usan como insumo inicial de carga y trazabilidad. Despues de esa carga, el nucleo analitico en Python lee desde MySQL las tablas `vehiculos_ev` y `activos_hidraulicos`, porque ahi viven el forecasting, el modelo energetico, el GIS analitico y el analisis multicriterio.

**Pipeline analitico oficial**

Excel crudos  
↓  
Carga SQL oficial  
↓  
Datos EV historicos desde `vehiculos_ev`  
↓  
Forecast de crecimiento EV  
↓  
Modelo energetico  
↓  
GIS territorial con `activos_hidraulicos`  
↓  
Priorizacion territorial

**Naturaleza del proyecto por etapa**

| Etapa | Naturaleza principal |
| --- | --- |
| Forecast EV | IA |
| Energia | Ingenieria energetica parametrizada |
| GIS | Analisis espacial y multicriterio |

**Fase 0: Preparacion del dato y arquitectura**
1. Mantener `proyecto_ev_colombia/` con `data/raw`, `data/processed`, `notebooks`, `models`, `maps`, `requirements.txt` y `main.py`.
2. Configurar entorno local en macOS con `venv`, `pip`, VS Code y JupyterLab.
3. Copiar a `data/raw/` solo las dos fuentes oficiales del flujo base: [proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx](proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx) y [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx). Los demas archivos quedan como respaldo metodologico, no como dependencia del pipeline principal.
4. Cargar esas dos fuentes a MySQL local en la base `proyecto_ev_colombia`, usando como tablas oficiales `vehiculos_ev` y `activos_hidraulicos`.
5. Perfilar por separado ambas fuentes y validar su version ya cargada en SQL: columnas, tipos, nulos, granularidad temporal, granularidad geografica y variables energeticas.
6. Normalizar variables criticas: `anio`, `departamento`, `tipo_vehiculo`, `cantidad_ev`, `kwh_promedio`, `potencia_carga`, `simultaneidad`, `latitud` y `longitud`.
7. Generar tablas procesadas separadas para tiempo, energia y geografia en `data/processed/` leyendo desde SQL, no desde Excel directo.

**ETAPA 1: Modelo temporal**
1. Objetivo: predecir crecimiento futuro de EV por departamento y tipo de vehiculo.
2. Entradas minimas: `anio`, `departamento`, `tipo_vehiculo`, `cantidad_ev`, tomadas desde la tabla `vehiculos_ev`.
3. Unidad recomendada: departamento-anio-tipo de vehiculo.
4. Metodo recomendado: usar backtest temporal para comparar un baseline temporal puro, un baseline hibrido con variables energeticas y una proyeccion tendencial por grupo. Para los horizontes futuros, la salida oficial debe usar la proyeccion tendencial por grupo, porque permite extrapolar en el tiempo sin dejar forecast plano por horizonte.
5. Ingenieria de variables: rezagos, tasas de crecimiento y tendencia temporal, solo si el dato lo soporta.
6. Salidas: tabla proyectada de EV por territorio y horizonte, metricas y artefactos reproducibles.
7. Riesgo principal: si la historia temporal es corta, conviene presentar el resultado como proyeccion por escenarios o tendencias defendibles, no como forecasting fuerte.

**ETAPA 2: Modelo energetico**
1. Objetivo: convertir la proyeccion EV en `consumo_energetico` y `demanda_futura`.
2. Entrada obligatoria: salida formal de la ETAPA 1.
3. Variables tecnicas: `kwh_promedio`, `potencia_carga` y `simultaneidad`.
4. Metodo recomendado: modelo hibrido, no caja negra. La base debe ser calculo tecnico parametrizado por la proyeccion EV.
5. Diseñar escenarios bajo, medio y alto si `simultaneidad` no esta observada o es incierta.
6. Separar claramente energia y potencia: una responde a consumo acumulado; la otra a presion de carga o requerimiento de capacidad.
7. Salidas: tablas energeticas por departamento y periodo, sensibilidad por escenarios y supuestos documentados.
8. Riesgo principal: si faltan variables energeticas clave, reducir el alcance a escenarios tecnicamente plausibles.

**ETAPA 3: GIS y priorizacion territorial**
1. Objetivo: traducir resultados temporales y energeticos a decisiones espaciales.
2. Entradas: `departamento`, coordenadas y salidas de las etapas 1 y 2, junto con la tabla `activos_hidraulicos`, cargada originalmente desde [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx).
3. Metodo recomendado: empezar con mapas coropleticos por departamento y complementar con puntos de activos hidraulicos si hay coordenadas disponibles.
4. Herramientas: `folium` para reproducibilidad y QGIS para afinado cartografico.
5. Resultado esperado: mapa de demanda energetica proyectada, mapa de activos hidraulicos y mapa de prioridad territorial considerando la demanda EV y el soporte hidraulico observado.
6. La “estacion optima” debe presentarse como priorizacion multicriterio territorial, no como optimizacion exacta.
7. Riesgo principal: si solo hay resolucion departamental, no se debe prometer localizacion fina de estaciones.

**Metodologia formal de la ETAPA 3**
1. Definir la unidad espacial oficial del analisis. La recomendacion base es trabajar por departamento y escalar a puntos solo cuando las coordenadas de PARATEC sean utilizables.
2. Preparar las capas espaciales. Convertir la demanda proyectada de la ETAPA 2 y la capa hidraulica a una misma referencia territorial.
3. Construir los criterios de priorizacion. Como minimo deben entrar `demanda_energetica_proyectada`, `crecimiento_ev_proyectado` y un criterio de `soporte_hidraulico` derivado de capacidad o cercania a activos de PARATEC.
4. Estandarizar los criterios. Llevar todos los indicadores a una escala comparable, por ejemplo de 0 a 1.
5. Definir pesos del analisis multicriterio. La version inicial debe priorizar demanda proyectada y crecimiento EV, dejando el soporte hidraulico como factor complementario.
6. Calcular un indice de prioridad territorial. Combinar los criterios estandarizados en un puntaje sintetico por departamento.
7. Generar salidas cartograficas y analiticas. Producir mapas tematicos individuales por criterio, un mapa final del indice multicriterio y una tabla ranking de territorios priorizados.
8. Validar consistencia territorial. Revisar que las zonas con prioridad alta tengan sentido frente a la demanda proyectada y la oferta hidraulica observada.
9. Documentar limites del analisis. Si la resolucion espacial es departamental o faltan variables criticas, el resultado debe presentarse como priorizacion territorial preliminar.

**Tabla de variables: capa hidraulica**

| Variable | Unidad | Fuente | Transformacion | Uso analitico |
| --- | --- | --- | --- | --- |
| `nombre_activo` | texto | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Limpiar duplicados y variantes | Identificacion de infraestructura |
| `departamento` | categorica | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Normalizar nombres territoriales | Agregacion territorial |
| `municipio` | categorica | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Normalizar nombres territoriales | Contexto territorial adicional |
| `latitud` | grados | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Validar coordenadas | Georreferenciacion |
| `longitud` | grados | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Validar coordenadas | Georreferenciacion |
| `capacidad_hidraulica` | MW o equivalente | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Homologar unidad y completar nulos si es viable | Contexto de oferta energetica |
| `tipo_activo_hidraulico` | categorica | [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx) | Homologar categorias | Segmentacion de activos |

**Base de datos operativa**

- motor actual: MySQL local
- base oficial: `proyecto_ev_colombia`
- tablas fuente oficiales: `vehiculos_ev` y `activos_hidraulicos`
- rol de los Excel: insumo inicial de carga y trazabilidad
- rol de SQL: fuente operativa para ETAPA 1, ETAPA 2 y ETAPA 3

**Relevant files**
- [proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx](proyecto_ev_colombia/data/raw/datos_abiertos_EV_colombia_realista.xlsx): dataset maestro del flujo temporal y energetico.
- [proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx](proyecto_ev_colombia/data/raw/PARATEC_Phidráulica_18-05-2026.xlsx): capa hidraulica oficial para GIS y soporte energetico territorial.
- [proyecto_ev_colombia/src/build_phase_tables.py](proyecto_ev_colombia/src/build_phase_tables.py): punto central del pipeline por etapas.
- [proyecto_ev_colombia/src/train_temporal_baseline.py](proyecto_ev_colombia/src/train_temporal_baseline.py): entrenamiento y exportacion del forecast EV.
- [proyecto_ev_colombia/src/gis/loaders.py](proyecto_ev_colombia/src/gis/loaders.py): carga de puntos PARATEC y armado geoespacial.
- [proyecto_ev_colombia/src/maps/generate_maps.py](proyecto_ev_colombia/src/maps/generate_maps.py): generacion de mapas HTML.
- [proyecto_ev_colombia/src/load_data.py](proyecto_ev_colombia/src/load_data.py): carga SQL simplificada a dos tablas oficiales.
- [proyecto_ev_colombia/sql/schema.sql](proyecto_ev_colombia/sql/schema.sql): esquema SQL reducido a `vehiculos_ev` y `activos_hidraulicos`.

**Verification**
1. Confirmar que `datos_abiertos_EV_colombia_realista.xlsx` contiene o permite derivar las variables minimas de ETAPA 1 y ETAPA 2.
2. Confirmar que la base `proyecto_ev_colombia` existe en MySQL y que contiene `vehiculos_ev` y `activos_hidraulicos`.
3. Validar que ETAPA 1, ETAPA 2 y ETAPA 3 lean desde SQL y no desde Excel directo.
4. Validar que la ETAPA 1 use particion temporal y entregue proyecciones por departamento y tipo de vehiculo.
5. Validar que la ETAPA 2 diferencie correctamente entre `consumo_energetico` y `demanda_futura`.
6. Confirmar que ETAPA 1, ETAPA 2 y ETAPA 3 usan la misma unidad territorial y temporal cuando se agregan resultados.
7. Verificar que la capa PARATEC pueda alinearse espacialmente con la unidad geografica usada en GIS.
8. Probar en macOS la ejecucion completa del entorno y al menos un mapa exportado.

**Decisions**
- El flujo oficial es: ETAPA 1 temporal, ETAPA 2 energetica y ETAPA 3 GIS con PARATEC.
- La IA tiene sentido principalmente en ETAPA 1.
- ETAPA 2 debe ser predominantemente tecnica o hibrida.
- La ETAPA 3 usa PARATEC como soporte espacial y energetico oficial del flujo base.
- `infraestructura_generacion_86_registros.xlsx` queda fuera del alcance base y solo se reincorpora si se pide ampliar el analisis a solar y termica.
- MySQL local `proyecto_ev_colombia` es la fuente operativa oficial del pipeline.
- Los Excel quedan como insumo inicial de carga, no como fuente de lectura principal del modelo.
- El dashboard queda fuera del alcance inicial.

**Estado actual del proyecto**

1. La base MySQL local `proyecto_ev_colombia` ya existe.
2. Las tablas oficiales `vehiculos_ev` y `activos_hidraulicos` ya fueron cargadas correctamente.
3. El pipeline principal ya fue reorientado para leer desde SQL en vez de leer los Excel directos.
4. La capa de `infraestructura_generacion_86_registros.xlsx` ya no hace parte del flujo base oficial.
5. La documentacion base del proyecto ya fue actualizada para reflejar el flujo SQL-first con MySQL.
6. La corrida completa end-to-end con `main.py --forecast-horizons 5 10 15 20 30` ya se ejecuto correctamente y regenero tablas procesadas y mapas HTML.
7. La ETAPA 1 ya quedo cerrada operativamente: genera backtest, comparacion de modelos, metricas y forecast futuro con variacion real por horizonte.
8. La ETAPA 2 ya quedo cerrada operativamente: separa energia y potencia, conserva la tabla base del escenario operativo y exporta sensibilidad por escenarios `bajo`, `medio` y `alto`.
9. La ETAPA 3 ya quedo cerrada operativamente: el ranking territorial ahora prioriza demanda y brecha hidraulica, y exporta `validacion_etapa3.csv` para trazabilidad metodologica.

**Pendientes inmediatos para continuar**

1. Mantener sincronizados los dos archivos de plan (`plan-proyectoEvColombiaPorEtapas.prompt.md` y `planProyectoEvColombiaPorEtapas.prompt.md`) si el segundo vuelve a existir o se restaura.
2. Si se quiere ampliar el alcance, el siguiente paso ya no es cerrar etapas base sino extender el modelo con capas adicionales o dashboard.

**Siguiente accion recomendada**

La siguiente accion correcta es hacer una corrida final completa con `main.py` y revisar visualmente los mapas exportados como verificacion de cierre del pipeline base, porque ETAPA 1, ETAPA 2 y ETAPA 3 ya quedaron operativas sobre el flujo SQL-first con MySQL.