# RiskLab NEXT 0.5 · observatorio de actualización continua

Implementación funcional en `integration/next-phase1`, PR #2 en borrador. No se ha fusionado, desplegado ni modificado el servicio Render. No es un sistema oficial de vigilancia, predicción o alerta.

## Qué probar

Preparar dependencias como indica README y ejecutar `python3 abrir.py`. Abre `/next/?mode=continuous` y arranca un recolector en el servidor local. El navegador puede cerrarse: la adquisición continúa mientras siga ejecutándose Python. Para otros procesos: `python3 -m risklab_next.continuous.worker`. La interfaz nunca llama directamente a IGN/USGS para adquirir el canal continuo.

1. Comprobar las dos tarjetas de fuente, latido del recolector y última sincronización válida. IGN principal y USGS complementaria son selecciones explícitas: no hay sustitución automática ni suma de catálogos.
2. Elegir 24 h, 7 días, 30 días, un año o histórico acumulado; comprobar la cobertura. El corte se fija en la ventana de la consulta válida, no en la hora de finalización de HTTP. Nunca se rellena un periodo no adquirido.
3. Cambiar territorio, magnitud, escala o profundidad; ejecutar. Ciudadanía/Investigación comparten cálculo y captura. Las magnitudes se distribuyen por escala, sin convertirlas.
4. Seleccionar una barra o un evento; revisar original público, primera/última observación local, revisiones y huellas. Los originales HTTP completos permanecen privados.
5. Elegir periodo fijo UTC: conserva exactamente sus límites, incluso la precisión subsegundo del corte, cuando se sincroniza otra vez. Las revisiones y publicaciones tardías dentro de ese periodo sí pueden actualizar sus datos; exportar JSON congela datos y método.
6. Solicitar sincronización manual: encola trabajo, no ejecuta una descarga desde el hilo HTTP. Respeta exclusión mutua, mínimo global de 60 segundos y Retry-After. El botón no elude el backoff.
7. Exportar JSON/CSV y repetir: `python3 tools/reproduce_continuous.py ruta/run.json`. No requiere red ni la base privada. Los recorridos históricos IGN 2023–2024, USGS y las herramientas heredadas siguen disponibles.

## Arquitectura operativa

- `continuous/connectors.py`: endpoints oficiales fijos, transporte HTTPS con verificación TLS, validadores específicos y contrato `Connector`/`Batch`. Límite de respuesta 8 MB; conexión 8 s y lectura 25 s. No acepta URL del navegador ni sigue redirecciones.
- `continuous/worker.py`: planificación en servidor, comprobación de trabajos cada 5 s y leases transaccionales SQLite de 180 s. Dos recolectores que comparten la misma base no descargan el mismo trabajo a la vez. Inicio explícito en `abrir.py` o CLI; importar Flask no inicia ingestas.
- `continuous/store.py`: SQLite WAL, transacciones atómicas, cuerpos HTTP principales comprimidos en almacenamiento privado, SHA-256, adquisiciones, intentos, observaciones, versiones inmutables y cambios. Estado/versión actual mutable; versiones anteriores no se sobrescriben. Directorio local privado y fichero 0600. Los cuerpos y las bases no tienen ruta HTTP pública.
- `continuous/api.py`: lecturas consistentes por transacción; comprobación de versión y del último cuerpo HTTP antes de analizar; consultas reproducibles, detalle público del evento, estado, salud y encolado limitado. Capturas analíticas comprimidas e inmutables y caché persistente: una lectura repetida del mismo estado no crea otra captura.
- `continuous/analysis.py`: método nuevo `continuous-catalogue-descriptive/1.0`, ventanas UTC semiabiertas, comparación temporal de duración idéntica, comparación territorial de la misma fuente, series, histogramas por escala y agrupaciones descriptivas. No cambia métodos científicos heredados.
- `next/continuous.mjs/css`: interfaz específica, consulta de estado cada 5 s mientras está abierta, refresco de análisis cuando cambia la adquisición/estado. No mueve la cámara en sincronizaciones ni aplica silenciosamente filtros que el usuario está editando. Fallo del servidor conserva la última vista con aviso.

El almacenamiento se configura mediante `RISKLAB_CONTINUOUS_DB`; por defecto `.risklab-next/continuous.sqlite`. Observaciones identificadas por `(fuente, identificador)`: no se deduplican IGN/USGS entre sí. La huella de versión utiliza campos científicos y registro público normalizados, no cookies ni cambios del HTML de sesión. A→B→A conserva dos contenidos y tres transiciones. Una respuesta con duplicados idénticos cuenta una sola observación; duplicados contradictorios invalidan la adquisición completa.

