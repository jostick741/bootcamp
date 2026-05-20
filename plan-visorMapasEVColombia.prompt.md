## Plan: Visor GIS EV Colombia

Este plan no redefine el pipeline analitico. Parte de una base ya cerrada: ETAPA 1, ETAPA 2 y ETAPA 3 ya generan tablas y mapas. El problema que queda no es de calculo sino de entrega visual. Los mapas actuales salen como HTML separados y no se entienden como producto. La solucion correcta es convertir la salida cartografica en un visor unico, inspirado en la experiencia de PARATEC, pero adaptado al objetivo real del proyecto: demanda EV, presion energetica y priorizacion territorial.

**Objetivo del visor**

El objetivo del nuevo visor no es mostrar todos los mapas a la vez. El objetivo es ofrecer una sola interfaz donde el usuario pueda:

1. elegir que mapa analitico quiere ver;
2. filtrar el escenario temporal cuando el mapa lo requiera;
3. activar o desactivar capas de apoyo sin ensuciar la lectura principal;
4. entender para que sirve cada vista sin tener que abrir seis HTML distintos.

**Problema actual que resuelve este plan**

1. Los mapas se entregan como archivos sueltos sin una interfaz dominante.
2. El mapa principal no expone bien los anos proyectados como control visible y obvio.
3. Se mezclan capas auxiliares con la capa principal y se vuelve confuso leer el resultado.
4. La salida no responde a una logica de visor, sino a una logica de exportacion tecnica.
5. La narrativa GIS no esta alineada con la pregunta real del proyecto: donde se concentra la demanda EV futura y que territorios deben priorizarse.

**Principio de diseno**

El visor debe parecer una herramienta de consulta, no un conjunto de notebooks renderizados en HTML. La referencia valida es una interfaz tipo PARATEC:

1. un solo lienzo de mapa;
2. una barra superior de seleccion de vista;
3. un bloque claro de filtros solo para la vista activa;
4. una leyenda compacta por lado;
5. capas auxiliares apagadas por defecto;
6. interaccion guiada por seleccion, no por superposicion de elementos irrelevantes.

**Mapa principal y vistas oficiales**

El visor debe reducir la experiencia base a cuatro vistas oficiales:

1. `Demanda futura por anio`
   Usa la salida de ETAPA 2 y es la vista principal para explorar historico + proyeccion.
2. `Presion energetica`
   Muestra el consumo energetico agregado por departamento.
3. `Prioridad territorial`
   Muestra el indice final multicriterio de ETAPA 3.
4. `Soporte hidraulico`
   Muestra activos hidraulicos observados como capa de consulta y contraste.

Los mapas `vista combinada` y `heatmap exploratorio` deben salir de la portada principal y quedar como secundarios o fuera del visor inicial.

**Controles del visor**

La interfaz debe tener una banda superior con botones o tabs, no un listado de links.

Botones principales de seleccion de mapa:

1. `Demanda futura`
2. `Presion energetica`
3. `Prioridad territorial`
4. `Soporte hidraulico`

Cada boton debe cambiar el iframe o la vista principal del mapa sin obligar a abrir otra pagina manualmente.

**Filtros por vista**

Los filtros no deben ser globales si no aplican a todas las vistas.

### Vista 1: Demanda futura

Controles requeridos:

1. `Select de anio`
   Debe mostrar como opciones visibles: `2010-2022` historicos y `2027, 2032, 2037, 2042, 2052` proyectados.
2. `Botones rapidos de anos proyectados`
   Deben estar visibles: `2027`, `2032`, `2037`, `2042`, `2052`.
3. `Select de departamento`
   Opcional, para centrar o resaltar un territorio especifico.
4. `Switch de etiquetas`
   Apagado por defecto.

Comportamiento:

1. si el usuario cambia el anio, cambia el color del coropletico;
2. si elige un departamento, el mapa se centra y resalta;
3. las capas auxiliares deben permanecer ocultas salvo activacion expresa.

### Vista 2: Presion energetica

Controles requeridos:

1. `Select de anio`
   Debe ofrecer anos disponibles para que el usuario compare historico vs proyeccion.
2. `Select de departamento`
   Para enfocar la lectura territorial.
3. `Switch de etiquetas`
   Apagado por defecto.

### Vista 3: Prioridad territorial

Controles requeridos:

1. `Select de anio o escenario base`
   Si la salida final sigue siendo el ultimo anio del escenario base, debe indicarse claramente como `2052 - escenario base`.
2. `Select de categoria`
   `Alta`, `Media`, `Baja`.
3. `Select de departamento`
   Para buscar o centrar un caso.
