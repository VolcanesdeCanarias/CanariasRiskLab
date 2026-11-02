# Revisión de entrega · 0.1.0 · 2026-11-02

Primera integración funcional para revisión local, **no plataforma completa ni preparada para publicación operativa**. Rama `integration/next-phase1`, basada en P0 `ac9ff9c207625426e34ac047997d391c149a10a0`. No cambia main, el PR #1, Earth o Render. La arquitectura y las capacidades previstas están diferenciadas de código implementado en los diez documentos maestros.

## Cambios demostrables

- Flask canónico y seis APIs originales conservados; `/` mantiene la aplicación heredada. `/next/` añade interfaz luminosa con fuente sans serif de sistema, filtros, mapa principal y cinco áreas con estado real de disponibilidad.
- API común para ocho islas y mar, registro de los 88 municipios (recupera cinco omitidos en listas antiguas), asignación por polígonos y referencia de versión/checksum del GeoJSON. La Graciosa se identifica por componente de Teguise; regla pendiente de revisión SIG. No asigna municipios a sismos marinos por cercanía.
- Adquisición P0, caché de 60 s por fuente e instantáneas normalizadas inmutables en SQLite; análisis por ID, método y parámetros UTC. No almacena aún respuestas crudas, no hay scheduler/PostGIS/backup operativo.
- Distingue vacío válido, fuente fallida, filtros vacíos y cobertura parcial. Conteo nulo y explicación de abstención ante fallo; no publica índice ni falsa tranquilidad. USGS nulo permanece nulo en el nuevo contrato, sin cambiar respuesta antigua por defecto.
- Comparación descriptiva de periodos iguales, con validación de cobertura nominal; CSV/JSON vinculados al resultado completo, no al cursor. No reconcilia ni suma IGN y USGS.
- Plantillas explicativas con evidencia, no LLM ni IA predictiva. Ciudadanía/Investigación comparten exactamente los resultados; espacio institucional no configurado, con 403 de servidor.
- Leaflet 2D y componente Earth/Cesium 3D elipsoidal con hipocentros y fichas, profundidad/datum aproximados explícitos. Sin MDT ni imagen privada redistribuidos. Las herramientas completas Earth V2.1 siguen intactas en su repositorio.
- Research ajustable por puntero/teclado, minimizar/cerrar sin desplazar posición 2D o cámara 3D. La prueba detectó desplazamiento 2D y se corrigió utilizando la actualización de tamaño que conserva el centro.
- Capas opcionales de 11 referencias volcánicas y 32 equipamientos heredados, siempre no verificados. Tagoro no se dibuja hasta resolver coordenadas discrepantes; original preservado. No se muestran PEVOLCA manual antiguo o exclusión histórica como comunicación vigente.

## Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| Python `python -m unittest discover -s tests -p 'test_*.py' -q` | **41/41** (28 P0 + 13 nuevos) |
| JS `node tests/frontend_data_status.test.cjs` | **9/9** |
| Navegador legado `node tests/browser/review.cjs` | **10/10**, un caso live opcional omitido (no cuenta como aprobado) |
| Navegador NEXT `node tests/next/browser.cjs` | **11/11** |
| `git diff --check` | Sin errores |
| Hash de index.html, 4 datos originales y render.yaml | Idénticos a base P0; prueba y manifiesto INTEGRITY.json |
| Métodos científicos heredados | Prueba AST existente sin cambios respecto al commit auditado |

Total: **71 comprobaciones automatizadas aprobadas**, más revisión local live. Python 3.12.14, Node 24, Chromium 154.0.8037.57 en Linux con SwiftShader (no equivale a rendimiento GPU real de Mac). Pruebas browser incluyen selección de evento, perfiles numéricamente iguales, filtros rápidos, vacío IGN, errores 403 IGN/USGS y recuperación, mapas 2D/3D, estabilidad al abrir/redimensionar/minimizar/cerrar Research, móvil sin desbordamiento, reproducción y descarga JSON. Fixtures solo en tests, nunca en producción. CI preparada, ejecución remota pendiente de GitHub tras abrir PR.

