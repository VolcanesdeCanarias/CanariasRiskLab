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


## Revisión funcional 01 · 2026-11-02

Revisión01: view-state.mjs separa estado geográfico de consultas y calcula presupuesto Research con mínimo de mapa320px escritorio/250px móvil. Solo resize de vista visible, preservando pose/centro/zoom con reset explícito. Transiciones transfieren ámbito seguro sin alterar evento/filtros. Cambio físico de anchura reencuadra territorio; abrir panel no es ese evento.

Catálogo añade bounds por isla/municipio, fichas GVP, instrumentación manual no operativa verificada y registro fijo WMS. Método descriptive-counts/1.1 añade municipality_id/min_depth/max_depth compartidos en comparación/CSV. no_coverage mantiene count nulo y bloquea CSV. Normalización1.1 corrige componentes de Teguise; instantáneas antiguas conservadas.

cartography.mjs integra fuentes fijas sin proxy público. terrain.py lee derivado local fijo, presupuesto limitado, metadatos declarados y nodata. Cesium puede dibujar malla de LOD; no hay MDT real incluido, batimetría, transformación vertical ni colisiones contra esa malla. Ver TERRAIN-IMPORT.md.


## Revisión de producto 01 · 2026-11-02

Nuevo módulo research.py dentro del Blueprint Flask canónico: casos/catálogo históricos, POST ejecuciones, GET ejecución inmutable, consultas acotadas y exportaciones. Originales USGSGeoJSON/CSV/count+manifest versionados en risklab_next/data/research; loader estricto verifica checksums, reconciliación, rangos y nulos. Contexto científico separado en JSON, referencias primarias y relaciones tipadas sin causalidad. Geometría municipal conserva su hash y calidad heredada.

research_runs SQLite guarda resultados por hash de dataset/parámetros/contexto/método/código/geografía. Método catalogue-rates-spatial/1.0, especificación y CLI para repetición offline. Exportación allowlist HTML/CSV/JSON/ZIP, escapes/CSP y originales/checksums sin exponer archivos internos. research.mjs es un cuaderno en la misma aplicación, no un backend/prototipo independiente. Estado y datos históricos separados del IGN/USGS reciente: un fallo reciente no invalida evidencia archivada. Cambios de parámetros invalidan exportaciones/respuestas pendientes.

Asistencia determinista de herramientas por intención acotada, con rutas de evidencia; sin ejecución arbitraria, proveedor LLM o pago. Más fuentes/multiseñal, RAG y validación quedan posteriores. No se atribuye cobertura/certidumbre por existir una respuesta HTTP200.


## Salto funcional multinsular · 0.4 · 2026-11-02

Nuevo módulo `observatory.py` y cliente `observatory.mjs/css`, registrados por fachada `research.py`; API/servidor heredados intactos. `research_v1.py` conserva método0.3 y sus hashes. Archivo IGN inmutable + BDDAE con polígonos completos cacheados, originales completos privados locales; tablas públicas sin sesión y GeoJSON municipal transparente. SQLite guarda ejecuciones inmutables; exportaciones públicas acotadas. Sin backend institucional habilitado ni LLM.


## Actualización continua · 0.5 · 2026-11-03

El canal `risklab_next/continuous` añade conectores oficiales, planificación en servidor, ledger SQLite WAL privado, versiones inmutables y API analítica reproducible. `abrir.py` inicia el recolector; un supervisor independiente prepara una futura instancia Render con disco compartido entre web y worker. No se ha desplegado. [Diseño y operación](docs/next/CONTINUOUS-01.md).
