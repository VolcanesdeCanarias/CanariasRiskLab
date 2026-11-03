# Revisión funcional 01 · entrega 0.2.0

Trabajo sobre `integration/next-phase1`, actualización del PR #2 en borrador. Sin otro prototipo, sin cambios en main, PR #1, Earth o Render. Directiva maestra y matriz F01–F60 conservadas.

## Resultado por incidencia

| ID | Implementado y comprobación | Límite pendiente |
|---|---|---|
| MAP-01 | Contenedor de mapa en flujo real; estado geográfico separado de filtros/perfil; no redimensionar vista oculta ni frustum con altura cero; restauración explícita de centro/zoom y pose 3D. Pruebas repetidas Ciudadanía/Investigación/Gestión en 1440×1000, 1280×720, 768×1024 y 390×844 | Prueba local del promotor en macOS pendiente para esta revisión; Chromium Linux no certifica Safari |
| MAP-02 | Research ajustable, minimizar a cabecera, restaurar/cerrar; presupuesto dinámico conserva ≥320px de mapa escritorio/≥250px móvil. En pantallas muy cortas hay scroll, nunca altura negativa o franja | Panel pequeño requiere scroll interno para herramientas; accesibilidad completa aún pendiente |
| MAP-03 | Bases OSM, topográfica IGN, PNOA e híbrida intercambiables, atribución y estado de imagen independientes de adquisición sísmica. Capabilities y GetMap reales comprobados | Servicios externos pueden fallar parcialmente; GRAFCAN y base de relieve numérico pendientes de verificaciones específicas |
| MAP-04 | Cesium admite cartografía oficial regional, globo elipsoidal e importación local opcional de GeoTIFF oficial documentado; malla con LOD, nodata preservado y sin exageración | **No hay un MDT real descargado/validado en esta entrega.** No se declara resuelto el relieve/batimetría. Geoide, cobertura y precisión requieren validación. Renderer/importador probados con fixtures de test, no con alturas inventadas en producción |
| MAP-05 | Cambio 2D/3D conserva catálogo, parámetros temporales, filtros, evento seleccionado y contexto. Transferencia acotada del encuadre; no capturar límites globales de un contenedor oculto. Navegación nueva explícita solo por selección territorial/usuario | Vistas muy inclinadas sin intersección de las cuatro esquinas recuperan último ámbito seguro; no se promete equivalencia fotogramétrica exacta |
| MAP-06 | Capas separadas por observaciones y referencias manuales; leyenda plegable y se oculta al abrir capas; base y calidad tienen estados separados | Inventarios manuales no equivalen a operación actual ni exposición/criticidad |

## Recuperación funcional y rigor

Registro municipal y navegación por sus 88 geometrías, ocho islas y mar, encuadre dedicado a La Graciosa y tres sistemas documentales. Corregida la regla de componentes de Teguise para no agrupar Alegranza/Montaña Clara como La Graciosa. Versionado de normalización `catalogue-normalization/1.1`; las instantáneas anteriores permanecen inmutables.

Filtro municipal por ID y profundidad mínima/máxima aplicado en servidor al mismo dataset, comparación y exportación. La navegación a un sistema volcánico cambia cámara/ficha, no inventa límites geológicos ni recorta silenciosamente eventos. Las tres primeras fichas citan los registros GVP Tenerife 383030, La Palma 383010 y Hierro 383020; son revisión documental verificable, no validación científica experta ni informe de vigilancia actual.

Recuperado histograma de profundidad; serie temporal UTC, comparación, exportaciones y explicación conservadas. Cuatro estaciones recuperadas como inventario manual **sin trasladar su etiqueta «operativa» a un estado actual**; no hay telemetría ni series GNSS. Los 32 equipamientos siguen como referencias con procedencia heredada, no instalaciones críticas certificadas. El análisis territorial de proximidad/exposición avanzado permanece en legado y pendiente de migración/validación; no se reemplaza con una falsa evaluación de riesgo.

