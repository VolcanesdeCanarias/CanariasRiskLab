# Primera intervención P0: seguridad y fiabilidad de datos

Base auditada: `647bec9544e2bc2fbee36731e850cca60b685c2a`.
Rama: `fix/p0-security-data-reliability`.

## Alcance

Se conserva Flask, el visor Leaflet, las seis API y todos los indicadores.
Las funciones científicas no se modifican. Una prueba compara sus AST con el
commit auditado, incluidas las funciones de agrupación, puntuación, ventanas y
clasificación geográfica. No se añaden datos simulados al código de producción:
las respuestas sintéticas se generan exclusivamente en las pruebas.

## Archivos públicos

Flask ya no registra la ruta estática automática. `/` sirve `index.html` y la
ruta de recursos solo admite estos nombres exactos, desde el directorio de la
aplicación, independientemente del directorio de ejecución:

- `index.html`
- `municipios_canarias.geojson`
- `la_palma_exclusion15ene26.geojson`
- `ign_instrumentation.json`
- `catalogo.kmz`

Los dos últimos se mantienen como recursos públicos existentes; la
instrumentación también sigue disponible por API. No se permite publicar
automáticamente ningún archivo nuevo. Código, requisitos, configuración,
pruebas, documentación, rutas ocultas, `.git` y rutas con segmentos adicionales
devuelven 404. No se cambia el catálogo geográfico ni el KMZ.

## Contrato de adquisición

Las respuestas de IGN, USGS, bundle y clusters incorporan `data_status`:

- `available`: adquisición y validación correctas con eventos.
- `empty`: adquisición y validación correctas sin eventos en el catálogo
  devuelto por la API de esa fuente; no es un fallo de conexión.
- `unavailable`: fallo de adquisición, validación o cálculo. No se puede
  inferir ausencia de actividad. `count` es `null`.

`checked_at` indica cuándo se completó o intentó la adquisición; no certifica
la fecha del último evento ni la vigencia de PEVOLCA. En el bundle el estado y
conteo se refieren al catálogo IGN adquirido antes de aplicar los filtros.
`ign_eventos` sigue respetando el filtro seleccionado. USGS utiliza el área
regional ya existente y su feed de 24 horas.

Los errores HTTP de origen, incluidos 403, 429 y 5xx, se devuelven como 502 con
`error_code: http_error` y `data_status.upstream_status`. Los timeouts devuelven
504; los fallos de conexión y validación, 502. Un fallo interno devuelve 500 con
un mensaje genérico. Se registran fuente, código y estado HTTP, sin volcar
cuerpos externos, credenciales ni detalles internos al cliente.

Los arrays vacíos de una respuesta de error son contenedores compatibles, no
resultados científicos. El cliente debe comprobar `ok` y `data_status` antes de
interpretarlos. Los indicadores e interpretación del bundle son `null` ante un
fallo; los focos tienen conteo `null` y una lectura de no evaluación.

## Validación de fuentes

IGN requiere HTTP 200, Content-Type HTML y una tabla con los encabezados de
evento, fecha, hora UTC, coordenadas, profundidad, magnitud, tipo y localización.
Se leen las columnas por encabezado, evitando confundir intensidad y magnitud.
Se comprueban fechas, ID, duplicados, valores finitos y rangos físicos amplios.
Una sola fila incompleta invalida el catálogo entero: no se publican estadísticas
parciales como si la adquisición fuera completa.

Las fechas futuras tienen una tolerancia de cinco minutos. Si el evento más
reciente tiene más de once días, el catálogo de diez días se declara
desactualizado; el margen permite diferencias de día natural. Esto es una
condición de calidad de entrada, sin modificar las ventanas ni fórmulas.

Una tabla sin filas no basta para afirmar que no hubo terremotos. Solo se acepta
una fila explícita con uno de estos mensajes normalizados:
`No se han encontrado terremotos`, `No hay terremotos`, `No hay eventos`.
Se admite un punto final. Un mensaje junto con eventos es contradictorio y se
rechaza. El formato vacío real del proveedor no se pudo observar en la consulta
de validación; si cambia, se mostrará indisponibilidad hasta revisar el parser.

USGS comprueba HTTP antes de leer JSON, Content-Type, FeatureCollection,
metadatos de estado y conteo, geometrías Point y campos numéricos/temporales.
La generación del feed debe estar dentro de las últimas dos horas, con la misma
tolerancia futura de cinco minutos. Se valida el catálogo antes de filtrar la
región; una respuesta inválida no se convierte en cero eventos regionales.

## Interfaz

Se añaden mensajes de estado accesibles al panel de fuentes. No se rediseña el
visor. Durante una adquisición y ante errores se eliminan los resultados IGN
anteriores; las tarjetas, gráficos y popups dejan de presentar ceros o frases
tranquilizadoras como resultados de una adquisición fallida.

USGS, instrumentación y estado oficial se solicitan independientemente del
bundle. Un fallo IGN no impide representarlos. Un fallo USGS se muestra como
indisponibilidad, separado del resultado válido sin eventos. Un contador de
solicitudes impide que una respuesta antigua sobrescriba los datos del filtro
actual. Los mensajes externos de error se insertan con `textContent`.

## Pruebas reproducibles

Requisitos: Python 3.12 con `requirements.txt` instalado y Node.js 24.
Desde la raíz del repositorio:

```sh
python -B -m unittest discover -s tests -v
node tests/frontend_data_status.test.cjs
git diff --check
```

La prueba de preservación científica necesita el commit auditado disponible en
Git. El workflow usa `fetch-depth: 0`. Las pruebas de regresión no necesitan
acceso a IGN ni USGS; usan mocks en memoria y el cliente de pruebas Flask. Las
pruebas JavaScript ejecutan funciones reales del visor con un arnés DOM/red; no
sustituyen una comprobación visual completa en navegador.

Resultados locales del 1 de noviembre de 2026:

- 26 pruebas Python: correctas.
- 9 pruebas JavaScript: correctas.
- Sintaxis JavaScript, identificadores DOM y preservación de funciones
  científicas: correctas.
- Consultas reales mediante el cliente Flask: IGN, USGS, bundle y clusters
  respondieron HTTP 200. IGN: 19 eventos validados. USGS: cero regionales, con
  feed válido. El HTTP 403 no se reprodujo en vivo; sí se verifica con mocks.

## Riesgos y trabajo posterior

- IGN sigue dependiendo de HTML. La validación conservadora puede declarar
  indisponibilidad cuando cambie su estructura o falten parámetros publicados.
- Un HTML que conserve eventos recientes no acredita por sí solo que el
  proveedor esté actualizado; no se dispone de una marca de generación fiable
  del catálogo IGN. No se introduce una caché ni un servicio histórico en P0.
- Se conservan los problemas metodológicos auditados: cobertura de diez días
  para indicadores etiquetados 30d, baseline, puntuación vacía de 9, agrupación
  experimental, municipios y exposición. Una adquisición vacía validada sigue
  utilizando las fórmulas originales.
- PEVOLCA continúa siendo una transcripción manual. Sus fechas y colores no se
  modifican en esta intervención. Tampoco se modifica la escala experimental.
- La sanitización general de popups, dependencias y otros hallazgos de seguridad
  ajenos a la exposición de archivos quedan pendientes.
- La lista permitida debe actualizarse expresamente si se añaden recursos
  públicos. Cualquier servidor frontal o almacenamiento externo que publique
  directamente la raíz del repositorio debe restringirse por separado.

Este cambio se prepara para revisión por pull request. No incluye fusión con
`main`, despliegue ni cambios en Render.
