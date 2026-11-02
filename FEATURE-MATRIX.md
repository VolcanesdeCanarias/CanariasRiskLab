# Matriz de trazabilidad · 60 capacidades

Inspección: CanariasRiskLab main `647bec9544e2bc2fbee36731e850cca60b685c2a`; P0 `ac9ff9c207625426e34ac047997d391c149a10a0`; Earth `evolution/v2.1` `6521581003cdf23ad98d84cfcc476872b3a5a297`. Nueva rama parte de P0. «Legado disponible» significa funcionalidad existente accesible en `/` o API antigua, no que haya sido migrada a NEXT. «Previsto» no equivale a implementado. Referencias archivadas no garantizan calidad/licencia. No se han eliminado capacidades originales.

| ID / función | Estado original | Earth V2.1 | Integración / estado real | Prioridad | Archivo o evidencia |
|---|---|---|---|---|---|
| 01 · Exploración 2D | Sí, Leaflet | Sí, Tenerife | Mapa Canarias en NEXT; legado conservado | P1 | index.html / next/app.mjs |
| 02 · Relieve 3D | No | Sí, terreno local | Elipsoide en NEXT; MDT pendiente de licencia/datum | P1 | Earth app.mjs / next/earth.mjs |
| 03 · Cambio 2D/3D | No | Sí | Componente Cesium con límite vertical visible | P1 | next/app.mjs |
| 04 · Navegación archipiélago | Sí, siete islas y mar | No, caja Tenerife | Ocho islas y mar; encuadre global | P1 | risklab_next/api.py |
| 05 · La Graciosa | Sin identidad propia | No | Identidad propia por componente Teguise; validación pendiente | P1 | Geography |
| 06 · Registro municipal | 83 nombres, 88 geometrías | 31 auxiliares | Registro completo 88 sin alterar originales | P1 | api.py Geography |
| 07 · Filtro municipal | Sí, inferido por texto | No | Disponible legado; nueva asignación por polígono, filtro pendiente | P1 | server.py / api.py |
| 08 · Catálogo IGN reciente | Sí, HTML diez días | No | Adaptador P0 + instantánea | P0 | parse_ign_canarias |
| 09 · Feed USGS diario | Sí | No | Fuente independiente, magnitud nula preservada en nuevo contrato | P0 | fetch_usgs_canarias |
| 10 · Histórico KMZ | Archivo; no usado por API | Derivado candidato | Conservar; validar procedencia antes de ingestión | P1 | catalogo.kmz / Earth data |
| 11 · Magnitud y tipo | Sí, nulo USGS a cero | Sí, tipo parcial | Nuevo contrato conserva desconocido; legado compatible | P1 | server.py / api.py |
| 12 · Profundidad | Sí | Sí | Referencia catálogo explícita; incertidumbre no inventada | P1 | api.py / app.mjs |
| 13 · Hipocentros | No | Sí | Mismos registros, z aproximada; no medición geodésica | P1 | next/earth.mjs |
| 14 · Fichas de evento | Popups | Sí | Panel contextual seguro con textContent | P1 | next/app.mjs |
| 15 · Incertidumbres | No publicadas | Aviso de ausencia | Nulas explícitas, no error cero | P0 | api.py normalize |
| 16 · Filtro territorial | Cajas e inferencia | Caja Tenerife | Polígono terrestre; mar separado | P1 | Geography.locate |
| 17 · Filtro magnitud | Sí | Sí | Compartido API; sin cambiar resultados por perfil | P1 | analyze |
| 18 · Filtro profundidad | Distribución, no consulta avanzada | Sí, bandas | Legado/Earth disponibles; migración de filtro pendiente | P1 | Earth core.mjs |
| 19 · Periodos | 24h/7/10/30d sobre IGN10d | Calendario UTC | Intervalos UTC excluyentes; cobertura parcial explícita | P1 | analyze |
| 20 · Reproducción temporal | No | Sí | Cursor y pausa sobre selección completa | P1 | next/app.mjs |
| 21 · Avance/retroceso | No | Cursor y días | Cursor temporal; atajos de días aún no migrados | P2 | next/app.mjs |
| 22 · Comparación periodos | Ventanas acumuladas no equivalentes | Duraciones UTC iguales | Ventanas equivalentes y comprobación cobertura nominal | P1 | analyze comparison |
| 23 · Serie temporal | Sí; pierde año/29feb | Sí, bins UTC | Gráfico UTC con año en NEXT; legado no corregido todavía | P1 | server.py serie_temporal / next chart |
| 24 · Mmax | Sí, negativos sesgados en serie | Sí | Nuevo cálculo descriptivo conserva negativos/nulos | P1 | analyze stats |
| 25 · Histograma profundidad | Sí | Sí | Legado disponible; migración pendiente | P1 | depth_profile / Earth core |
| 26 · Exportación CSV | No | Sí, protección de fórmulas | Exportación por snapshot+parámetros y escape | P1 | api.py CSV |
| 27 · Manifiesto/exportación JSON | No | Sí | Resultado+parámetros+método+evidencia | P1 | next/app.mjs |
| 28 · Ciudadanía | Sí, modo | Sí | Mismos datos y resultados en NEXT | P1 | next/app.mjs |
| 29 · Investigación | Análisis | Research | Panel ajustable, gráficos/consulta/exportación | P1 | next Research |
| 30 · Gestión institucional | Territorio UI; no permisos | No | Espacio no habilitado; API 403 real | P0 | api.py institutional |
| 31 · Panel Research ajustable | No | Sí | Ratón/táctil/teclado, minimizar/cerrar | P1 | next resize |
| 32 · Cámara estable al redimensionar | Mapa único | Sí, probado | Prueba 2D/3D específica | P1 | tests/next/browser.cjs |
| 33 · Responsive | Parcial | Sí | App luminosa, viewport móvil probado | P1 | next/style.css |
| 34 · Accesibilidad | Parcial | Teclado dock y controles | Foco/skip/labels/selector; auditoría completa pendiente | P1 | next/index.html |
| 35 · Catálogo edificios volcánicos | 12 manuales | Lugares relevantes | 11 referencias opcionales; Tagoro retenido en legado por conflicto | P1 | references.json |
| 36 · Zonas volcánicas | 3 manuales | No | Conservar legado; migrar tras fuente/verificación | P1 | index.html VOLCANIC_ZONES |
| 37 · PEVOLCA | 7 manuales; P0 indica no vigente | No | No mostrar como actual; enlace oficial y abstención | P0 | OFFICIAL_STATUS_METADATA / catalog |
| 38 · Exclusión La Palma | 13 polígonos históricos | No | Legado con aviso; no guía de seguridad actual | P0 | la_palma_exclusion15ene26.geojson |
| 39 · Inventario instrumental | 4 referencias manuales | No | Legado disponible; series operativas no acreditadas | P1 | ign_instrumentation.json |
| 40 · GNSS series | Previsto, no implementado | No | Contratos/operadores/datum y huecos antes de conectar | P2 | ROADMAP F2-03 |
| 41 · InSAR | Previsto, no implementado | No | EGMS candidato, LOS/órbita/coherencia y cobertura por verificar | P2 | BENCHMARK |
| 42 · Geoquímica/geotermia | Previsto, no implementado | No | Solo al disponer de datos licenciados y calidad | P2 | PRODUCT-VISION |
| 43 · 32 equipamientos | Sí, manuales duplicados | No | Recuperados con procedencia, sin clasificar crítico | P1 | references.json |
| 44 · Proximidad/exposición | Distancias/score experimental | No | Conservar legado; no afirmar riesgo o exposición validada | P1 | exposed_infrastructures |
| 45 · Ranking municipal | Sí, experimental | No | Disponible legado; revisar ámbito/coordenadas antes de migrar | P1 | municipality_ranking |
| 46 · Clusters municipales | Sí, simbología aproximada | No | Legado disponible; no usar centro volcánico como centro sísmico | P1 | detect_municipal_clusters |
| 47 · Clusters espaciales | Conectividad 12km/72h experimental | No | Legado disponible; sensibilidad/profundidad/rendimiento pendientes | P1 | build_spatial_clusters |
| 48 · Clusters temporales | Agregados anidados insulares | No | No confundir con detección espaciotemporal validada | P1 | build_temporal_clusters |
| 49 · Focos/ranking | Sí, reglas experimentales | No | Conservar API/legado sin validar foco físico | P1 | build_focus_ranking |
| 50 · Enjambres | Heurística 48h, sin UI completa | No | Preservado backend; validación/migración pendientes | P1 | detect_swarms |
| 51 · Índice RiskLab | Experimental; vacío=9 en main | No | P0 bloquea vacío/fallo; no publicado en nueva UI como alerta | P0 | compute_risklab_index |
| 52 · Baseline/aceleración | Experimental, ventanas sesgadas | No | Conservar sin alterar ciencia; validar antes de promoción | P1 | compute_baseline / compute_acceleration |
| 53 · Migración/régimen/anomalía | Heurísticas no validadas | No | Legado disponible; no causalidad/predicción | P1 | detect_depth_migration / detect_regime_change / compute_anomaly_signal |
| 54 · Interpretación automática | Texto por reglas | No | Plantilla descriptiva nueva con snapshot; no IA científica | P1 | auto_interpretation / analyze explanation |
| 55 · Capas/basemaps/calor | 12 toggles, 3 bases, heatmap | 2D/3D y terreno | Legado íntegro; NEXT migra eventos+referencias, resto pendiente | P1 | index.html / next/app.mjs |
| 56 · Trazabilidad/adquisición | Estado P0; sin persistencia | Inventario/manifest histórico | SQLite snapshot inmutable y método; originales crudos pendientes | P0 | SnapshotStore |
| 57 · Seguridad HTTP/errores | P0 en rama no main | Allowlist local, no endurecido público | P0 incluido; nuevas rutas explícitas y errores sin cero | P0 | server.py PUBLIC_FILES / api.py |
| 58 · IA documental/natural | Prevista, no implementada | No | Arquitectura herramientas/RAG; plantilla temprana real | P2 | ARCHITECTURE |
| 59 · Escenarios/revisión institucional | Previstos, no implementados | No | Bloqueados hasta datos, modelos, permisos y revisión humana | P2 | ROADMAP F5 |
| 60 · Pruebas/calidad | 28 Python +9 JS + navegador P0 | Core/integridad/browser V2.1 | Pruebas heredadas más contrato/UI NEXT; no certificación científica | P0 | tests/ / docs/next/REVIEW.md |


