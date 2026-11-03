// Real Chromium/Leaflet/Chart.js regression tests. Fixtures only exist in tests.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium, request } = require('playwright');

const root = path.resolve(__dirname, '../..');
const base = 'http://127.0.0.1:' + (process.env.TEST_PORT || '8765');
const artifacts = process.env.BROWSER_ARTIFACTS || path.join(root, 'work/browser-review');
let server, browser, localRequest, page, context, scenario, pageErrors;
let serverLog = '';

async function screenshot(name) {
  await page.evaluate(() => {
    for (const chart of [seriesChart, depthChart, compareChart]) {
      if (chart) { chart.stop(); chart.update('none'); }
    }
  });
  await page.screenshot({ path: path.join(artifacts, name + '.png'), fullPage: true, animations: 'disabled' });
}

async function loaded() {
  await page.waitForFunction(() => ignDataState !== 'loading');
}

async function reloadSources() {
  await page.evaluate(() => loadAll());
  await loaded();
}

test.before(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  server = spawn(process.env.PYTHON || 'python', ['-B', 'tests/browser/serve.py'], { cwd: root });
  server.stdout.on('data', data => { serverLog += data; });
  server.stderr.on('data', data => { serverLog += data; });
  localRequest = await request.newContext();
  let ready = false;
  for (let i = 0; i < 50; i++) {
    try {
      const r = await localRequest.get(base + '/__test__/ready', { timeout: 500 });
      ready = r.ok();
      if (ready) break;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(ready, serverLog);
  browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
    args: ['--no-sandbox'] });
  console.log('Browser:', browser.version());
});

test.beforeEach(async () => {
  if (!browser) return;
  scenario = { ign: 'ok', usgs: 'ok', hold: null };
  pageErrors = [];
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const assets = {
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js': require.resolve('leaflet/dist/leaflet.js'),
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css': require.resolve('leaflet/dist/leaflet.css'),
    'https://unpkg.com/leaflet.heat/dist/leaflet-heat.js': require.resolve('leaflet.heat/dist/leaflet-heat.js'),
    'https://cdn.jsdelivr.net/npm/chart.js': path.join(path.dirname(require.resolve('chart.js')), 'chart.umd.js')
  };
  // Offline suite uses the real libraries, local GeoJSON and real Flask API calculations.
  // Only external base tiles are absent. The optional live case checks genuine OSM tiles.
  await context.route('https://**/*', async route => {
    const file = assets[route.request().url()];
    if (file) await route.fulfill({ path: file, contentType: file.endsWith('.css') ? 'text/css' : 'application/javascript' });
    else await route.abort();
  });
  await context.route('**/api/risklab-bundle?*', async route => {
    if (scenario.ign === 'error') {
      await route.fulfill({ status: 502, json: { ok: false, error: 'IGN: error HTTP 403.' } });
      return;
    }
    const url = new URL(route.request().url());
    const response = await route.fetch(scenario.ign === 'empty'
      ? { url: base + '/__test__/empty-bundle' + url.search } : {});
    const hold = scenario.hold;
    const held = hold && hold.island === url.searchParams.get('island') &&
      (!hold.municipality || hold.municipality === url.searchParams.get('municipio'));
    if (held) {
      hold.entered();
      await hold.release;
    }
    await route.fulfill({ response });
    if (held) hold.finished();
  });
  await context.route('**/api/usgs-canarias', async route => {
    if (scenario.usgs === 'error') await route.fulfill({ status: 504, json: { ok: false, error: 'USGS: tiempo de espera agotado.' } });
    else await route.continue();
  });
  page = await context.newPage();
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto(base, { waitUntil: 'networkidle' });
  await loaded();
});

test.afterEach(async t => {
  if (page && !page.isClosed() && !t.passed) await screenshot('failure-' + t.name.replace(/[^a-z0-9]/gi, '-'));
  if (context) await context.close();
  assert.deepEqual(pageErrors, [], 'No uncaught browser errors');
});

test.after(async () => {
  if (browser) await browser.close();
  if (localRequest) await localRequest.dispose();
  if (server) server.kill('SIGTERM');
});

