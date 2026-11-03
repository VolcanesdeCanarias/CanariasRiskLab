# Observatorio continuo 0.5 · resultados de revisión

## Demostración con fuentes oficiales

El 3 de noviembre de 2026, el recolector adquirió 21 registros IGN a las 14:02 UTC. Sin intervención del navegador incorporó un registro nuevo a las 14:12 y otro a las 14:22: 23 identificadores únicos y 23 versiones originales. Los registros repetidos no crearon nuevas versiones. USGS devolvió un catálogo vacío válido, verificado mediante su servicio oficial de recuento; no sustituyó a IGN. Véase [ledger público normalizado](ACQUISITIONS-PUBLIC.json).

Una revisión posterior en Chromium 154 observó otra adquisición programada desde la aplicación iniciada con `abrir.py`. Cambió el identificador de adquisición sin pulsar sincronización; mantuvo cámara, fuente y filtros. Los seis registros del periodo de 24 horas no cambiaron: no se inventaron eventos para la demostración. [Evidencia verificable](LIVE-EVIDENCE.json), [diez capturas reales](captures) y [ejecución exportada](example-run.json).

No hubo revisiones reales durante esta muestra. Las revisiones, reversiones y fallos se probaron con fixtures identificados exclusivamente en tests. Los originales HTTP y la base persistente permanecen privados; solo se adjuntan campos sísmicos públicos, metadatos y huellas.

## Verificación automatizada local

| Grupo | Satisfactorias |
|---|---:|
| Python: P0, históricos y almacenamiento/adquisición continua | 99 |
| Estado de datos en JavaScript heredado | 9 |
| Estado y dimensiones del mapa | 3 |
| Navegador de aplicación heredada | 10 |
| Navegador NEXT, mapa, perfiles y Research | 26 |
| Navegador histórico multinsular | 7 |
| Navegador del observatorio continuo | 9 |
| **Total** | **163** |

Una prueba opcional heredada de red/CDN permanece omitida; la adquisición y revisión reales se ejecutaron por separado y constan arriba. Los primeros intentos de la suite heredada no arrancaron por dependencias locales ausentes; tras preparar el entorno, las diez pruebas pasaron. Se corrigió una carrera entre resize y encuadre que podía mover el mapa al cambiar de perfil; las 26 comprobaciones existentes pasan con sus aserciones originales.

El canal nuevo verifica planificación sin navegador, persistencia/reinicio, exclusión mutua entre workers, duplicados, revisiones y reversión, ausencias/reaparición, fallos 403/429/503, reintentos limitados, recuperación, cobertura, intervalos UTC semiabiertos, caché reproducible, integridad alterada y protección de rutas privadas. En navegador verifica actualización de nuevos eventos, revisión, error/recuperación, desconexión, respuestas tardías, periodos fijos exactos, perfiles, móvil, preguntas y exportaciones.

Las ejecuciones congeladas 0.3, 0.4 y 0.5 se reprodujeron sin red. Se verificó identidad byte a byte de diez archivos protegidos, incluidos `server.py`, `index.html`, `render.yaml`, datos originales y métodos históricos. `git diff --check` no detectó errores.

## Limitaciones observadas

- Cobertura inicial nominal: IGN diez días, USGS treinta. Un año es parcial; no hay backfill validado nuevo.
- Fecha/latencia de publicación no determinadas cuando la interfaz oficial no las proporciona. Consulta reciente no garantiza catálogo completo.
- Cartografía externa: 111 imágenes WMS respondieron 200 y 16 respondieron 502. La aplicación mostró carga parcial sin alterar observaciones; no se afirma disponibilidad cartográfica perfecta.
- Sin MDT/batimetría real validados en NEXT. El 3D sigue siendo una aproximación sobre elipsoide.
- Persistencia local y copia privada probadas. Render solo tiene un ejemplo de configuración; disco, costes, operación prolongada, archivo y escalado requieren revisión y autorización.
- No se habilitaron alertas, predicciones ni Gestión institucional. Sin fusión, despliegue o cambios en `main`.
