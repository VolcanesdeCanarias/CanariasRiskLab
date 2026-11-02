# Registro de decisiones

- ADR-001 · 2026-11-02 · CanariasRiskLab canónico; Earth componente. Mantener Flask, no reconstruir núcleo ni eliminar legado.
- ADR-002 · Rama `integration/next-phase1` desde `ac9ff9c207625426e34ac047997d391c149a10a0` (P0), sin fusionar ni alterar PR #1. El PR de integración incluirá diferencias P0 respecto main; no implica aprobación de despliegue.
- ADR-003 · `/next/` como entrada optativa; `/` y seis endpoints heredados intactos. Recuperación parcial declarada, no paridad ficticia.
- ADR-004 · SQLite local transitorio; registro objetivo PostGIS/objetos originales/colas. Persistir normalizado inmutable ahora; no afirmar ingesta programada, archivo crudo, backup o permisos implementados.
- ADR-005 · Consultas y explicaciones por snapshot+parámetros, duraciones equivalentes UTC, sin mezclar IGN/USGS. Campo desconocido permanece nulo en nuevo contrato USGS; compatibilidad heredada conservada.
- ADR-006 · Plantillas deterministas tempranas, sin proveedor LLM/pago/agentes. RAG/herramientas y evaluación antes de interpretación avanzada.
- ADR-007 · Registro de ocho islas/mar y 88 municipios derivado del GeoJSON, sustituyendo lista incompleta solo en nueva API. Asignación por geometría, sin inventar municipio marino.
- ADR-008 · No redistribuir activos privados Earth con permiso cartográfico incierto. Globe elipsoidal con límites explícitos hasta autorizar MDT e imagen. Las referencias manuales llevan advertencia y Tagoro queda fuera de mapa nuevo por conflicto.
- ADR-009 · Gestión institucional no habilitada: 403 servidor; perfil de interfaz no autoriza. No datos sensibles ni escenarios improvisados.
- ADR-010 · Interfaz luminosa, sans serif de sistema equivalente a Inter sin dependencia de fuente remota; marca de producto textual. Logo de Volcanes de Canarias pendiente del archivo oficial.

Decisiones revisables al disponer de evidencia. Incertidumbres de licencia, fuente, datum y validación científica no se resuelven por suposición técnica.


## Revisión funcional 01 · 2026-11-02

ADR-011: fila cartográfica real, mínimo útil, presupuesto dinámico Research y estado de cámara independiente; resize solo visible y Leaflet reset para evitar deriva de píxel.

ADR-012: integrar primero WMS IGN con atribución comprobada. GRAFCAN requiere revisar condiciones/conectividad; gratuidad no implica redistribución irrestricta. WMS no es MDT.

ADR-013: importación local GeoTIFF documentado con malla LOD limitada; no empaquetar alturas ficticias/activos privados. MAP-04 parcial hasta datos reales y revisión vertical.

ADR-014: sistema documental navega cámara/ficha, sin inventar polígono geológico ni filtrar observaciones silenciosamente. Municipio/profundidad son filtros de servidor exportables.

ADR-015: sin cobertura total → count nulo/no_coverage, sin CSV/gráfico cero; fallos cartográficos independientes de adquisición.