test('map, all layer controls, charts, modes and panels remain functional', async () => {
  assert.equal(await page.evaluate(() => L.version), '1.9.4');
  assert.ok(await page.evaluate(() => ignLayer.getLayers().length > 0 && focusLayer.getLayers().length > 0));
  await page.click('#mode-analysis');
  for (const [id, layer] of [
    ['toggle-official-status', 'officialStatusLayer'], ['toggle-exclusion', 'exclusionLayer'],
    ['toggle-volcanoes', 'volcanoLayer'], ['toggle-volcanic-zones', 'volcanicZonesLayer'],
    ['toggle-municipalities', 'municipalitiesLayer'], ['toggle-clusters', 'clusterLayer'],
    ['toggle-focuses', 'focusLayer'], ['toggle-ign', 'ignLayer'], ['toggle-usgs', 'usgsLayer'],
    ['toggle-infra', 'infraLayer'], ['toggle-instrumentation', 'instrumentationLayer'], ['toggle-heatmap', 'heatLayer']
  ]) {
    await page.check('#' + id);
    assert.ok(await page.evaluate(name => map.hasLayer(eval(name)), layer), id + ' on');
    await page.uncheck('#' + id);
    assert.equal(await page.evaluate(name => map.hasLayer(eval(name)), layer), false, id + ' off');
  }
  for (const tab of ['series', 'depth', 'compare', 'interpret', 'territory', 'legend', 'summary']) {
    await page.click(`[data-tab="tab-${tab}"]`);
    assert.ok(await page.locator('#tab-' + tab).isVisible());
    if (['series', 'depth', 'compare'].includes(tab)) {
      await page.waitForFunction(name => {
        const chart = Chart.getChart(document.getElementById(name + 'Chart'));
        return chart && chart.width > 0 && chart.height > 0;
      }, tab);
      if (tab === 'series') await screenshot('fixture-series-rendered');
    }
  }
  assert.ok(await page.evaluate(() => [seriesChart, depthChart, compareChart].every(c => c !== null)));
  await page.click('#bottom-toggle');
  assert.ok(await page.locator('#bottom-panel').evaluate(el => el.classList.contains('collapsed')));
  await page.click('#bottom-toggle');
  await page.click('#mode-territory');
  assert.ok(await page.locator('#tab-territory').isVisible());
  await page.click('#mode-citizens');
  assert.ok(await page.locator('#tab-summary').isVisible());
  await screenshot('fixture-desktop-functional');
});

test('island and municipality filters preserve selected tab and layer switches', async () => {
  await page.click('#mode-analysis');
  await page.check('#toggle-usgs');
  await page.uncheck('#toggle-focuses');
  await page.click('[data-tab="tab-series"]');
  await page.selectOption('#island-filter', 'Tenerife');
  await loaded();
  await page.selectOption('#municipality-filter', 'Icod de los Vinos');
  await loaded();
  assert.ok(await page.locator('#tab-series').isVisible());
  assert.ok(await page.locator('#toggle-usgs').isChecked());
  assert.equal(await page.locator('#toggle-focuses').isChecked(), false);
  assert.ok(await page.evaluate(() => ignEvents.length === 4 && ignEvents.every(e => e.municipio === 'Icod de los Vinos')));
  assert.ok(await page.evaluate(() => selectedMunicipalityLayer !== null && seriesChart.data.labels.length > 0));
  await page.click('[data-tab="tab-interpret"]');
  assert.match(await page.locator('#selectedMunicipalityContent').textContent(), /Icod de los Vinos/);
});

test('validated empty IGN never displays experimental index 9 or reassuring interpretation', async () => {
  scenario.ign = 'empty';
  await reloadSources();
  assert.equal(await page.evaluate(() => ignDataState), 'empty');
  assert.equal(await page.evaluate(() => risklabIndex), null);
  assert.equal(await page.locator('#status-title').textContent(), 'Índice RiskLab: sin eventos registrados');
  assert.doesNotMatch(await page.locator('#status-title').textContent(), /valor|9/);
  await page.click('[data-tab="tab-interpret"]');
  assert.match(await page.locator('#interpretContent').textContent(), /no se evalúan sin eventos/);
  assert.doesNotMatch(await page.locator('#interpretContent').textContent(), /próximos al comportamiento esperado|sin anomalías/i);
  assert.ok(await page.evaluate(() => ignLayer.getLayers().length === 0 && seriesChart === null));
  await screenshot('fixture-empty-ign');
  scenario.ign = 'ok';
  await reloadSources();
  assert.ok(await page.evaluate(() => risklabIndex !== null && ignEvents.length > 0));
  assert.ok(await page.locator('#tab-interpret').isVisible());
});