4. `Switch de activos hidraulicos`
   Apagado por defecto.

### Vista 4: Soporte hidraulico

Controles requeridos:

1. `Select de departamento`
2. `Select de municipio` si el dato lo soporta.
3. `Filtro de capacidad hidraulica`
   Rango o categorias simples.
4. `Switch de etiquetas`
   Apagado por defecto.

**Componentes visuales obligatorios**

1. Un panel superior de tabs o botones de vista.
2. Un panel horizontal de filtros solo para la vista activa.
3. Una leyenda compacta a la derecha.
4. Un mapa grande y limpio en la parte central.
5. Un pequeño bloque textual fuera del mapa que diga:
   `Que muestra esta vista` y `Para que sirve`.

Ese bloque explicativo no debe ir flotando sobre el mapa como panel grande. Debe vivir en la interfaz del visor, no encima del lienzo geografico.

**Reglas de experiencia de usuario**

1. El usuario debe poder entender la vista activa en menos de 5 segundos.
2. Los anos proyectados deben verse sin necesidad de mover un slider escondido abajo.
3. Ninguna capa auxiliar debe venir activada si tapa la capa principal.
4. Las etiquetas no deben activarse por defecto.
5. La leyenda debe hablar en lenguaje analitico, no en nombres internos del pipeline.

**Arquitectura tecnica recomendada**

La forma pragmatica de implementarlo es esta:

1. Mantener los mapas HTML base generados por Folium.
2. Reemplazar `maps/index.html` por un visor real con:
   - tabs de vista;
   - iframe principal;
   - toolbar de filtros;
   - sincronizacion de query params hacia el mapa activo.
3. Hacer que los mapas Folium acepten parametros por URL cuando aplique:
   - `?anio=2027`
   - `?departamento=ANTIOQUIA`
   - `?categoria=ALTA`
4. Dejar la logica de datos en Python y la logica de interaccion del visor en HTML + CSS + JS simple.

**Archivos objetivo para la implementacion**

1. `proyecto_ev_colombia/src/maps/generate_maps.py`
   Para producir el nuevo `index.html` como visor y no como simple listado.
2. `proyecto_ev_colombia/src/maps/folium_builders.py`
   Para leer parametros de URL y limpiar overlays por defecto.
3. `proyecto_ev_colombia/maps/index.html`
   Como salida final del visor generado.

**Fases de implementacion del visor**

### Fase A: Replantear el entregable

1. Convertir `maps/index.html` en visor unico.
2. Reducir vistas oficiales a cuatro.
3. Eliminar del landing los mapas secundarios o moverlos a una seccion `exploratoria`.

### Fase B: Control temporal real

1. Hacer visible el `select de anio` en la vista `Demanda futura`.
2. Mostrar botones directos `2027, 2032, 2037, 2042, 2052`.
3. Sincronizar seleccion de anio con el mapa por URL o por script del iframe.

### Fase C: Filtros territoriales

1. Agregar `select de departamento` para las vistas relevantes.
2. Resaltar y centrar el territorio elegido.
3. Asegurar que los filtros no rompan el HTML exportado offline.

### Fase D: Limpieza visual

1. Quitar paneles grandes flotando sobre el mapa.
2. Apagar etiquetas por defecto.
3. Apagar capas auxiliares por defecto.
4. Reducir la cantidad de colores simultaneos visibles por vista.

### Fase E: Validacion de producto

1. Verificar que un usuario entienda `que mapa esta viendo` sin leer codigo.
2. Verificar que el anio proyectado se pueda cambiar desde un control visible.
3. Verificar que la vista `Prioridad territorial` no mezcle capas que oculten la decision principal.

**Criterios de aceptacion**

1. Existe un solo `maps/index.html` que funciona como visor principal.
2. La vista `Demanda futura` muestra un `select de anio` visible y botones de anos proyectados.
3. Cada vista tiene solo los filtros que necesita.
4. Las capas auxiliares salen apagadas por defecto.
5. El usuario puede distinguir claramente entre demanda, presion, prioridad y soporte hidraulico.
6. El visor se entiende como producto final, no como carpeta de HTML sueltos.

**Fuera de alcance de este plan**

1. Rehacer el pipeline analitico de ETAPA 1, ETAPA 2 o ETAPA 3.
2. Migrar el visor a React o framework pesado si HTML + JS simple resuelve el objetivo.
3. Copiar literalmente PARATEC. La referencia es de interaccion, no de replica exacta.

**Resultado esperado**

El entregable final debe sentirse como un visor GIS operativo del proyecto EV Colombia: un mapa central, tabs claros, filtros utiles, anos proyectados visibles y una lectura inmediata de para que sirve cada vista.