## Revisión funcional 01 · 2026-11-02

Revisión01 actualiza estas filas manteniendo las 60 originales:

| Filas | Recuperación demostrable | Pendiente |
|---|---|---|
| 01–07,16 | Encuadre estable, ocho islas/mar, La Graciosa separada de islotes, municipios/bounds/filtro | Certificar límites y consultas área/coordenadas |
| 02–03,13 | Transferencia 2D/3D coherente, base oficial sobre elipsoide e importador/malla MDT con LOD | No hay MDT real validado ni batimetría |
| 18,25 | Filtro/histograma de profundidad recuperados | Series multiseñal y análisis avanzados |
| 22–23,26–29 | Comparación/CSV con mismos filtros; no_coverage con abstención | Históricos completos/licenciados y comparación multiterritorio dedicada |
| 31–34 | Research ajustable/minimizar/restaurar y mapa mínimo; cuatro viewports | Accesibilidad integral, Safari/Mac |
| 35–36 | Tres fichas documentales de fuente primaria y navegación sin límites geológicos inventados | Catálogo completo/revisión experta/Tagoro |
| 39,43,55 | Cuatro estaciones manuales sin estado operativo; inventarios organizados; bases oficiales | Telemetría y capas analíticas restantes |
| 56–57,60 | Falta de cobertura distinta de cero y cartografía fallida independiente; regresión ampliada | Persistencia cruda, cuotas, seguridad del legado, preparación pública |

