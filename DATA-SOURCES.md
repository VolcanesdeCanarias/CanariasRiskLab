# Fuentes e inventario · revisión 2026-11-02

| Fuente/activo | Procedencia y cobertura conocida | Calidad/licencia/uso en esta entrega |
|---|---|---|
| IGN diez días | URL oficial en `/api/v1/catalog`; HTML regional móvil, columnas fecha UTC/magnitud/tipo/profundidad | Adaptador P0 rechaza 403/429/5xx, HTML inesperado, filas inválidas, duplicados, stale y vacíos ambiguos. Sin completitud ni incertidumbres. Permisos de redistribución masiva por confirmar |
| USGS día | Feed oficial global, recorte 26–31 N y −19..−12 O | FeatureCollection/metadatos/generación vigentes validados. No representa todos los microsismos regionales. Nuevo contrato conserva magnitud desconocida nula y tipo si existe. No reconciliado con IGN |
| municipios_canarias.geojson | Original del repositorio, 88 municipios, CRS84 (lon,lat); códigos de isla siete más La Graciosa derivada de Teguise | 13 MB; origen/licencia/fecha no documentados suficientemente. No es evidencia de límites oficiales vigentes. Derivado de contornos muestreado solo visual, original intacto |
| catalogo.kmz | Candidato atribuido a IGN, 52.199 placemarks, 2004–marzo 2026 en inspección previa, KML ≈101 MB | No consumido por nuevo runtime ni validado automáticamente por existir en repo. Debe verificarse procedencia/duplicados/UTC/datum/licencia antes de ingestión |
| Earth V2.1 events.json | Derivado candidato de KMZ, 13.573 registros en caja Tenerife, 2004–marzo 2026 | Permanece en repo privado, no copiado; 1.095 profundidades cero y 119 tipos de magnitud ausentes; UTC asumida documentada por Earth |
| Earth terreno e imagen | Esri, malla 1025² ≈135 m e imagen 1344×1152, referencias verticales aproximadas | No copiados al repo público ni nueva interfaz; licencia/redistribución y transformación geodésica pendientes. No batimetría |
| OpenStreetMap | Teselas web estándar, atribución visible | Servicio externo sujeto a política de teselas: https://operations.osmfoundation.org/policies/tiles/ ; no descarga masiva ni garantía offline. Caída de base no modifica datos |
| 12 volcanes / 3 zonas | Constantes manuales index.html; clasificación/historia no acreditadas | 11 referencias visibles opcionalmente en NEXT. Tagoro retenido en legado, omitido del mapa nuevo por latitud discordante 27.629 vs 27.729. Las 3 zonas no migradas todavía |
| 32 equipamientos | Constantes manuales duplicadas front/backend | Recuperados en registro con procedencia/commit y advertencia; no clasificación crítica ni fuente autorizada actual |
| ign_instrumentation.json | Cuatro referencias manuales (3 sísmicas, 1 GNSS) | Disponible en legado; no demuestra estaciones operativas ni contiene series de sensores |
| PEVOLCA / exclusión | Siete transcripciones 2026-04-06; 13 polígonos archivo 2026-01-15 | Históricos no vigentes verificados. NEXT enlaza fuente oficial y se abstiene de mostrar nivel actual |
| Datos de test | Generados bajo tests/test_next.py y tests/next/serve.py | Solo pruebas automatizadas, capturas rotuladas; nunca cargados por abrir.py o server:app |
| Logo oficial | No existe archivo oficial en fuentes inspeccionadas | Pendiente de aportar original SVG/PNG/WebP autorizado; colocar en `next/brand/` tras revisión y añadir ruta explícita. No recreado |

Acquisición y observación son fechas distintas. El snapshot conserva el tiempo de adquisición y los tiempos originales de eventos; no inventa fecha de publicación o actualización del organismo. Estado empty solo tras adquisición válida; filtered_empty significa selección sin registros; partial_coverage indica rango fuera de la ventana nominal; unavailable no permite calcular cero. Comparaciones exigen dos ventanas iguales dentro de cobertura nominal, que no prueba completitud instrumental.

No se han introducido datos simulados en producción, ni observaciones GNSS/InSAR/gas inventadas. Los inventarios manuales no se convierten en datos oficiales por haber sido recuperados. Para redistribución nueva de datos, resolver atribución/licencia por activo; que el original ya sea público no concede derechos adicionales.


## Revisión funcional 01 · 2026-11-02

Revisión01: fuentes/cartografía y verificaciones directas en docs/next/OFFICIAL-CARTOGRAPHY.md. IGN topográfica/PNOA/híbrida con atribución de capabilities; sin archivos Esri privados. Tres fichas GVP con fecha de consulta, no alertas ni validación experta. Inventario de cuatro estaciones sin etiqueta de operación actual. La Graciosa usa mayor componente septentrional de Teguise, sin Alegranza/Montaña Clara; regla pendiente de certificación SIG.

MDT real no adquirido: importador preparado, sin dataset simulado en producción. imported_at no es vuelo/levantamiento oficial. no_coverage distinto de vacío/fallo/filtros/solapamiento parcial. GRAFCAN/IHM/EMODnet investigados, sin conexión implementada ni cobertura efectiva por isla verificada.


## Revisión de producto 01 · 2026-11-02

HistóricoUSGS adquirido oficialmente: ventana consultada2000–2026, cajaTenerife/mar,181 filas reconciliadasGeoJSON/CSV/count, todas net=us;4 magnitudes nulas preservadas. Solo1 registro publica horizontalError/depthError/magError; no hay error0 inventado. Originales y manifiesto con URL/política/hash/tiempo de generación comunicada por proveedor, no fecha ficticia de levantamiento. Datos USGS y política ANSS documentadas. No completitud instrumental ni detección homogénea verificadas; mayor parte2000–2008 y otro registro2019.

Fuentes primarias de contexto: IGN descripción geológica/sísmica de Tenerife, IGME guía del Teide, GVP383030, MITECO y CNH380178. Son síntesis documentales con consulta y publicación desconocida explícita, no niveles oficiales vigentes. Hospital sin geometría, capacidad/operación no certificadas. Polígonos municipales son los heredados, no inventario oficial nuevo. KMZ/archivo privadoEarth no usados como datos validados. No se ha adquirido históricoIGN/multiseñal; no declarar caída general por un404 de URL FDSN probada sin acreditar interfaz oficial.


## Salto funcional multinsular · 0.4 · 2026-11-02

Nuevos archivos: `risklab_next/data/observatory/ign-2023-2024` (consulta oficial IGN3609 filas,73 originales locales y extracción pública de tablas,criterios/total/hashes/licencia compatible CC BY4); `ign-administration` (WFS IGN BDDAE,92 unidades originales/88 municipios derivados,CC BY4,EPSG4326). Original WFS local sin pérdida; restaurador verifica el hash o recupera la respuesta desde el servicio público. GeoJSON completo de88 municipios incluido en formato legible. GVP5 fichas primarias,clasificación morfológica diferenciada de clusters sísmicos. No se promovió KMZ privado ni se generaron observaciones. Fecha descarga no equivale a vigencia operacional.