test('empty municipality is distinct from failure even when other islands have events', async () => {
  await page.selectOption('#island-filter', 'Tenerife');
  await loaded();
  await page.selectOption('#municipality-filter', 'Arona');
  await loaded();
  assert.equal(await page.evaluate(() => ignDataState), 'available');
  assert.equal(await page.evaluate(() => risklabIndex), null);
  assert.match(await page.locator('#status-title').textContent(), /sin eventos registrados/);
  assert.match(await page.locator('#ign-data-status').textContent(), /adquisición validada/);
  await page.check('#toggle-municipalities');
  await page.evaluate(() => { municipalitiesLayer.getLayers()[0].getLayers()[0].openPopup(); });
  assert.match(await page.locator('.leaflet-popup-content').textContent(), /Sin eventos IGN registrados/);
});

test('manual PEVOLCA dates cannot be mistaken for current official verification', async () => {
  assert.match(await page.locator('#official-data-status').textContent(), /2026-04-06.*no es una actualización oficial vigente/);
  await page.click('#mode-territory');
  const text = await page.locator('#officialStatusContent').textContent();
  assert.match(text, /referencia manual/);
  assert.match(text, /Vigencia no comprobada/);
  assert.doesNotMatch(text, /verificado 2026/);
  assert.ok(await page.evaluate(() => officialStatusLayer.getLayers()[0].getLayers().every(l => l.options.dashArray === '6 6' && l.options.color === '#64748b')));
  await page.evaluate(() => { officialStatusLayer.getLayers()[0].getLayers()[0].openPopup(); });
  assert.match(await page.locator('.leaflet-popup-content').textContent(), /Vigencia no comprobada/);
  await screenshot('fixture-manual-pevolca');
});

test('IGN error keeps independent layers, map and filters usable and recovers', async () => {
  scenario.ign = 'error';
  await page.selectOption('#island-filter', 'Tenerife');
  await loaded();
  assert.match(await page.locator('#ign-data-status').textContent(), /403.*no indica ausencia/);
  assert.equal(await page.evaluate(() => risklabIndex), null);
  await page.click('#mode-territory');
  assert.match(await page.locator('#territorialContent').textContent(), /Análisis no disponible/);
  assert.ok(await page.evaluate(() => usgsEvents.length === 1 && instrumentationStations.length > 0 && officialStatus.length > 0));
  await page.check('#toggle-usgs');
  assert.ok(await page.evaluate(() => map.hasLayer(usgsLayer) && usgsLayer.getLayers().length === 1));
  await page.evaluate(() => { infraLayer.getLayers()[0].openPopup(); });
  assert.match(await page.locator('.leaflet-popup-content').textContent(), /Exposición no evaluada/);
  await screenshot('fixture-ign-error');
  scenario.ign = 'ok';
  await page.selectOption('#municipality-filter', 'Icod de los Vinos');
  await loaded();
  assert.ok(await page.evaluate(() => risklabIndex !== null && ignEvents.length === 4));
  assert.ok(await page.locator('#tab-territory').isVisible());
});

test('USGS failure and later recovery leave IGN and charts functional', async () => {
  scenario.usgs = 'error';
  await reloadSources();
  assert.match(await page.locator('#usgs-data-status').textContent(), /USGS no disponible/);
  assert.ok(await page.evaluate(() => ignEvents.length > 0 && risklabIndex !== null && seriesChart !== null));
  assert.equal(await page.evaluate(() => usgsEvents.length), 0);
  scenario.usgs = 'ok';
  await reloadSources();
  assert.match(await page.locator('#usgs-data-status').textContent(), /adquisición correcta/);
  assert.equal(await page.evaluate(() => usgsEvents.length), 1);
});

test('rapid island/municipality changes discard delayed success after latest failure', async () => {
  let release, entered, finished;
  const enteredPromise = new Promise(resolve => { entered = resolve; });
  const finishedPromise = new Promise(resolve => { finished = resolve; });
  scenario.hold = { island: 'Tenerife', entered, finished, release: new Promise(resolve => { release = resolve; }) };
  const delayedResponse = page.waitForResponse(r => r.url().includes('/api/risklab-bundle?island=Tenerife'));
  await page.click('[data-tab="tab-depth"]');
  await page.selectOption('#island-filter', 'Tenerife');
  await enteredPromise;
  scenario.ign = 'error';
  await page.selectOption('#island-filter', 'La Palma');
  await loaded();
  release();
  await finishedPromise;
  await (await delayedResponse).finished();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await page.evaluate(() => ignDataState), 'unavailable');
  assert.equal(await page.locator('#island-filter').inputValue(), 'La Palma');
  assert.equal(await page.evaluate(() => ignEvents.length), 0);
  assert.ok(await page.locator('#tab-depth').isVisible());
  scenario.hold = null;
  scenario.ign = 'ok';
  await page.selectOption('#municipality-filter', 'El Paso');
  await loaded();
  assert.ok(await page.evaluate(() => ignEvents.length === 4 && ignEvents.every(e => e.isla === 'La Palma' && e.municipio === 'El Paso')));
});

