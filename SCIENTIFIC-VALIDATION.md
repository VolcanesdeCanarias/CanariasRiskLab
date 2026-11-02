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