La API diferencia ahora `no_coverage` (periodo completamente anterior a cobertura nominal) de `partial_coverage`, `filtered_empty`, `empty` y `unavailable`. Ante falta de cobertura o fallo no hay recuento cero, histograma tranquilizador ni exportación de catálogo vacío. Al cambiar experiencia, los filtros avanzados permanecen activos y el filtro de profundidad se anuncia también en Ciudadanía.

Gestión institucional sigue bloqueada con 403 de servidor; no se habilitan herramientas de emergencia ni escenarios no validados. El logotipo oficial continúa pendiente del archivo auténtico; no recreado.

## Pruebas y revisión real

- Backend: **49 pruebas** (incluye P0, integridad byte a byte, nuevos filtros, cobertura, catálogos y validación de malla).
- JS de estado heredado: **9 pruebas**.
- Unidad de layout/encuadre: **3 pruebas**.
- Navegador legado: **10 pruebas aprobadas** y un smoke live opcional omitido.
- Navegador NEXT: **19 pruebas**: once anteriores y ocho específicas de revisión, con transiciones repetidas, cuatro viewports, altura mínima, filtros/selección, fuentes de imagen fallidas, fichas, municipio, profundidad, ausencia de cobertura y renderer MDT de prueba.
- Total de la ejecución final archivada: **90 comprobaciones automatizadas aprobadas**. Ver logs en `review01/`; no contar el smoke omitido como aprobado.

Chromium 154.0.8037.57, Python3.12 y Node24, Linux/SwiftShader. No es prueba de Safari, GPU Mac, FPS de catálogos grandes ni validación científica de métodos heredados. CI remota debe comprobarse tras actualizar el PR.

Revisión live sin fixtures: IGN respondió con 20 registros; 4 en selección de 24h, y se cargaron 24 imágenes cartográficas en la ejecución de 2026-11-02T17:09:56Z (18:09:56 CET). Transportó imágenes auténticas IGN mediante el proxy autorizado, sin desactivar TLS ni sustituir respuestas. Una ejecución anterior tuvo imágenes HTTP502: la UI comunica carga parcial, preservando datos. Los detalles están en [evaluación de cartografía](OFFICIAL-CARTOGRAPHY.md) y `review01/LIVE-EVIDENCE.json`.

Capturas reales: [escritorio](review01/captures/desktop-live.png), [Research](review01/captures/research-live.png), [3D sin MDT](review01/captures/earth-live.png), [móvil](review01/captures/mobile-live.png). No son renders de diseño. El sombreado/batimetría que aparece en el mapa ráster es imagen oficial, **no geometría 3D medida**.

## Ejecutar en Mac

Mismo procedimiento README: entorno virtual Python, requisitos, `npm ci`, `python3 abrir.py`. Entrada `/next/`, legado en `/`. Sin servicios de pago, despliegue o modificaciones de la aplicación pública. El ZIP de código requiere dependencias; no es paquete offline. [Importación de MDT opcional](TERRAIN-IMPORT.md) requiere archivo oficial real y dependencia rasterio solo para esa operación.

## Riesgos y siguiente paso

Completar descarga y validación de MDT terrestre real (dominio actual fuera de política de red), referencias verticales, condiciones GRAFCAN, cobertura/licencia IHM/EMODnet y prueba Mac. Históricos candidatos siguen sin ingestión automática; sus datos no se inventan ni se dan por completos. Pendientes migración de capas/analítica restante, rendimiento del render de miles, archivo crudo/retención, seguridad XSS del legado, endurecimiento público y autenticación institucional. La API de terreno permite revisión local, no certifica autenticidad de un archivo porque el operador declare URL/licencia.

No fusionar ni desplegar sin aprobación expresa. PR en borrador y capacidades parciales señaladas; esta iteración no completa toda Fase1 ni resuelve MAP-04 como relieve validado.
