# Hoja de ruta y backlog verificable

Estado 2026-11-02: Fase 0 documentada con benchmark preliminar; primera integración de Fase 1 implementada para revisión. Ninguna fase integral se declara terminada. Prioridad P0 bloquea exposición pública; P1 funcional; P2 expansión.

| ID | Prioridad / fase | Unidad y dependencia | Criterio y prueba de aceptación | Estado |
|---|---|---|---|---|
| F0-01 | P1 / 0 | Inventario de ambos commits y matriz 60 | Cada capacidad con archivo, estado y destino | Documentado |
| F0-02 | P1 / 0 | Benchmark primario revisable | URL, capacidad real, límites, interoperabilidad y decisión | Preliminar, revisión experta pendiente |
| F1-01 | P0 / 1 | Arrancar desde P0 sin modificar PR1 | 28 backend + 9 JS + navegador legado | Implementado; resultados en informe |
| F1-02 | P0 / 1 | Contrato de calidad e instantáneas | vacío/fallo/parcial/filtro vacío separados; hash y reproducción | Implementado local |
| F1-03 | P1 / 1 | Registro multinsular y mapa 2D | 8 islas, 88 municipios, mar no inferido por proximidad | Implementado; cartografía pendiente de certificación |
| F1-04 | P1 / 1 | Aplicación luminosa + Research | perfiles numéricamente iguales; redimensionar sin salto | Implementado; navegador en informe |
| F1-05 | P1 / 1 | Earth como componente 3D | mismos eventos y ficha; datum visible | Elipsoide implementado; MDT pendiente |
| F1-06 | P1 / 1 | Fichas volcánicas verificadas | referencia primaria por ficha y revisión de Tagoro | Bloqueado por verificación científica; referencias marcadas |
| F1-07 | P1 / 1 | Identidad oficial | archivo autorizado real, licencia y contraste | Pendiente de archivo; sin recreación |
| F1-08 | P0 / 1 | Persistencia de originales/ingesta | checksum bytes, scheduler, reintento 403/429, health, cuotas | Pendiente; depende política de fuentes |
| F1-09 | P0 / 1 | Preparación pública | revisión XSS legado, deps, CSP, tasa/límites, retención y restauración | Pendiente: no exponer públicamente |
| F2-01 | P1 / 2 | Migrar todas las capas de legado | paridad 12 capas, conteos, leyendas, popup seguro | Legado disponible; migración parcial |
| F2-02 | P1 / 2 | Territorio/municipio/área/coordenadas | point-in-polygon contrastado, mar, bordes, índices | Municipio API disponible como registro; filtros avanzados pendientes |
| F2-03 | P1 / 2 | Series GNSS/InSAR y redes | operador, datum/unidades, disponibilidad y licencia, huecos | Pendiente de fuentes verificadas |
| F2-04 | P1 / 2 | Inventario territorial trazable | IDs/fechas/fuentes/atributos autorizados, sin clasificar crítico | Referencias recuperadas; verificación pendiente |
| F3-01 | P1 / 3 | Motor de métodos | baseline independiente, completitud, retrospectivo, revisión | Descriptivo implementado; métodos avanzados pendientes |
| F3-02 | P1 / 3 | Clusters espaciotemporales | contrastar referencias, sensibilidad y sesgos, rendimiento | Legado experimental preservado; no validado |
| F4-01 | P1 / 4 temprana | Explicación fundamentada | cada cifra vinculada a snapshot/consulta, abstención en fallo | Plantillas implementadas |
| F4-02 | P2 / 4 | Consulta natural + RAG | corpus autorizado, evaluaciones y citas, sin ejecución libre | No implementado; proveedor no contratado |
| F5-01 | P0 / 5 | Acceso institucional | OIDC, permisos servidor, 401/403 y auditoría | API cerrada; autenticación pendiente |
| F5-02 | P2 / 5 | Escenarios y revisión humana | hipótesis explícitas, modelos validados, firma de revisión | No implementado |
| F6-01 | P1 / 6 | Calidad operativa | accesibilidad auditada, cargas reales, seguridad, restore | Comprobaciones iniciales; no certificación |

