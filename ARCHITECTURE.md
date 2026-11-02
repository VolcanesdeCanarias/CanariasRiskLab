# Arquitectura integrada · ADR-001

## Estado real de esta entrega

Flask sigue siendo el núcleo (`server.py`), conservando `/`, seis API y la interfaz heredada. `risklab_next` añade un Blueprint con contratos versionados `/api/v1/*` y `/next/`; no modifica el arranque Render. `next/` contiene aplicación luminosa modular, Leaflet 1.9.4 y componente Earth/Cesium 1.146.0. Dependencias npm fijadas con lockfile, servidas desde directorios de distribución explícitos. No hay un backend independiente Earth.

Adaptadores P0 IGN/USGS → normalización → asignación por polígonos → instantánea inmutable SQLite → método `descriptive-counts/1.0` → plantilla explicativa y CSV/JSON. La instantánea incorpora respuesta normalizada, calidad, cobertura nominal, tiempo de adquisición y SHA-256; su ID cambia con cualquiera de esos contenidos. No se archivan aún los bytes originales HTML/GeoJSON. Se conserva el identificador y el datetime original de cada registro. No se reconcílian ni suman catálogos.

GET `/api/v1/catalog`: ocho islas/mar, 88 municipios, capacidades, referencias y estado oficial no verificado. GET `/api/v1/observations/IGN|USGS`: adquisición/caché 60 s, calidad available/empty/unavailable, fuente, limitaciones y snapshot_id (503 ante fallo). GET `/api/v1/analysis/{snapshot_id}`: parámetros UTC `from`, `until` excluido, `territory`, `min_mag`; resultados, comparación de duración idéntica y explicación con evidencia. `format=csv` exporta esa selección; fallo nunca exporta cero. GET `/api/v1/territory-outlines`: derivado muestreado solo para representación. GET `/api/v1/institutional/*`: 403 hasta configurar autorización real. Los datos no son restringidos; no cargar información sensible en este prototipo.

SQLite es un adaptador local transitorio, fuera de rutas públicas. Caché acotada a dos fuentes, bloqueo por fuente, sin fallback silencioso ante fallo. Persistencia no tiene todavía política de retención/cuotas/backup: no apta para servicio público continuo. Dos procesos pueden adquirir distintas instantáneas; dentro de cada análisis solo se usa una. No hay ingesta programada ni monitorización operativa todavía.

## Modelo objetivo

`Source` (operador/licencia/URL), `Acquisition` (HTTP/tiempos/estado/checksum), `RawObject` inmutable, `DatasetVersion`, `Observation` (variable/unidad/CRS/referencia vertical/incertidumbre), `Station`, `Territory`, `VolcanicSystem`, `Asset`, `MethodVersion`, `AnalysisRun` (dataset+parámetros+código+salida), `Evidence`, `Document` (emisor/fecha/vigencia), `Scenario`, `Review`, `Decision` y `AuditEvent`.

Evolución: PostgreSQL/PostGIS para geometrías/consultas; almacenamiento de objetos originales con checksums y retención; workers de adquisición programada y colas con reintentos/backoff; API común paginada, consulta temporal/espacial indexada; OpenAPI, exportaciones GeoJSON/CSV/GeoPackage según licencia. Cada capa declara resolución y disponibilidad por territorio. Guardar tiempos de observación, publicación y adquisición por separado.

## Análisis e IA

Registro de métodos versionados con entradas/salidas validadas, semillas si proceden y ejecución reproducible. Legado experimental aislado y disponible, sin cambiar sus fórmulas en esta entrega. Cambios estadísticos requieren catálogo completo, baseline independiente, sensibilidad, backtesting y revisión científica.

La explicación temprana es una plantilla determinista, no un LLM. Futuro asistente: plan de consulta validado → herramientas autorizadas de solo lectura → AnalysisRun → recuperación documental con metadatos de vigencia → respuesta con citas → verificadores numéricos/abstención → revisión humana para uso institucional. Sin ejecución arbitraria, documentos tratados como datos no instrucciones, sin órdenes de emergencia ni niveles inventados. Pruebas de alucinaciones, contradicciones, inyección documental y lenguaje alarmista/tranquilizador. No agentes autónomos sin beneficio medido.

## Seguridad y disponibilidad objetivo

Autenticación OIDC y autorización de servidor por ámbito/rol; separación de datos públicos/restringidos, minimización, auditoría de accesos/exportaciones, revisión/publicación explícitas. CSP y cabeceras, rate limiting, límites de consulta, CSRF para mutaciones, gestión de secretos, revisión de dependencias, backup/restauración y observabilidad antes de exposición pública. No se presentan como ya implementados. El prototipo se ejecuta con servidor local 127.0.0.1.

## Cartografía

Earth es un adaptador de representación de las mismas observaciones. Cesium utiliza ahora elipsoide WGS84 y contornos muestreados; coordenada vertical de hipocentros = −profundidad de catálogo es aproximación visual sin transformación de datum. No hay batimetría ni relieve validado en NEXT. V2.1 conserva sus activos privados sin cambios. Integrar MDT/imagen solo al acreditar licencia, cobertura, resolución y transformación vertical. La Graciosa se identifica mediante componente del multipolígono Teguise al norte de 29.20 y oeste de −13.40; regla de selección documentada, pendiente de validación cartográfica, no límite oficial nuevo.