Legado disponible no equivale a migración completa. Originales y fórmulas preservados.


## Revisión de producto 01 · 2026-11-02

Actualización de producto01, conservando F01–F60 y funciones heredadas:

| Funciones | Implementado en piloto | Pendiente |
|---|---|---|
| F08–F12,F19–F27 | ArchivoUSGS181 oficial, originales/hash/reconciliación, serie anual/consulta, filtros y comparación reproducible, CSV/HTML/ZIP | HistóricoIGN completo, completitud instrumental/multiseñal |
| F35–F36 | Geología/clasificación/estructuras e historia1798/1909 con fuentes primarias y relaciones tipadas | Cartografía geológica/vectorial acreditada, revisión experta, catálogo completo |
| F43–F44 | Asignación territorial derivada versionada, parque/hospital documentados, sin convertir referencias manuales en oficiales | Geolocalización acreditada, proximidad/exposición con escenarios/modelos |
| F47–F54,F58 | Método exploratorio de catálogo, vecino/celdas/sensibilidad y explicación con evidencias; consultas acotadas | Clusters/focos/unrest causal y métodos científicos avanzados validados; no predicción |
| F56–F57,F60 | Originales históricos inmutables/runhash/CLI, corrupción/estado/refusal/export seguro,114 pruebas ampliadas | Pipeline global con cuotas/retención, endurecimiento operativo |

Piloto soloTenerife/mar; otras islas no tienen caso histórico implementado. 3D/legado y navegación multinsular conservados; ninguna capacidad prevista se declara completada por existir documentación.