Presupuestos propuestos: consultas descriptivas 13k < 1 s en equipo de referencia, interacción de filtros p95 < 500 ms tras caché, primer mapa utilizable < 3 s sin coste de red externa; 3D ≥ 30 FPS en GPU Mac de referencia. Son objetivos, no resultados medidos ni garantías. Medir con datos reales y hardware documentado antes de ampliar. Consultas/CSV completos, nivel de detalle solo visual sin cambiar números.

Siguiente secuencia autorizada: consolidar pruebas de esta entrega → ingesta cruda/retención/contrato OpenAPI → navegación municipio/área y recuperación progresiva de capas con trazabilidad → licencia MDT y fichas volcánicas. La publicación pública sigue bloqueada hasta revisión P0, datos/activos y autorización del promotor.


## Revisión funcional 01 · 2026-11-02

Revisión01: MAP-01/02/05 implementados y comprobados en cuatro viewports; MAP-03 primera integración IGN/PNOA/híbrida y evaluación oficial documentada; MAP-06 leyenda plegable/capas por naturaleza. F2-02 navegación municipal/bounds/filtro y sistemas documentales; áreas/coordenadas aún pendientes. F1-06 tres fichas documentales, no catálogo completo ni validación experta. F2-01 histograma/filtro profundidad y estaciones manuales recuperados.

MAP-04 parcial: importador/malla LOD probados, sin MDT real. Siguiente tarea: habilitar dominio oficial mediante configuración autorizada o recibir archivo auténtico; verificar licencia/datum/resolución/cobertura, importar isla piloto y probar geodesia/LOD/Mac. Cierre exige archivo real con checksum y revisión vertical; no imagen WMS. Mantener pendientes archivo crudo/retención y endurecimiento público.


## Revisión de producto 01 · 2026-11-02

Producto01 reordena prioridades: recorrido vertical implementado en pilotoTenerife, no completar la plataforma por añadir otro visor. Nuevos entregables: históricoUSGS181 reconciliado, corpus primario, método espacial/tasas/sensibilidad, asistencia acotada, contexto territorial y exportación evidencias/CLI.

Siguiente prioridad P1: históricoIGN adquirido mediante interfaz documentada con licencia/calidad, reconciliación y análisis de completitud; después primera señalGNSS/InSAR auténtica con unidades/datum/huecos, corpus revisado científicamente, activos georreferenciados acreditados y proximidad distinguida de exposición. Cada fuente debe entregar originales versionados y pruebas. El archivo crudo/versionado existe para este piloto; ingesta/retención/cuotas de fuentes recientes siguen pendientes.

MDT/batimetría no bloquean el valor científico inicial pero siguen pendientes de fuentes/resolución/licencia/datum y validación; no imagen inclinada como sustituto. Institucional/auth/escenarios permanecen cerrados. Antes de exposición pública: XSS/seguridad de legado, límites, cuotas, backups y revisión humana.


## Salto funcional multinsular · 0.4 · 2026-11-02

Entregado: consulta IGN2023–2024 multinsular, comparación territorial/temporal, exploración gráfica, celdas/bloques descriptivos, asistencia vinculada a ejecución y capa municipal oficial consultable. Siguiente: ampliar el archivo a años adicionales mediante nuevas versiones, estudiar completitud/cambios de red y revisar atribución geográfica. MDT: falta autorización de salida a servicios.idee.es/centrodedescargas.cnig.es o un GeoTIFF oficial aportado; no bloquea las funciones anteriores. Después: instalaciones oficiales, GNSS/InSAR/gases, auth institucional y revisión experta.


## Actualización continua · 0.5 · 2026-11-03

Entregado el canal sísmico continuo y su demostración local. Siguiente validación: backfill oficial IGN para ampliar cobertura, caracterización de completitud, política de archivo/retención y supervisión operativa. Escalado multiinstancia requiere PostgreSQL u otro almacenamiento compartido. GNSS, InSAR y geoquímica necesitan contratos y validación propios; no se simulan. Render sigue pendiente de aprobación. [Detalles](docs/next/CONTINUOUS-01.md).
