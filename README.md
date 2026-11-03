# Canarias RiskLab NEXT · revisión local

Observatorio de actualización continua · versión 0.5, en desarrollo. No es un sistema oficial de vigilancia, alerta o predicción. `/` conserva CanariasRiskLab con P0; `/next/` abre la nueva experiencia.

## Mac

Descarga el ZIP del código de la rama `integration/next-phase1` desde GitHub (Code → Download ZIP), descomprímelo y abre Terminal en esa carpeta. Instala Python 3 y Node.js LTS si no están disponibles. Ejecuta:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
npm ci
python3 abrir.py
```

Se abre http://127.0.0.1:8787/next/?mode=continuous . Para detener: Ctrl+C. El servidor solo escucha en tu Mac. No despliega nada ni modifica Render. Si el puerto está ocupado: `RISKLAB_PORT=8788 python3 abrir.py`. Necesitas conexión para adquisición IGN/USGS y teselas OSM; un 403 se mostrará como fallo, nunca como actividad cero. npm ci instala SDKs con versiones fijadas; no activa servicios de pago. El ZIP de GitHub no contiene dependencias instaladas: no se presenta como paquete offline autocontenido.

Selecciona territorio/fuente/periodo UTC, pulsa Aplicar, explora eventos y abre Investigación. El panel inferior permite cambiar altura con ratón/táctil o flechas de teclado; minimizar/cerrar conserva cámara. Exportación utiliza la selección completa (el cursor de reproducción solo cambia visualización). Perfiles comparten resultados; Gestión institucional es espacio no habilitado con acceso servidor rechazado.

La revisión 01 añade bases topográfica IGN, PNOA e híbrida, navegación municipal/sistemas documentales, filtro e histograma de profundidad y Research con mapa mínimo. El 3D muestra cartografía sobre elipsoide y eventos, **sin MDT ni batimetría reales validados en esta entrega**. Incluye importador local opcional de GeoTIFF auténtico documentado, aún pendiente de prueba con un MDT real. El Earth V2.1 privado conserva su terreno local separado. Capas manuales opcionales no certifican actividad ni instalaciones críticas. No hay logo oficial disponible para incorporar.

Consulta [recorrido geocientífico y pruebas actuales](docs/next/PRODUCT-REVIEW-01.md), [método y reproducción](docs/next/RESEARCH-METHOD.md), [revisión anterior](docs/next/REVIEW-01.md), [cartografía oficial](docs/next/OFFICIAL-CARTOGRAPHY.md), [MDT opcional](docs/next/TERRAIN-IMPORT.md), [entrega anterior](docs/next/REVIEW.md), [matriz funcional](FEATURE-MATRIX.md), [arquitectura](ARCHITECTURE.md), [fuentes](DATA-SOURCES.md) y [punto de reanudación](SESSION-HANDOFF.md). No fusionar ni desplegar sin aprobación expresa.


Para probar el salto funcional: selecciona Tenerife/Teide–Pico Viejo y pulsa **Cuaderno Tenerife · archivo USGS**. El históricoUSGS archivado funciona sin adquisición reciente; la cartografía externa sí necesita conexión. Ejecuta el caso2004 mbLg≥2, consulta fuentes/series/tasas/espacio, pregunta por cobertura y exporta el informe o ZIP de evidencias. Es un piloto con181 registros oficiales de procedencia verificada, no un catálogo regional completo ni una predicción. Para leer un resultado sin arrancar la aplicación, descarga docs/next/product01/example-evidence.zip, descomprímelo y abre report.html en tu navegador.


## Nuevo recorrido multinsular

Pulsa **Investigar Canarias · histórico IGN**. Compara islas y periodos, explora series/profundidades, consulta municipios oficiales en el área visible y pregunta por evidencias. Archivo IGN: 3.609 registros de 2023–2024, sin simulaciones. Funciona sin adquisición reciente; cartografía externa requiere red. Exporta JSON/CSV y reproduce con `python3 tools/reproduce_observatory.py run.json`. [Guía de revisión y límites](docs/next/OBSERVATORY-01.md).


## Canal de actualización continua 0.5

`python3 abrir.py` abre el observatorio continuo y arranca el recolector en el servidor local. IGN cada 10 min y USGS cada 15 min; sigue adquiriendo con el navegador cerrado mientras Python permanezca abierto. La primera ejecución necesita red: no incluye una base viva precargada ni datos simulados. Los archivos históricos anteriores son independientes.

Consulta fuentes y último éxito; elige periodo, territorio y filtros y revisa cobertura. Al arrancar solo hay diez días nominales IGN y treinta USGS: un año no se finge completo. Fija el periodo UTC para mantenerlo durante actualizaciones; JSON congela datos/método y se reproduce con `python3 tools/reproduce_continuous.py run.json`.

[Recorrido, arquitectura, frecuencia, operación y limitaciones](docs/next/CONTINUOUS-01.md). [Capturas reales](docs/next/continuous01/captures). Worker independiente opcional: `python3 -m risklab_next.continuous.worker`; no es necesario ejecutarlo aparte si se usa abrir.py. Diagnóstico, auditoría y copia privada: `tools/audit_continuous.py`. No copiar bases ni HTML crudo a GitHub. El ejemplo Render no despliega nada y necesita revisión/aprobación del disco y plan antes de usarlo.
