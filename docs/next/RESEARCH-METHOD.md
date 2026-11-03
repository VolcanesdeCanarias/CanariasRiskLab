# Especificación reproducible del caso geocientífico · versión1.0

Entrada: snapshotUSGS reconciliado, caja explícita, umbral/tipo de magnitud, intervalo UTC[a,b), celda angular. No se mezclan fuentes o escalas silenciosamente. Incertidumbres conservadas como nulas cuando no se publican. Método/código y dependencias geográficas identificados mediante SHA256.

1. Selección: coordenadas en caja de estudio; magnitud no nula≥umbral; tipo especificado o mezcla explícita. No atribución causal al edificio volcánico.
2. Periodo actual[a,b), previo[a−(b−a),a); duración en días = segundos/86400. Si una ventana excede consulta original, count=null y sin interpretación de actividad. El dato fuente retornado vacío dentro de la consulta no acredita ausencia de detecciones reales.
3. Tasa del catálogo=n/días×365,25. Razón=tasaActual/tasaPrevia, nula si no hay cobertura o denominador0. No infinidades ni etiquetas de riesgo. Escalas mezcladas/desconocidas no producen mediana de magnitud comparable.
4. Distancia epicentral por haversine: 2R·atan2(√h,√(1−h)), R6371,0088km; h=sin²(Δφ/2)+cosφ1·cosφ2·sin²(Δλ/2). Tomar mínimo por observación y mediana de mínimos. No profundidad, error de localización ni corrección elipsoidal. N<2 devuelve null. Mediana de distancia redondeada a9 decimales de km para estabilizar identidad numérica entre bibliotecas matemáticas; no expresa precisión física de la localización. Coordenadas repetidas se cuentan, no se eliminan sin evidencia.
5. Celdas: floor((lon−oeste)/paso), floor((lat−sur)/paso); pasos0,025/0,05/0,1°. Son recuentos de registros, no clustering físico ni intensidad/riesgo. La escala angular varía en metros con latitud.
6. Sensibilidad descriptiva: repetir recuentos con umbral+0,5 y+1 conservando tipo/área/ventanas. No estima Mc ni elimina sesgos instrumentales.
7. Conexión territorial: point-in-polygon sobre polígonos heredados versionados; calidad/vigencia no certificadas, sin exposición. Documentación de parque/hospital separada; sin inventar geometrías o asignar criticidad.
8. Interpretación: herramientas/plantillas acotadas sobre resultados y corpus primario; evidencia por campo. La falta de completitud/estabilidad impide inferencias estadísticas de actividad, causas, unrest, alertas o predicciones.

Validación técnica: recuentos contrastados con consultas SQL independientes sobre el CSV oficial; distancias contrastadas con ley de cosenos esférica y vector analítico de1°; periodos excluyentes y año bisiesto; series distinguen exclusiones/ausencias; corrupción/nulos; identidad de ejecución y repetición CLI sin red. Son pruebas de software/matemática y procedencia, no validación geofísica de causalidad.

Repetición: descargar ZIP evidencias, obtener versión de código que corresponda al hash/método y ejecutar `python3 tools/reproduce_research.py run.json` desde raíz con dependencias README. Si cambian código, contexto, geografía, originales o parámetros, debe rechazar la identidad anterior. Un servidor USGS puede revisar su catálogo: el ZIP conserva bytes originales de esta versión; repetir la URL de consulta en otra fecha no obliga al proveedor a devolver el mismo snapshot.
