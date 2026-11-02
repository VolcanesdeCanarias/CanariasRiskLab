# Revisión de producto 01 · 0.3.0 · Cuaderno geocientífico Tenerife

Primera capacidad vertical de investigación en la aplicación existente: territorio → sistema → documentos científicos → histórico oficial → análisis reproducible → explicación con evidencias → territorio → informe. Rama `integration/next-phase1`, PR #2 en borrador; no otro prototipo, despliegue o modificación de producción.

## Cómo demostrar el recorrido

1. Ejecutar `python3 abrir.py` siguiendo README. Seleccionar **Tenerife** y **Tenerife · Teide–Pico Viejo**. Pulsar **Investigar un sistema · caso Tenerife**. También abre el piloto directamente y deja su territorio explícito.
2. Consultar geología, estructuras e historia: contexto IGN/IGME, Chahorra–Pico Viejo1798 y Chinyero1909 diferenciados. Cada afirmación lleva fuentes. La caja de estudio no es frontera del sistema ni área de peligro.
3. Consultar histórico USGS: 181 registros reales archivados, reconciliados entre GeoJSON, CSV y endpoint count. La serie anual distingue registros seleccionados, registros existentes en el área y años sin registros retornados. Explorar catálogo completo o selección analizada en el mapa.
4. Ejecutar el caso inicial: desde2004-01-01 hasta2005-01-01 excluido, mbLg≥2, celda0,05°. Periodo previo calculado automáticamente con igual duración: 2002-12-31→2004-01-01 excluido. Cambiar parámetros invalida resultados y exportaciones hasta volver a ejecutar.
5. Examinar tasas del catálogo, mediana de vecino más próximo, ocupación de celdas, sensibilidad al umbral y disponibilidad de incertidumbres. Preguntar a la asistencia por tasas/cobertura/geología/territorio: responde con campos de evidencia de esa ejecución, se abstiene ante predicción/alertas/causas.
6. Consultar asignación geométrica tierra/mar/municipio y contexto territorial documentado. Parque y referencia hospitalaria tienen procedencia explícita, sin inventar geometrías, distancias o exposición.
7. Descargar informeHTML imprimible a PDF, CSV de ambos periodos y ZIP de evidencias. ZIP incluye originales, ejecuciónJSON, método/especificación y checksums. Repetir con `python3 tools/reproduce_research.py run.json` desde el código compatible; debe coincidir run_id.

## Resultado real del caso inicial

| Campo | Resultado |
|---|---|
| Registros del periodo actual | 11 |
| Registros del periodo previo | 35 |
| Duración de cada periodo | 366 días, intervalos UTC excluyentes |
| Tasa actual del catálogo | 10,977459 registros/año de365,25d |
| Tasa previa del catálogo | 34,928279 registros/año |
| Razón de tasas | 0,3142857143 |
| Vecino más próximo epicentral, mediana | 3,387151511km |
| Celdas0,05° ocupadas | 8 |
| Registros actuales tierra/mar según polígonos heredados | 4 Icod de los Vinos / 7 entorno marítimo |
| Errores publicados horizontal/profundidad/magnitud en selección actual | 0/0/0 **registros con error informado**; valores desconocidos, no errores de0 |
| Inferencia de cambio geofísico/predicción/alerta | No permitida; p-valor nulo, no inventado |

Estos valores describen una selección de **ComCat**, no una tasa completa de sismicidad ni una disminución demostrada de actividad. El umbral2 no es una estimación de Mc. Se selecciona una sola escala de magnitud; no se convierten escalas. No atribuir todos los terremotos a Teide–Pico Viejo por estar en la caja.

## Qué datos se verificaron y qué no