test('rapid municipality changes cannot replace a newer empty filter with old events', async () => {
  await page.selectOption('#island-filter', 'Tenerife');
  await loaded();
  let release, entered, finished;
  const enteredPromise = new Promise(resolve => { entered = resolve; });
  const finishedPromise = new Promise(resolve => { finished = resolve; });
  scenario.hold = { island: 'Tenerife', municipality: 'Icod de los Vinos', entered, finished,
    release: new Promise(resolve => { release = resolve; }) };
  const delayedResponse = page.waitForResponse(r => r.url().includes('/api/risklab-bundle?') &&
    new URL(r.url()).searchParams.get('municipio') === 'Icod de los Vinos');
  await page.selectOption('#municipality-filter', 'Icod de los Vinos');
  await enteredPromise;
  await page.selectOption('#municipality-filter', 'Arona');
  await loaded();
  release();
  await finishedPromise;
  await (await delayedResponse).finished();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await page.locator('#municipality-filter').inputValue(), 'Arona');
  assert.equal(await page.evaluate(() => ignEvents.length), 0);
  assert.equal(await page.evaluate(() => risklabIndex), null);
  assert.match(await page.locator('#status-title').textContent(), /sin eventos registrados/);
});

test('narrow-screen source warnings do not cover filters or panel tabs', async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  scenario.ign = 'error'; scenario.usgs = 'error';
  await reloadSources();
  await page.waitForFunction(() => {
    const s = document.getElementById('sources-panel').getBoundingClientRect();
    const c = document.getElementById('topright-panel').getBoundingClientRect();
    const b = document.getElementById('bottom-panel').getBoundingClientRect();
    return c.top >= s.bottom + 8 && b.top >= c.bottom + 8;
  });
  await page.selectOption('#island-filter', 'La Palma');
  await loaded();
  await page.click('[data-tab="tab-territory"]');
  assert.ok(await page.locator('#tab-territory').isVisible());
  assert.ok(await page.locator('#official-data-status').isVisible());
  await screenshot('fixture-mobile-errors');
});

test('live source smoke with real CDN assets and OpenStreetMap tiles', { skip: !process.env.LIVE_BASE_URL }, async () => {
  const upstream = await request.newContext(process.env.HTTPS_PROXY ? { proxy: { server: process.env.HTTPS_PROXY } } : {});
  const live = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  try {
    // APIRequestContext trusts NODE_EXTRA_CA_CERTS. TLS verification remains enabled.
    // Forward actual bytes to Chromium, whose OS trust store lacks the session CA.
    await live.route('https://**/*', async route => route.fulfill({ response: await upstream.get(route.request().url()) }));
    const p = await live.newPage();
    const errors = [];
    p.on('pageerror', e => errors.push(e.message));
    await p.goto(process.env.LIVE_BASE_URL, { waitUntil: 'networkidle' });
    await p.waitForFunction(() => ignDataState !== 'loading');
    assert.equal(await p.evaluate(() => ignDataState), 'available');
    assert.ok(await p.evaluate(() => ignEvents.length > 0 && document.querySelectorAll('.leaflet-tile-loaded').length > 0));
    await p.selectOption('#island-filter', 'Tenerife');
    await p.waitForFunction(() => ignDataState !== 'loading');
    assert.ok(await p.evaluate(() => ignEvents.every(e => e.isla === 'Tenerife')));
    await p.click('[data-tab="tab-series"]');
    assert.ok(await p.locator('#tab-series').isVisible());
    await p.waitForFunction(() => seriesChart.width > 0 && seriesChart.height > 0);
    await p.evaluate(() => { seriesChart.stop(); seriesChart.update('none'); });
    await p.screenshot({ path: path.join(artifacts, 'live-desktop.png'), fullPage: true, animations: 'disabled' });
    console.log('Live source snapshot:', await p.evaluate(() => ({ ign: ignEvents.length, usgs: usgsEvents.length,
      loadedTiles: document.querySelectorAll('.leaflet-tile-loaded').length, status: document.getElementById('ign-data-status').textContent })));
    assert.deepEqual(errors, []);
  } finally { await live.close(); await upstream.dispose(); }
});