Si una respuesta válida omite un registro dentro de su ventana, se conserva como `not_returned`, se excluye del recuento confirmado y queda accesible como evidencia sin inferir retirada ni causa. Salir por antigüedad de una ventana móvil no provoca esa marca. Un fallo de consulta no modifica presencias ni versiones. Una reaparición queda registrada. Las revisiones pueden actualizar fecha, coordenadas, magnitud o metadatos publicados; no se interpretan como cambio geofísico.

## Fuentes, fechas y frecuencia

**IGN:** https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias . Consulta regional móvil de aproximadamente 10 días, Canarias y entorno marino. Encabezados y filas completos validados; tabla vacía sin confirmación explícita no equivale a cero. Intervalo mínimo normal 600 s, más duración de adquisición y comprobación de planificación. [Política de datos IGN](https://www.ign.es/web/ign/portal/politica-datos), compatible CC BY 4.0, con atribución.

**USGS ComCat:** https://earthquake.usgs.gov/fdsnws/event/1/query . Consulta de terremotos de 30 días, 26–31 N / −19 a −12, límite local 10.000. Reconciliación con `/fdsnws/event/1/count`: el servicio de consulta no debe confundirse con el feed, cuyo metadato `count` no siempre existe en FDSN. Se conserva valor y hash de la comprobación de recuento. Se rechaza discrepancia o posible truncación. Intervalo normal 900 s. No sustituye el catálogo regional ni acredita microsismicidad completa. Se conservan `net`/`code` cuando publicados en el registro original. [Documentación FDSN](https://earthquake.usgs.gov/fdsnws/event/1/) y [créditos/condiciones USGS](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); no atribuir automáticamente dominio público a todos los datos de redes externas.

Fechas separadas: inicio/final de consulta, evento, generación de respuesta cuando existe, revisión de origen USGS cuando existe, primera/última observación local. `publication_at` es nula cuando la interfaz no proporciona fecha de publicación. HTTP Date y primera detección local no se presentan como fecha de publicación. La latencia de publicación es **no determinable** con estas interfaces; no se deduce de la edad del último evento. Una generación USGS antigua se marca `stale_response_generation`, sin diagnosticar por ello retraso de publicación de cada evento.

Cadencias elegidas conservadoramente para este prototipo; no se afirma que sean cuotas oficiales garantizadas. Máximo dos intentos por ciclo ante conexión, timeout o 5xx; no reintento inmediato para 403, 429, datos inválidos o generación antigua. Backoff persistente según fallos, hasta 32 min salvo Retry-After mayor; Retry-After numérico/fecha HTTP se respeta también en solicitudes manuales. Los errores almacenan código y HTTP cuando se conoce, sin volcar HTML o credenciales al cliente.

## Estados y límites científicos

`updated` describe una **consulta válida reciente**, no actividad o ausencia de actividad. `delayed` conserva el último éxito cuando hay error o se excede la tolerancia de actualización (dos intervalos más 60 s). `unavailable` significa que no existe éxito disponible. La cobertura de la consulta se informa por separado: `covered_nominally`, `partial`, `no_coverage`. El latido caduca a los 180 s; `/api/v1/continuous/health` responde 503 si el recolector no tiene latido reciente, aunque las consultas sobre datos guardados sigan disponibles.

Inicialmente IGN ofrece 10 días y USGS 30 días. **30 días/un año de IGN no están completos al arrancar**; histórico significa lo acumulado por el recolector, no importación automática del archivo 2023–2024. Un año solo será completo nominalmente tras acumularlo o incorporar un backfill oficial validado. Se devuelve `count=null` para cobertura parcial/desconocida y `observed_count` para los registros disponibles. No se dibujan barras positivas ficticias cuando el recuento es cero. Cobertura nominal no garantiza detección, estabilidad de red ni publicación exhaustiva.

Clasificación territorial por polígonos CRS84 heredados, con hash y validez actual no acreditada; registros marinos no se asignan a isla más cercana. Se mantiene separada de la capa oficial BDDAE del recorrido territorial. No es una delimitación jurídica. Las incertidumbres no publicadas son nulas, nunca cero. Hipocentros 3D mantienen la aproximación de referencia vertical existente; no se añade MDT ni batimetría.

Las agrupaciones son celdas de 0,1° × bloques UTC desde el inicio del periodo. No focos físicos, clusters causales, anomalías, aceleración volcánica o cambio de régimen. La asistencia determinista cita adquisición y ejecución y se abstiene ante estas interpretaciones. Institucional continúa 403, sin permisos por selector.

## Evidencia real y pruebas

Ver `continuous01/ACQUISITIONS-PUBLIC.json`: primera adquisición IGN de 21 eventos; dos sondeos programados posteriores incorporaron un registro nuevo cada uno, llegando a 22 y 23. En Madrid fueron aproximadamente 15:02, 15:12 y 15:22 del 3/11/2026; el registro científico adjunto conserva UTC 14:02, 14:12 y 14:22. Duplicados 21 y 22 respectivamente. No son registros simulados ni una promesa de erupción/actividad.

En la prueba de navegador real se observó automáticamente otra adquisición del servidor, sin pulsar sincronización: cambió la adquisición y el corte, manteniendo cámara y filtros. El número seleccionado de 24 h siguió siendo 6: no se inventaron nuevos eventos para demostrar la interfaz. En ese recorrido no se observaron revisiones reales; las revisiones, reversión, desaparición/reaparición y fallos se verifican con fixtures exclusivamente de tests.

USGS devolvió cero eventos, contrastado con su recuento oficial, permaneciendo independiente. El registro conserva un fallo inicial de validación durante el desarrollo del adaptador FDSN; se corrigió la diferencia de contrato y no se ocultó como un catálogo vacío.

Diez capturas reales, móvil/escritorio, y `LIVE-EVIDENCE.json`: sin errores JavaScript ni desbordamiento móvil; cámara conservada entre adquisiciones. Se registraron 111 respuestas de imagen WMS 200 y 16 de imagen 502: la cartografía parcial se advierte por separado, sin borrar observaciones ni cambiar sus recuentos. No se sustituyeron teselas por imágenes inventadas.

## Operación, persistencia y Render — sin despliegue

`deploy/render-next.example.yaml` es solo un ejemplo con autoDeploy desactivado. **No modifica `render.yaml` ni crea servicios.** Tras aprobación se requeriría un disco persistente/plan compatible y una instancia única, con web y recolector en la misma instancia: Render no comparte discos locales entre servicios independientes. `python -m risklab_next.continuous.runtime` supervisa Gunicorn y worker y hace fallar el proceso si alguno termina. En Render rechaza una base fuera de `/var/data/`. PostgreSQL/almacenamiento compartido e índices espaciotemporales son necesarios para escalar a varias instancias; no se afirma haber probado un despliegue Render.

Copia online privada: `python3 tools/audit_continuous.py --backup /ruta/privada/observations.sqlite`. No copiar la base activa ignorando WAL. Restaurar con procesos detenidos, conservar primero el original, ejecutar la auditoría sobre la copia y volver a arrancar; las claves únicas y leases evitan duplicar versiones tras reinicio. El ejemplo no contrata disco ni servicios. No incluir bases/backups/HTML crudo en GitHub ni en rutas públicas.

No hay borrado automático: se conserva el histórico. Al alcanzar 5 GB de base, 100 MB libres mínimos o el presupuesto analítico de 20.000 observaciones se requiere intervención; no se trunca silenciosamente ni se inventa cobertura. Los contadores de versiones, tamaño, auditoría y errores deben revisarse. Falta archivo privado duradero y política aprobada de retención para operación prolongada.

Coste orientativo normal: IGN 144 solicitudes/día y USGS 192 (consulta+count), más reintentos limitados/manuales. La muestra real comprimió cada cuerpo principal IGN a unos 16,6 KB y USGS vacío a 310 bytes: aproximadamente 73 MB/mes para esos cuerpos con 30 días de esas condiciones, **sin contar** crecimiento por eventos/revisiones/capturas/índices/backups. Es extrapolación de una muestra, no una garantía ni precio Render. Software local sin coste de API o LLM; tarifa de hosting/disco/backup pendiente de comprobar y aprobar antes de desplegar.

## Preparación multiseñal

`Connector.fetch → Batch` separa transporte, validación, procedencia y almacenamiento. El tipo actual admitido es `seismic_event`: no se activan GNSS, InSAR ni geoquímica ficticios. Cada nueva familia requiere fuente/licencia acreditadas, contrato de unidades/CRS/datum/tiempos, validador, proyección de almacenamiento y método de análisis revisados. No se reutiliza una magnitud/profundidad como variable geodésica. Fuente observada, cálculo, incertidumbre y comunicación oficial seguirán separados.
