# MDT terrestre local documentado · capacidad experimental de representación

**No se incluye un MDT real en esta entrega.** El WCS actual CNIG no está habilitado para descarga en este entorno y el enlace histórico responde 404. Se entrega el importador y el renderizador, probados con fixtures exclusivamente bajo tests; no se presentan esos fixtures como relieve real.

Para una revisión local posterior, descarga un GeoTIFF terrestre auténtico IGN/CNIG bajo licencia compatible CC BY4.0 y conserva el original. Comprueba producto, cobertura, resolución, fecha del levantamiento, licencia y datum vertical. El importador requiere EPSG:4326 y norte arriba; si el producto es UTM/REGCAN95, la reproyección debe hacerse explícitamente con herramienta SIG, conservando sus parámetros y la resolución de origen. El importador no realiza conversiones de CRS o datum silenciosas.

Con el entorno Python activado, instala la dependencia opcional:

```sh
python3 -m pip install rasterio
python3 tools/import_cnig_dem.py /ruta/al/MDT-geografico.tif \
  --source-url 'https://centrodedescargas.cnig.es/CentroDescargas/' \
  --product 'IDENTIFICADOR_REAL_DEL_PRODUCTO' \
  --vertical-datum 'REFERENCIA_VERTICAL_DOCUMENTADA_DEL_ARCHIVO' \
  --resolution-m RESOLUCION_REAL_EN_METROS
python3 abrir.py
```

Sustituye los marcadores por metadatos comprobados, no por valores estimados. La URL por sí sola no acredita procedencia: corresponde al operador conservar el archivo oficial y su descarga/metadatos. La herramienta verifica estructura y declaración de licencia/fuente, **no certifica autenticidad ni validación científica**.

Escribe solo `.risklab-next/terrain.json` (ignorado por Git), con SHA256 del original, producto, fuente, licencia, referencia vertical, resolución declarada y fecha de importación. Esta fecha no es la del vuelo/levantamiento. Lee píxeles de origen, sin fabricar alturas ni aumentar el tamaño de malla. `--side 65|129|257` controla el presupuesto de visualización; el producto fuente puede tener mucha más resolución que la malla mostrada. Filas norte→sur, coordenadas de centros de píxel. No modifica el GeoTIFF ni los datos originales del proyecto.

El servidor expone exclusivamente el derivado fijo mediante `/api/v1/terrain`, nunca una ruta arbitraria del disco. Sin archivo: `not_configured`; archivo inválido: `invalid`; importación documentada: `documented_import`. La malla se dibuja sobre Cesium con pasos de LOD 4/2/1 según altura de cámara; se omiten triángulos que atraviesan nodata. No se rellenan huecos con cero ni se extrapola fuera de cobertura. No hay colisiones de cámara contra esta malla: no usarla para mediciones ni navegación técnica precisa.

Las alturas de origen se representan sin transformar al elipsoide: es aproximación visual claramente indicada. La profundidad de catálogo de hipocentros mantiene su referencia separada. No hay exageración vertical ni batimetría; no cargar modelos marinos mediante este importador terrestre. La revisión geodésica, el geoide, la validación de un MDT real y las pruebas en Mac con GPU siguen pendientes antes de considerar esta capacidad científicamente apta.
