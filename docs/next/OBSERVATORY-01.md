# Observatorio multinsular · revisión 0.4

Rama `integration/next-phase1`, continuación del PR #2 en borrador. Sin merge ni despliegue. La nueva herramienta está dentro de `/next/`: **Investigar Canarias · histórico IGN**. No es vigilancia oficial.

## Recorrido de revisión

1. Abre con `python3 abrir.py`, como indica README. Pulsa **Investigar Canarias · histórico IGN**.
2. Compara Tenerife y La Palma, 01/07/2024 incluido → 01/01/2025 excluido: 238 registros terrestres en Tenerife, 90 en La Palma; previo Tenerife 232, desde 30/12/2023, exactamente 184 días. Son registros catalogados, no actividad física estimada.
3. Explora las ocho islas, Canarias y entorno marítimo. Los sismos marinos no se asignan a la isla más cercana. Municipio recorta solo el territorio principal, indicado explícitamente. La caja visible opcional se aplica también a la comparación.
4. Selecciona una barra temporal para representar ese bloque en el mapa y restaura el periodo completo. En Patrones, selecciona puntos profundidad/fecha para abrir fichas; revisa magnitudes y activa celdas descriptivas.
5. Investigación ofrece filtros exactos de escala/magnitud/celda/bloque. Ciudadanía conserva cifras y muestra el alcance activo, con menos controles. Cambiar parámetros invalida gráficos, preguntas y exportaciones hasta recalcular. Navegar fichas geológicas conserva el análisis.
6. Territorio → **Consultar municipios del área visible** calcula intersección con polígonos completos IGN. Contornos muestreados solo para dibujar. Los botones municipales encuadran; intersección no equivale a afectación.
7. Pregunta por comparación, información ausente, fuentes o entorno del Teide. Esta última consulta recorta la selección actual a una caja manual de navegación, explicando sus límites; no atribuye origen volcánico. Las respuestas citan fuentes y ejecución. Erupciones/alertas: abstención.
8. Exporta JSON/CSV. Reproduce: `python3 tools/reproduce_observatory.py run.json`, con la misma versión. Cierra para volver a observaciones recientes. El cuaderno USGS anterior sigue disponible por separado.

## Fuentes incorporadas

**IGN histórico, operativo con cobertura limitada:** 3.609 identificadores únicos, consulta pública 27–30 N, −19 a −13, 01/01/2023–31/12/2024. Última fila: 31/12/2024 23:51:42 UTC. No es todo el catálogo desde 1370 ni adquisición automática actual. Los originales completos de 73 páginas se conservan localmente sin alterar. El paquete público incluye extracción transparente de todas sus tablas, URL/criterios/total, hashes de origen y derivado reconciliado, sin campos de sesión del portal. La adquisición por páginas no es una instantánea transaccional. Cobertura de consulta no acredita completitud ni estabilidad de detección.

