# Continuidad · Producto01 · 2026-11-02

CanariasRiskLab canónico, rama integration/next-phase1, PR #2 en borrador. Base de iteración39422d1d0b51e5ba83a66be25363b6a4e527040c. No tocar main, PR1/P0, EarthV2.1 ni Render. Leer PRODUCT-REVIEW-01.md, RESEARCH-METHOD.md y verificar HEAD/CI del PR al reanudar.

Salto funcional implementado: cuaderno en /next con selecciónTenerife/Teide–Pico Viejo, corpus geología/historia/documentos, históricoUSGS181 reconciliadoGeoJSON/CSV/count, método catalogue-rates-spatial/1.0, tasas/ventanas/celdas/vecino/sensibilidad, incertidumbre y asistencia determinista por evidencia, contexto municipal/parque/hospital y exportaciónHTML/CSV/ZIP+CLI. Originales bajo risklab_next/data/research; no sobrescribir esta versión. Corpus separa documental/observación/cálculo e interpretación y no inventa causalidad o geometrías.

Caso inicial:2004-01-01→2005-01-01 excluido, mbLg≥2, celda0,05°:11 registros actuales vs35 previos, ambos366d; razón0,3142857; medianaNN3,387151511km;8 celdas. Son registrosComCat, no actividad completa. Completitud/detección no acreditadas; cero no es quietud; sin p-valor o predicción. Polígonos heredados con hash y calidad no certificada; hospital sin geolocalización validada, no proximidad/exposición simulada.

Pruebas finales aprobadas/archivadas en docs/next/product01:66Python,9JS legado,3unidad layout,10browser legado y26browserNEXT=114 únicas; un smoke opcional omitido. Comprobar logs/CI final antes de afirmar estado. Capturas con app real, archivoUSGS real y PNOA real vía proxy autorizado, no fixtures. Informe ejemplo ZIP/HTML y CLI permiten repetición del run_id sin red. Validación de software/procedencia no equivale a revisión científica experta o Safari/Mac/GPU.

Próximo hito: adquirir históricoIGN por interfaz documentada y evaluar completitud/umbrales/estabilidad; no promover KMZ candidato sin evidencia. Después fuente multiseñal auténtica y corpus revisado, geolocalización acreditada de activos y consultas de proximidad separadas de exposición. Pipeline crudo/versionado existe para este piloto, no para toda ingesta reciente; cuotas/retención/backups/endurecimiento/XSS legado pendientes. MDT/batimetría reales y datum siguen pendientes, no imagen3D como sustituto.

Solo caso históricoTenerife/mar, otras islas not_implemented; navegación archipiélago/LaGraciosa/mar y capacidades previas conservadas. Institucional403 sin permisos reales, sin alertas. Logo auténtico pendiente. No merge/despliegue/pago. Probar localmente con README y python3 abrir.py; paquetes npm y Python existentes, sin dependencia científica de pago/LLM. PR https://github.com/VolcanesdeCanarias/CanariasRiskLab/pull/2 .

Ejecución de ejemplo: b4de445ffe75643744d4d4e8083ece3f11fcc4e6c0891d29e51dd4ad8521804b · paquete docs/next/product01/example-evidence.zip · repetir con tools/reproduce_research.py. El informe y manifiesto explican alcance/limitaciones, no cobertura completa o validación causal.


## Salto funcional multinsular · 0.4 · 2026-11-02

Continuar exclusivamente `integration/next-phase1`, PR#2 en borrador. Incremento0.4 implementado: ver docs/next/OBSERVATORY-01.md. Archivo IGN3609 registros,2023–2024; BDDAE88 municipios; módulo multinsular y asistencia determinista. No publicar como vigilancia. `research_v1.py` intacto mantiene evidencia0.3. Ejecutar Python/JS/browser; revisión real `tools/review_observatory.cjs`. Original WFS restaurable localmente o desde su URL oficial por tools/data/restore_administration_original.py; HTML íntegro no distribuido por campos de sesión. MDT bloqueado por política de salida, no confundir elipsoide con relieve. Siguientes datos: ampliar años IGN,completitud,instrumentación y fuentes territoriales oficiales. Revisión/actualización remota del PR por confirmar en evidencia final; jamás merge/desplegar.

Fuente pública0.4 final: dataset97bf28961d60b2cc8193563d56a227fc364f1d5f2d6bd8ea37171e89ca85945d; ejemplo58c632b1e01c2a0b71addbdc721a07b8f15cf1c8281a49201495143c73232a7d. Original HTML con sesión retenido localmente, no en GitHub. Publicación por tablas extraídas y88 GeoJSON legibles; no reintentar HTML rechazado por revisión automática.


## Actualización continua · 0.5 · 2026-11-03

Trabajar solo en `integration/next-phase1`, PR #2 en borrador. Leer [CONTINUOUS-01](docs/next/CONTINUOUS-01.md) y [resultados](docs/next/continuous01/RESULTS.md). `python3 abrir.py` inicia el recolector y abre `?mode=continuous`; importar Flask no adquiere. Base privada configurable: `.risklab-next/continuous.sqlite`. Evidencia real: IGN 21 → 22 → 23; USGS cero validado con count. Capturas y exportación normalizada en `docs/next/continuous01`; jamás publicar HTML de sesión ni bases. Próximos pasos: backfill validado, completitud, operación duradera y nuevas señales acreditadas. Verificar HEAD y CI del PR. No fusionar ni desplegar.