Para repetir navegador usa `npm ci`, `npm ci --prefix tests/browser`, `npx playwright install chromium` y las órdenes anteriores; `CHROMIUM_PATH` permite Chromium del sistema. Los logs adjuntos conservan advertencias esperadas de fuentes simuladas fallidas. La prueba opcional live requiere levantar `RISKLAB_NO_BROWSER=1 RISKLAB_PORT=8790 python3 abrir.py` y ejecutar `node tools/review_next.cjs`.

## Prueba real sin sustitución de respuestas

IGN respondió con **20 registros** en adquisición de 2026-11-02T14:48:45Z, **4** seleccionados en últimas 24 horas. Se comprobaron mapa, Research y exportaciones con evidencia; capturas no usan datos sintéticos. USGS respondió HTTP 200, estado **empty**, recuento regional 0 en adquisición 2026-11-02T14:50:42Z: no se interpretó como prueba de ausencia de actividad. Estos resultados describen solo esas ejecuciones, no un estado actual garantizado.

Las teselas OSM no cargaron en el navegador de este entorno (**0 teselas**), por lo que se ven los contornos derivados del GeoJSON. No se sustituyeron por una imagen inventada ni se atribuye la limitación a una causa HTTP específica sin evidencia. Hay conectividad de adquisición real IGN/USGS, no prueba completa de la base cartográfica externa. Ver LIVE-EVIDENCE.json.

Capturas reales: [escritorio](captures/desktop-live.png), [Research](captures/research-live.png), [3D](captures/earth-live.png), [móvil](captures/mobile-live.png). Muestran la implementación real; no son renders de diseño. El 3D es elipsoidal sin relieve validado. La ausencia de MDT es una limitación material, no una funcionalidad terminada.

## Rendimiento inicial

Análisis descriptivo sobre los **13.573 registros reales candidatos** del Earth local, sin incorporarlos al runtime público: 30 ejecuciones, mediana **6,89 ms**, máximo **8,81 ms** en este entorno; selección última jornada del candidato: 4 registros. Únicamente mide el núcleo descriptivo, no adquisición, render de miles, lectura SQLite, completitud ni hardware Mac. Repetible con `python tools/benchmark_next.py --events /ruta/a/data/events.json`; no incluye ese archivo privado. Ver PERFORMANCE.json.

Carga live hasta resultado y espera visual: 4,815 s en ejecución registrada, incluyendo 1,2 s de espera deliberada. No se presenta como benchmark normalizado. No se midieron FPS ni render 13k en Mac/móvil real. El render 2D actual recrea marcadores al mover el cursor; pendiente de medir y optimizar con render incremental/nivel de detalle antes de habilitar históricos completos. El backend no modifica recuentos por densidad visual.

## Riesgos y siguiente trabajo

**Bloquean exposición pública:** revisión XSS de popups heredados, límites/rate limiting y endurecimiento, persistencia cruda/retención/cuotas/backup, revisión de dependencias Python no fijadas, permisos de datos/cartografía y validación de fuentes/vigencia. El servidor de revisión escucha solo 127.0.0.1; no es despliegue.

**Pendientes funcionales:** migrar capas/gráficos/filtros avanzados restantes, históricos validados, navegación municipal/área/coordenadas, fichas volcánicas documentadas, MDT/batimetría licenciados, GNSS/InSAR/gases, autenticación institucional, escenarios, LLM/RAG y validación científica avanzada. Las funciones originales siguen disponibles en legado; eso no equivale a migración completa. El logotipo oficial no está disponible: incorporación preparada/documentada en next/brand/README.md sin inventarlo.

La matriz de 60 funciones, benchmark y backlog describen las dependencias y aceptación. No fusionar ni desplegar esta versión sin aprobación expresa y sin cerrar los bloqueos aplicables.
