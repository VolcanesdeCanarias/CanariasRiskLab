# Instrucciones permanentes de desarrollo

Canarias RiskLab NEXT conserva CanariasRiskLab como núcleo y Earth como componente cartográfico. Aplicar la directiva del promotor de 2026-11-02 y PRODUCT-VISION.md. Trabajar en ramas de desarrollo; nunca fusionar main, desplegar Render ni modificar producción sin autorización expresa. No alterar el PR #1 ni los originales de Earth. Mantener todos los originales de datos.

Conservar garantías P0: allowlist HTTP, validación íntegra de adquisición, estados empty/unavailable separados, sin indicadores ante fallo o selección vacía. No cambiar métodos científicos heredados sin decisión y validación documentadas. No añadir datos simulados a producción: fixtures exclusivamente bajo tests. No equiparar anomalía, proximidad o recuento con riesgo, causalidad, erupción o alerta.

Antes de publicar código/activos, revisar permisos de redistribución y datos restringidos. Earth es privado: no copiar sus imágenes/terreno o catálogo candidato al repositorio público sin permiso documental. No inventar logotipos; usar únicamente archivo oficial aportado/autorizado. No activar servicios de pago. La selección de perfil no concede permisos: acceso institucional en servidor.

Al trabajar, actualizar los diez documentos maestros, la matriz funcional y el punto de reanudación. Diferenciar código implementado, preservado en legado, experimental y planificado. Ejecutar unittest, pruebas JS y navegador proporcionales al cambio. Usar respuestas de test claramente identificadas. Documentar cobertura, incertidumbre, datum, licencia, versiones y evidencia. No declarar una fase completa porque exista documentación o una maqueta.

Decisiones técnicas rutinarias autorizadas: avanzar sin pedir nueva confirmación. Elevar únicamente restricciones de permisos, decisiones científicas/materiales o acciones fuera de alcance. No introducir agentes autónomos sin justificación técnica.


## Revisión funcional 01 · 2026-11-02

Revisión funcional 01 incorporada: docs/next/REVIEW-01.md. No redimensionar cámaras ocultas; conservar mínimo de mapa, selección y filtros entre perfiles. Separar fallos de cartografía/adquisición/falta de cobertura. Importación MDT solo real y documentada; fixtures de alturas exclusivamente en tests.
