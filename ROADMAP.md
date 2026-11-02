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
