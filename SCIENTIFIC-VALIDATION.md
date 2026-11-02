# Validación científica y límites

| Producto/método | Naturaleza | Validación / uso permitido |
|---|---|---|
| Registros IGN/USGS adquiridos | Observaciones publicadas por organismo | Validación sintáctica P0 no acredita completitud, precisión ni causalidad |
| Recuentos, Mmax, comparación de igual duración | Descriptivo `descriptive-counts/1.0` | Pruebas de UTC, intervalos excluyentes, negativos, nulos, cobertura y reproducción; no inferencia causal |
| Plantilla explicativa | Explicación determinista con evidencia | Cuenta registros de esa selección; no modelo predictivo ni interpretación científica avanzada |
| Índice RiskLab, anomalía, régimen, migración | Legado experimental | Fórmulas intactas; falta baseline independiente, incertidumbre, backtesting y revisión |
| Focos/agrupaciones/enjambres | Heurísticas experimentales heredadas | No equivalen a focos físicos activos ni precursores; radios/ventanas y sensibilidad pendientes |
| Score territorial/proximidad | Cálculo experimental heredado | No estima exposición, vulnerabilidad, daño ni riesgo; requiere escenarios y datos fiables |
| PEVOLCA manual 2026-04-06 | Transcripción histórica | No verificado vigente; nueva UI no reproduce semáforo como actual |
| Exclusión La Palma 2026-01-15 | Geometría histórica heredada | No usar como zona de seguridad vigente |
| Hipocentros NEXT 3D | Representación aproximada | −profundidad catálogo sobre elipsoide, sin datum convertido; sin MDT/batimetría |
| Referencias volcánicas / equipos | Inventario manual | No acreditan actividad presente, operación de sensores o carácter crítico |

Escala experimental heredada gris/azul/morado/negro no es PEVOLCA. No se muestra como señal oficial en NEXT. Un catálogo válido vacío nunca activa índice 9; el legado P0 evita ese cálculo vacío sin cambiar la fórmula. No hay cambios de metodología científica en esta integración.

Hallazgos que requieren trabajo posterior: baseline usa subconjunto solapado; aceleración compara duraciones distintas; régimen umbral potencialmente inalcanzable; clusters espaciales transitivos sin profundidad y coste elevado; fechas heredadas de serie pierden año y fallan en 29/02, Mmax inicializado a cero sesga magnitudes negativas. No ocultar estos problemas con un diseño nuevo. Reproducciones y archivos constan en FEATURE-MATRIX. No presentar los algoritmos heredados como validados mientras se mantengan accesibles.

Revisión necesaria: sismología (completitud/errores/reconciliación de catálogos), geodesia (datum/LOS/InSAR), volcanología (fichas/historia/hipótesis), SIG (límites/exposición) y protección civil (documentos vigentes/procedimientos). Cada aceptación tendrá revisor, fecha, datasets, versión de código, parámetros, comparación de referencia y límites de aplicabilidad. La aprobación técnica de un PR no sustituye revisión científica.


## Revisión funcional 01 · 2026-11-02

Revisión01: fichas GVP son referencias documentales verificables, no evaluación de actividad. Encuadres de sistema no son límites geológicos/peligro. descriptive-counts/1.1 añade selección municipal/profundidad y abstención fuera de cobertura; fórmulas experimentales heredadas intactas. WMS de sombreado/relieve/batimetría es imagen, no validación de elevación 3D. Importador/renderer probado con fixtures de tests; ningún MDT real validado todavía. Malla reducida/LOD no añaden precisión ni rellenan nodata; datum sin convertir solo aproxima una vista, no una medición.


## Revisión de producto 01 · 2026-11-02

catalogue-rates-spatial/1.0 implementa tasas de registros, ventanas iguales UTC, vecino más próximo epicentral, celdas y sensibilidad. Contraste técnico independiente SQL/cosenos esféricos, nulos, leapyear y reproducción CLI; revisión científica experta sigue pendiente. No p-valores o bandas ficticias ante completitud/detección desconocidas; no inferir actividad real, origen volcánico o causalidad. Mezcla de escalas no produce mediana de magnitud comparable. Umbral de consulta no es Mc.

Correlación documental crítica: catálogoUSGS con huecos no invalida sismicidad documentada porIGN; no traducir cero de la selección o fuente a quietud. Corpus vinculado a afirmaciones y tipos de relación, no a polígonos/estructuras inventados. Proximidad/celda no es foco físico ni riesgo. Contexto hospital/parque sin geometría acreditada no permite exposición. Asistencia determinista con abstención, no IA científica avanzada ni comunicación institucional. Ver método/reportes y validación requerida antes de operación.


## Salto funcional multinsular · 0.4 · 2026-11-02

Procedencia/integridad IGN contrastadas contra originales y total publicado, no certificación de completitud instrumental. UTC y periodos semiabiertos; previo de duración exacta; no conversión de escalas. Celdas/bloques solo agrupamientos descriptivos. Intersecciones administrativas no son exposición ni peligro. Caja Teide manual de navegación: recorta observaciones, no adscribe origen. Datum profundidad no especificado en tabla; sin transformación al MDT. Validación científica experta pendiente.
