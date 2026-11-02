# Punto de reanudación · Revisión funcional01 · 2026-11-02

Rama integration/next-phase1, PR #2 en borrador, CanariasRiskLab canónico. Base de iteración 7cb067c6bc4d1886bbeabf2a80bb9bdb7e99f001. No modificar main, PR #1/P0, Earth V2.1 o Render. Leer docs/next/REVIEW-01.md y comprobar HEAD/CI en GitHub antes de reanudar.

Implementado: MAP-01/02/05 con cámara y panel de mínimo útil, estado geográfico separado de consulta, sin perder evento/filtros en perfiles/2D/3D. IGN/PNOA/híbrida; ocho islas/mar, 88 municipios, tres sistemas documentales GVP. Filtro/histograma profundidad y estaciones manuales sin operación verificada. no_coverage con count nulo. Normalización1.1 corrige La Graciosa frente a islotes, sin reescribir instantáneas.

MDT: importador GeoTIFF y malla LOD técnicamente probados, sin MDT real adquirido/validado. WCS histórico404; servicios.idee.es actual fuera de política de descargas. Sin batimetría/geoide/conversión vertical. Imagen WMS no es terreno3D. Fichas documentales no son validación experta. Logo oficial ausente.

Resultados locales: 49 Python, 9 JS heredados, 3 unidad de layout, 10 navegador legado y 19 navegador NEXT = 90 aprobadas; un smoke opcional omitido. Pruebas/logs/capturas: docs/next/review01 y REVIEW-01.md. Comprobar ejecución final/CI, no extrapolar a Mac/Safari o FPS de miles. Revisión live con eventos y WMS auténticos por proxy autorizado, sin sustituir respuestas. Fixtures únicamente tests.

Próximo trabajo material MAP-04: obtener MDT oficial documentado (conectividad habilitada o archivo auténtico), comprobar licencia/checksum/datum/resolución, importar isla piloto y revisar LOD/nodata/vertical/cámara en Mac. No simular solución. Otras tareas viables: archivo crudo/retención y cuotas F1-08, OpenAPI, revisión XSS/endurecimiento antes de exposición. Pendientes históricos/capas/series multiseñal/comparación multiterritorio y autenticación institucional; mantener403.

Mac: README, python3 abrir.py, solo127.0.0.1; npm ci para SDKs. rasterio opcional solo para importar MDT auténtico. PR https://github.com/VolcanesdeCanarias/CanariasRiskLab/pull/2 . No fusionar/desplegar sin aprobación expresa.