Adquisición mediante formulario y paginación pública IGN. No se utilizó un endpoint FDSN supuesto. `indice=100` corresponde a la segunda página de 50 filas: el control de duplicados detectó y rechazó la primera tentativa incorrecta. La exportación CSV del portal devolvió solo cabecera y se descartó. Scripts de adquisición usan directorios nuevos. Cita: [IGN, Catálogo de terremotos](https://doi.org/10.7419/162.03.2022). [Política de datos](https://www.ign.es/web/ign/portal/politica-datos): licencia compatible CC BY 4.0.

**Territorio oficial, operativo:** IGN/CNIG BDDAE, [WFS INSPIRE](https://www.ign.es/wfs-inspire/unidades-administrativas). Capabilities declara CC BY 4.0 ign.es. Respuesta original conservada localmente: 92 unidades, incluidos niveles superiores. Paquete público: 88 municipios en GeoJSON transparente con coordenadas/anillos intactos. EPSG:4326, orden GeoJSON longitud/latitud. Fecha de descarga no es fecha de deslinde: versiones individuales no pobladas. La Graciosa pertenece a Teguise. Asignación insular reutiliza relación municipal heredada y convención explícita de la isla habitada, sin crear un municipio.

El original WFS completo ocupa 145,9 MB; se conserva localmente y se identifica por SHA-256. Restauración desde archivo local o descarga pública IGN, con comprobación de hash: `python3 tools/data/restore_administration_original.py original.geojson`. El paquete público incluye los polígonos completos de 88 municipios como GeoJSON legible, con hash individual y combinado; no se analiza con el contorno simplificado.

**Documentación volcánica:** cinco fichas insulares GVP: Tenerife, La Palma, El Hierro, Gran Canaria, Lanzarote, con clasificación/fuentes; no inventario exhaustivo. “Cluster” morfológico de GVP no equivale a agrupación sísmica calculada. Graciosa de Azores GVP382040 no se usa para la isla canaria. Encuadres documentales no son perímetros geológicos.

**Sin simulaciones en producción.** USGS anterior, feeds recientes y referencias manuales permanecen diferenciados. No se suman ni deduplican automáticamente los catálogos. El histórico funciona sin adquisición reciente; imágenes externas requieren red.

## Método y garantías

`ign-multinsular-descriptive/1.0`: UTC, intervalos semiabiertos, máximo 366 días. Previo de duración exacta. Mismos filtros de magnitud/escala/área para comparación, sin conversión de magnitudes, completitud Mc, significación, causalidad o peligro. Umbral −10 incluye magnitudes ausentes; otros umbrales las excluyen. Ausencia de error no es error cero.

Bloques de 1/7/30 días desde inicio, no semanas ISO. Celdas 0,05/0,1/0,2 grados, origen (−19,27), pares celda/bloque. No son focos activos ni clusters físicos y no tienen tamaño métrico uniforme. Gráficos: profundidad publicada y máximo de magnitud por bloque, escala identificada. Mezcla de escalas no genera magnitud convertida.

Intersección: esquinas/segmentos contra polígonos completos con huecos. No se calcula exposición, vulnerabilidad, instalaciones afectadas ni riesgo. Ejecuciones SQLite inmutables y hash de resultados/parámetros/datos/capa/código/geografía. Falta de cobertura no se exporta como cero. API institucional 403: perfil no concede permisos. Sin LLM. `research_v1.py` conserva exactamente el código 0.3 y su reproducción; fachada registra ambos módulos sin cambiar su método.

## Estado real

- **Operativo:** consulta regional IGN 2023–2024, ocho islas/mar, comparaciones, gráficos interactivos, agrupaciones descriptivas, asistencia fundamentada, municipios oficiales por área, exportación/reproducción, perfiles públicos diferenciados y cuaderno anterior.
- **Parcial:** dos años contrastados, cinco fichas volcánicas, completitud sin acreditar, cartografía externa variable, límites cartográficos sin certificación jurídica.
- **Bloqueado en este entorno:** MDT CNIG actual requiere `servicios.idee.es` y según producto `centrodedescargas.cnig.es`, fuera de la política de salida. Herramientas de entorno disponibles solo de lectura/diagnóstico. No se eludió la restricción ni se atribuye al proveedor una caída. Haría falta autorizar esos dominios mediante la configuración del entorno o aportar un GeoTIFF oficial con metadatos/licencia.
- **Pendiente:** MDT real/datum/LOD con datos, batimetría, GNSS/InSAR/gases, instalaciones oficiales, autenticación institucional, revisión científica y archivo gráfico oficial. El 3D sigue elipsoidal con aviso; ortofoto no es elevación.

Capturas/pruebas: `docs/next/observatory01/`. Imágenes WMS genuinas mediante proxy autorizado con TLS; no proxy en producción ni teselas ficticias. Fallos parciales de imagen también se registran. Rendimiento cloud local no equivale a prueba de carga ni a GPU/Mac reales.

## Publicación segura de las fuentes

La revisión automática rechazó subir HTML comprimido a un repositorio público por no poder verificar su contenido como no sensible. La inspección encontró campos de sesión anónima en el HTML del portal. No se reintenta publicar ese contenido ni se cambia de canal para eludir el bloqueo. Los originales completos permanecen intactos bajo `.risklab-next/source-originals`, excluidos de Git y del servidor HTTP. El paquete público contiene únicamente tablas sísmicas extraídas y GeoJSON administrativo legible: todas las observaciones/geometrías necesarias para reproducir los análisis, sin campos de sesión. Se verificaron las 92 piezas de datos públicos y no se hallaron patrones de sesión, Bearer o claves privadas. La extracción conserva 3609 IDs y todos los campos sísmicos; es un derivado documentado, no el HTML original completo.

Retención de originales brutos: local y excluida del paquete público; pendiente de archivo privado duradero con política de acceso/retención. Los datos públicos necesarios para los cálculos sí están incluidos en el ZIP de código.
