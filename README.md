# Canarias RiskLab NEXT · revisión local

Revisión funcional01 · versión0.2, en desarrollo. No es un sistema oficial de vigilancia, alerta o predicción. `/` conserva CanariasRiskLab con P0; `/next/` abre la nueva experiencia.

## Mac

Descarga el ZIP del código de la rama `integration/next-phase1` desde GitHub (Code → Download ZIP), descomprímelo y abre Terminal en esa carpeta. Instala Python 3 y Node.js LTS si no están disponibles. Ejecuta:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
npm ci
python3 abrir.py
```

Se abre http://127.0.0.1:8787/next/ . Para detener: Ctrl+C. El servidor solo escucha en tu Mac. No despliega nada ni modifica Render. Si el puerto está ocupado: `RISKLAB_PORT=8788 python3 abrir.py`. Necesitas conexión para adquisición IGN/USGS y teselas OSM; un 403 se mostrará como fallo, nunca como actividad cero. npm ci instala SDKs con versiones fijadas; no activa servicios de pago. El ZIP de GitHub no contiene dependencias instaladas: no se presenta como paquete offline autocontenido.

Selecciona territorio/fuente/periodo UTC, pulsa Aplicar, explora eventos y abre Investigación. El panel inferior permite cambiar altura con ratón/táctil o flechas de teclado; minimizar/cerrar conserva cámara. Exportación utiliza la selección completa (el cursor de reproducción solo cambia visualización). Perfiles comparten resultados; Gestión institucional es espacio no habilitado con acceso servidor rechazado.

La revisión 01 añade bases topográfica IGN, PNOA e híbrida, navegación municipal/sistemas documentales, filtro e histograma de profundidad y Research con mapa mínimo. El 3D muestra cartografía sobre elipsoide y eventos, **sin MDT ni batimetría reales validados en esta entrega**. Incluye importador local opcional de GeoTIFF auténtico documentado, aún pendiente de prueba con un MDT real. El Earth V2.1 privado conserva su terreno local separado. Capas manuales opcionales no certifican actividad ni instalaciones críticas. No hay logo oficial disponible para incorporar.

Consulta [revisión actual y pruebas](docs/next/REVIEW-01.md), [cartografía oficial](docs/next/OFFICIAL-CARTOGRAPHY.md), [MDT opcional](docs/next/TERRAIN-IMPORT.md), [entrega anterior](docs/next/REVIEW.md), [matriz funcional](FEATURE-MATRIX.md), [arquitectura](ARCHITECTURE.md), [fuentes](DATA-SOURCES.md) y [punto de reanudación](SESSION-HANDOFF.md). No fusionar ni desplegar sin aprobación expresa.
