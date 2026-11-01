# Revisión de seguridad previa a fusión del PR #1

Fecha: 1 de noviembre de 2026. Rama: `fix/p0-security-data-reliability`.
PR revisado inicialmente: `98e81da3557a4d5363d4f4f4096d4b160e9770eb`.
No se modifica `main`, no se fusiona y no se despliega en Render.

## Hallazgos corregidos

1. **Catálogo vacío e índice 9.** La fórmula original se mantiene, pero la API
   ya no la publica como medición cuando no existen eventos en el filtro. El
   índice, anomalía, régimen, migración, baseline y lectura territorial quedan
   sin evaluar. La interfaz distingue la fuente válida vacía del error de
   adquisición y también evita mostrar artefactos numéricos de respuestas de
   clientes anteriores. Se cubre tanto un catálogo global vacío como un
   municipio sin eventos dentro de un catálogo global con eventos.
2. **PEVOLCA manual.** La API declara explícitamente que no es una fuente en
   directo ni una verificación vigente. Fuentes, tarjetas, popups y leyenda
   indican referencia manual, fecha declarada 2026-04-06 y vigencia no comprobada.
   El contorno gris discontinuo evita colorear el territorio como si la
   transcripción antigua fuera un estado oficial actual. No se inventa una
   nueva verificación ni se modifican los niveles almacenados.
3. **Pestañas y capas durante filtros.** La recarga P0 aplicaba otra vez el modo
   activo y perdía la pestaña elegida o restablecía interruptores. Ahora el modo
   se aplica al iniciar o al pulsar su botón, no durante cada redibujado.
4. **Avisos en móvil.** Las posiciones fijas de los paneles no contemplaban el
   crecimiento de mensajes. Sus alturas reales determinan ahora la separación
   en pantallas estrechas, evitando que las fuentes oculten los filtros.
5. **Capas independientes durante carga.** Se retiran datos anteriores de
   instrumentación y PEVOLCA al iniciar otra carga para no mostrarlos como
   correspondientes a una selección todavía no resuelta.

## Pruebas

- Backend: 28 pruebas unitarias, incluida comparación AST de las funciones
  científicas con el commit auditado. Rutas privadas 404 y activos públicos 200.
- JavaScript: 9 pruebas unitarias de estado, errores, recuperación y concurrencia.
- Navegador: 10 casos reproducibles en Chromium, más un caso opcional en vivo.
  Se prueban Leaflet 1.9.4, Leaflet.heat 0.2.0 y Chart.js 4.5.1, los dos GeoJSON
  completos y las rutas Flask del proyecto. No se sustituye el DOM por un arnés.

La suite de navegador recorre las 12 capas, los tres modos, las siete pestañas,
los tres gráficos renderizados, el cierre del panel, isla y municipio,
preservación de controles, ausencia de eventos, fallos IGN 403 y USGS 504,
recuperación posterior, dos casos de respuestas fuera de orden y vista móvil
de 390 × 844. En los casos de carrera se retiene una respuesta y se libera
después de una selección más reciente, sin esperas temporales arbitrarias.
También se exige que no existan excepciones JavaScript sin capturar.

Las fuentes sintéticas solo se utilizan en `tests/browser/serve.py` y en
intercepciones Playwright. El servidor de producción sigue siendo `server:app`
y no registra las rutas `__test__`. La suite reproducible usa bibliotecas reales
instaladas con versiones fijadas; no descarga teselas. Por ello sus capturas
`fixture-*` tienen fondo cartográfico gris y no representan una observación real.

Resultado local: **28 pruebas Python, 9 JavaScript y 11 de navegador correctas**,
sin fallos. En CI se ejecutan los diez casos de navegador reproducibles; el caso
en vivo se omite expresamente.

## Prueba visual y consultas reales

Se abrió Chromium 154.0.8037.57 en modo headless, con viewport 1440 × 1000, contra
el servidor Flask local de producción. Se cargaron las bibliotecas CDN y teselas
OpenStreetMap auténticas, con verificación TLS habilitada y la CA del entorno.
Se inspeccionaron las capturas del mapa, gráfico, catálogo vacío, PEVOLCA manual
y móvil con errores. No es una prueba del despliegue Render.

La consulta real registró 19 eventos IGN antes de filtrar; Tenerife mostró 10.
USGS devolvió cero eventos regionales con adquisición válida. Se verificaron
teselas cargadas, filtro por Tenerife y gráfico de serie visible, sin excepciones
JavaScript. El 403 histórico no se reprodujo en vivo; se cubre en pruebas.

Las capturas de CI se conservan como artefacto `browser-review-fixtures`. La
captura local `live-desktop.png` corresponde al caso en vivo; no se usan datos
reales como fixtures fijos de producción ni se versionan dependencias instaladas.

## Reproducción

Desde la raíz, con Python 3.12 y Node 24:

```sh
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
node tests/frontend_data_status.test.cjs
npm ci --prefix tests/browser
npx --prefix tests/browser playwright install --with-deps chromium
node tests/browser/review.cjs
git diff --check
```

El caso en vivo se habilita con `LIVE_BASE_URL` apuntando a un servidor local de
producción ya iniciado. `PYTHON` permite seleccionar su intérprete de pruebas y
`CHROMIUM_PATH` un navegador del sistema. En CI el caso en vivo se omite para que
las regresiones no dependan de la disponibilidad de terceros.

## Límites para aprobación

Los cambios revisados corrigen los bloqueos identificados para la publicación
P0. Permanecen los límites metodológicos y geográficos de la auditoría: etiquetas
30d con fuente de diez días, baseline, municipios, exposición y validación de
clusters. Tampoco se ha actualizado PEVOLCA con una fuente oficial nueva, ni se
ha ampliado esta intervención a la sanitización general de popups o a fijar las
dependencias CDN de producción. No se afirma que esos pendientes estén resueltos.

Los clientes externos de la API deben admitir `risklab_index: null` y consultar
`analysis_status` cuando un filtro no contiene eventos; no deben convertir ese
`null` en cero ni en actividad baja.

La aprobación solicitada es del contenido del PR; la fusión y el despliegue
siguen pendientes de autorización expresa.