Se adquirió una respuesta auténtica del [servicio FDSN USGS](https://earthquake.usgs.gov/fdsnws/event/1/), ventana consultada2000-01-01→2026-01-01 excluido, caja[-17,4,27,5,-15,5,29]. Sus181 IDs coinciden en GeoJSON y CSV y con count181. Se verifican coordenadas, fechas UTC, profundidad, magnitud/tipo, rangos, filas duplicadas, nulos e integridad de bytes. Todos los registros incluidos tienen red `us`; política de datos y atribución USGS archivadas en el manifiesto. Hay4 magnitudes nulas preservadas y solo1 registro de todo el archivo publica errores horizontal/profundidad/magnitud en el CSV.

**Procedencia e integridad verificadas no equivalen a completitud instrumental o validación causal.** Los registros se concentran en2000–2008 y solo hay otro registro en2019 en la caja de consulta. La consulta cubre un intervalo, pero no acredita detección homogénea en todo él. IGN documenta sismicidad regional que no se reconstruye con este subconjunto global. Años sin registros no son prueba de inactividad; un filtro que excluye datos tampoco es un año vacío de la fuente.

El KMZ candidato y los13.573 registros privados Earth no se incorporaron ni se promovieron a catálogo oficial validado. No hay histórico IGN adquirido para este flujo: el catálogo web oficial existe, pero la URL FDSN probada aquí respondió404 y no se ha acreditado como interfaz oficial de adquisición. No se declara por ello que IGN esté caído. GNSS/InSAR/gases históricos siguen pendientes.

Las fichas científicas son una síntesis documental de fuentes primarias, con revisión experta pendiente. La geometría municipal es la heredada, con hash y vigencia no certificada. El hospital CNH380178 está referenciado desde el registro oficial de Sanidad; no se copian coordenadas manuales ni se afirma capacidad, criticidad u operación actuales. Sin una geometría acreditada no se calcula proximidad, y sin escenario no se calcula exposición/riesgo.

## Análisis y asistencia implementados

Método `catalogue-rates-spatial/1.0`: tasas normalizadas por duración real; razón entre ventanas iguales; vecino más próximo mediante haversine esférico R6371,0088km; celdas con origen/resolución explícitos; sensibilidad a incrementos de0,5 y1 de magnitud. Distancia epicentral, no hipocentral; celdas no son clusters físicos ni focos activos. Presupuesto: periodo≤3660d y selección espacial≤2000 registros. No p-valores/confianzas ficticias ante detección no acreditada.

La ejecución es inmutable en SQLite y su identificador SHA256 vincula parámetros, dataset, contexto, método/código, geometría/código de asignación y resultados. Se guarda la respuesta normalizada con IDs y fuentes; originales históricos inmutables se incluyen con checksums. El historial reciente IGN/USGS permanece separado, incluso ante fallos o recuperación.

La primera asistencia es **un router determinista de consultas acotadas con herramientas/resultados trazables, sin LLM**. Puede explicar tasas, patrón espacial descriptivo, cobertura, contexto geológico y territorial. Rechaza predicciones/alertas/causas/evacuaciones y reconoce preguntas no soportadas. Preguntar por otro territorio, cifras de parámetros distintos o tasas de otro año no modifica la ejecución ni inventa una respuesta: exige ajustar el formulario. No se presenta como IA científica avanzada validada.

## Pruebas y evidencias

- Backend: **66 pruebas** (incluye49 previas y17 nuevas de datos históricos, SQL independiente, distancias con referencia independiente, UTC/leapyear, nulos, integridad, persistencia, seguridad de informe, asistencia y reproducción CLI).
- JavaScript legado: **9**. Unidad de layout: **3**.
- Navegador legado: **10 aprobadas**, un smoke live opcional omitido.
- Navegador NEXT: **26 aprobadas**, incluyendo19 previas y7 nuevas del recorrido completo, parámetros/caducidad, asistencia, descarga real, fallo/recuperación, independencia de IGN, móvil/perfiles y respuestas tardías que no reabren un estudio cerrado.
- Total: **114 comprobaciones automatizadas únicas**, sin contar el smoke omitido ni repeticiones.

Logs finales y pruebas de ejecución/CLI en `product01/`. Capturas auténticas de la aplicación con el histórico oficial archivado, sin observaciones simuladas: [contexto](product01/captures/01-context-desktop.jpg), [serie](product01/captures/02-historical-series.jpg), [análisis](product01/captures/03-reproducible-analysis.jpg), [asistencia](product01/captures/04-grounded-assistance.jpg), [territorio](product01/captures/05-territorial-context.jpg), [informe](product01/captures/06-exported-report.jpg), [móvil](product01/captures/08-mobile-analysis.jpg). Cartografía PNOA auténtica mediante proxy autorizado de revisión, sin sustituir imágenes ni desactivar TLS. Los servicios externos pueden fallar parcialmente; no cambia el análisis archivado.

[Ejemplo descargable de evidencias](product01/example-evidence.zip) incluye el informeHTML y todos los datos/parámetros para inspección local. El informe no es una comunicación oficial. Revisión ejecutada en Chromium/Linux/SwiftShader; macOS/Safari/GPU y accesibilidad integral todavía requieren comprobación. La CI del commit final se verificará en el PR.

## Alcance y siguientes hitos

Caso disponible solo para **Tenerife/Teide–Pico Viejo y caja marina de estudio**. Arquitectura/navegación conserva ocho islas incluida La Graciosa y mar; los demás casos históricos responden `not_implemented`, no cobertura simulada. Institucional continúa restringido con403. Sin merge o despliegue.

Prioridad siguiente: histórico IGN con procedencia/licencia y evaluación de completitud; ingestión cruda/versionada y cuotas para fuentes recientes; corpus científico revisado; primera serie multiseñal auténtica; infraestructuras georreferenciadas con fuentes acreditadas y consultas de proximidad diferenciadas de exposición. MDT/batimetría siguen planificados por fuente/resolución/datum/licencia, sin elevar una imagen inclinada a modelo científico. Mantener revisión científica e institucional antes de usos operativos; no hay predicción eruptiva ni alertas.


Ejecución de ejemplo archivada: `b4de445ffe75643744d4d4e8083ece3f11fcc4e6c0891d29e51dd4ad8521804b`. Dataset: `609f4f89a7b470e2975163a4b289cae92f7e26e1209646c4f00b03a657be3879`. Reproducción CLI confirmada (`product01/REPRODUCE.txt`), sin red ni generador de datos.

Rendimiento local preliminar:20 solicitudes Flask en proceso con181 filas reales, verificación/normalización/análisis/SQLite; mediana16.84ms y máximo68.80ms. No incluye red cartográfica, FPS, TCP ni Mac/GPU; no es una garantía de servicio.
