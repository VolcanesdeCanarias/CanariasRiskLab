# Punto de reanudación · 2026-11-02

## Estado exacto

Repositorio canónico VolcanesdeCanarias/CanariasRiskLab, rama `integration/next-phase1` desde `ac9ff9c207625426e34ac047997d391c149a10a0` (P0). Proyecto local `/workspace/canarias-risklab-next`; originals `/workspace/CanariasRiskLab` y `/workspace/risklab-earth-v2.1` sin modificar. Main auditado `647bec9544e2bc2fbee36731e850cca60b685c2a`; Earth v2.1 `6521581003cdf23ad98d84cfcc476872b3a5a297`. No tocar PR #1 ni Render. El PR de esta rama debe ser borrador, nunca fusionado sin autorización.

Implementado: `/next/`, API común de observaciones/análisis por snapshot, SQLite local, ocho islas/mar y registro 88 municipios, interfaz luminosa con perfiles y Research ajustable, 2D/3D elipsoidal, filtros/tiempo/fichas/exportaciones, explicación determinista y rechazo de acceso institucional. Garantías P0 incluidas; index.html/datos/render.yaml idénticos a base (INTEGRITY.json). Cincuenta o sesenta documentos no sustituyen funcionalidades: FEATURE-MATRIX distingue lo migrado, preservado y previsto. Fase 1 solo parcial.

Pruebas: 41 Python, 9 JS heredadas, 10 browser legado y 11 browser NEXT = 71 aprobadas. Un smoke live opcional del legado omitido. Revisión live separada: IGN 20 registros/4 en 24h; USGS HTTP200 vacío regional; sin mocks. Teselas externas no disponibles en este navegador, contornos locales visibles; 3D sin MDT/batimetría. Capturas y evidencia en docs/next, logs allí. Benchmark 13.573 registros candidatos: mediana 6,89 ms del análisis descriptivo; no validación de catálogo ni FPS Mac. CI configurada, verificar estado remoto tras crear PR; no darla por pasada sin consultarla.

## Abrir y repetir

README.md incluye `python3 -m venv .venv`, activar, `pip install -r requirements.txt`, `npm ci`, `python3 abrir.py`. URL 127.0.0.1:8787/next/. Sin publicar ni modificar producción. SDKs y Python requieren instalación: ZIP de código no equivale a paquete offline autocontenido. Base de datos local `.risklab-next/` ignorada y no accesible HTTP. `RISKLAB_NEXT_DB` permite ruta alternativa.

## Próxima tarea concreta

F1-08: diseñar y probar retención acotada de bytes originales de adquisición, separar observación/publicación/adquisición, permitir reproducir normalización con checksum y versión de adaptador. Implementar interfaz de almacenamiento y pruebas de corrupción/errores/disco lleno/retención, sin tocar fórmulas heredadas. Cerrar términos de redistribución antes de publicar datos adicionales. Después: OpenAPI y navegación municipal/área con revisión de límites, migración de capas por unidad con pruebas. Ver ROADMAP.

Bloqueos materiales: licencias MDT/imagen Earth y datos candidatos; verificación científica de fichas/Tagoro; archivo oficial del logotipo; proveedores/datos GNSS/InSAR; revisión científica para algoritmos avanzados; permisos/identidad institucional antes de abrir ese espacio. No detener decisiones rutinarias ni simular su solución. No servicios de pago, alertas oficiales, recomendaciones operativas, merge o despliegue.

## Publicación de esta entrega

PR en borrador: https://github.com/VolcanesdeCanarias/CanariasRiskLab/pull/2 . Rama de revisión: https://github.com/VolcanesdeCanarias/CanariasRiskLab/tree/integration/next-phase1 . No aprobado para merge/despliegue.

Código y documentos únicamente en rama de integración. Usar PR en borrador con enlace al informe y capturas; el árbol incluye P0 desde su commit sin alterar la rama/PR originales. Antes de una siguiente sesión, leer este archivo y comprobar HEAD/estado del PR/CI en GitHub, no asumir que las ramas se mantienen en los SHA anteriores.
