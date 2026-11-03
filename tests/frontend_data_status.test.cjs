const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const script = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');

// Execute the production functions against a small DOM/network harness, without external CDNs.
function productionFunction(name) {
  const start = script.search(new RegExp(`^    (?:async )?function ${name}\\(`, 'm'));
  assert.notEqual(start, -1, name);
  const tail = script.slice(start + 1);
  const next = tail.search(/^    (?:async )?function \w+\(/m);
  return next === -1 ? script.slice(start) : script.slice(start, start + 1 + next);
}

function harness() {
  const elements = new Map();
  const context = vm.createContext({
    console, Date, Promise, Array, encodeURIComponent,
    document: { getElementById(id) {
      if (!elements.has(id)) elements.set(id, { textContent: '', innerHTML: '', style: {} });
      return elements.get(id);
    } },
    selectedIsland: () => 'Todas', selectedMunicipality: () => 'Todos',
    canonicalMunicipalityName: s => s,
    ignDataState: 'available', loadSequence: 0,
    ignEvents: [{ id: 'previous' }], usgsEvents: [{ id: 'previous-usgs' }],
    risklabIndex: { value: 55 }, summary: { old: true },
    depthProfile: {}, compareData: {}, seriesData: {}, interpretation: {},
    regimeData: {}, migrationData: {}, anomalyData: {}, territorialData: {},
    municipalityStats: {}, municipalRanking: [], selectedMunicipalityData: {},
    municipalClusters: [], infraExpuestas: [], focusClusters: [], focusTemporalClusters: [],
    focusSummary: {}, officialStatus: [], instrumentationStations: [],
    redrawAll() {},
    fetch: async () => { throw new Error('Unexpected network call'); }
  });
  const names = ['hasIgnAnalysis', 'analysisUnavailable', 'fetchJson', 'clearIgnAnalysis', 'loadAll', 'updateStatus',
    'drawSummary', 'buildInterpretation', 'buildRegimeCard', 'buildMigrationCard', 'buildAnomalyCard',
    'buildFocusSummaryCard', 'buildFocusRankingCard', 'buildTerritorialCard',
    'buildSelectedMunicipalityCard', 'buildClusterCard', 'buildInfraExposureCard', 'buildTerritorialRanking'];
  vm.runInContext(names.map(productionFunction).join('\n'), context);
  return { context, elements };
}

const goodBundle = () => ({ ok: true, data_status: { state: 'available' },
  ign_eventos: [{ id: 'new', isla: 'Tenerife' }], risklab_index: { value: 25 } });

function sources(bundle = goodBundle(), usgs = { ok: true, data_status: { state: 'empty' }, eventos: [] }) {
  return async url => {
    if (url.startsWith('/api/risklab-bundle')) {
      if (bundle instanceof Error) throw bundle;
      return bundle;
    }
    if (url === '/api/usgs-canarias') {
      if (usgs instanceof Error) throw usgs;
      return usgs;
    }
    if (url === '/api/instrumentation') return { stations: [{ nombre: 'station' }] };
    if (url === '/api/official-volcanic-status') return { official_status: [{ isla: 'Tenerife' }] };
    throw new Error(url);
  };
}

test('inline JavaScript parses and referenced DOM IDs exist', () => {
  new vm.Script(script);
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  for (const [, id] of script.matchAll(/getElementById\("([^"]+)"\)/g)) assert.ok(ids.includes(id), id);
});

test('HTTP errors and ok:false cannot be read as successful data', async () => {
  const { context } = harness();
  for (const res of [
    { ok: false, status: 502, json: async () => ({ ok: false, error: 'IGN: error HTTP 403.' }) },
    { ok: true, status: 200, json: async () => ({ ok: false, error: 'Invalid source' }) }
  ]) {
    context.fetch = async () => res;
    await assert.rejects(context.fetchJson('/api/ign-canarias'));
  }
});

test('IGN failure clears old analysis but preserves independent sources', async () => {
  const { context, elements } = harness();
  context.fetchJson = sources(new Error('IGN: error HTTP 403.'), {
    ok: true, data_status: { state: 'available' }, eventos: [{ id: 'usgs', isla: 'Tenerife' }]
  });
  await context.loadAll();
  assert.equal(context.ignDataState, 'unavailable');
  assert.equal(context.ignEvents.length, 0);
  assert.equal(context.risklabIndex, null);
  assert.equal(context.focusSummary, null);
  assert.equal(context.usgsEvents.length, 1);
  assert.equal(context.instrumentationStations.length, 1);
  assert.equal(context.officialStatus.length, 1);
  assert.match(elements.get('ign-data-status').textContent, /403/);
  assert.match(elements.get('ign-data-status').textContent, /no indica ausencia/);
});

test('all analytical cards refuse to interpret unavailable data', () => {
  const { context, elements } = harness();
  context.ignDataState = 'unavailable';
  const cards = { drawSummary: 'summary-content', buildInterpretation: 'interpretContent',
    buildRegimeCard: 'regimeContent', buildMigrationCard: 'migrationContent', buildAnomalyCard: 'anomalyContent',
    buildFocusSummaryCard: 'focusSummaryContent', buildFocusRankingCard: 'focusRankingContent',
    buildTerritorialCard: 'territorialContent', buildSelectedMunicipalityCard: 'selectedMunicipalityContent',
    buildClusterCard: 'clusterContent', buildInfraExposureCard: 'infraExposureContent',
    buildTerritorialRanking: 'territorialRankingContent' };
  for (const [name, id] of Object.entries(cards)) {
    context[name]();
    assert.match(elements.get(id).textContent, /Análisis no disponible/, name);
    assert.match(elements.get(id).textContent, /no indica ausencia/, name);
  }
  context.updateStatus();
  assert.equal(elements.get('status-title').textContent, 'Índice RiskLab: no disponible');
});

test('validated empty catalogue is explicitly distinguished from unavailable data', async () => {
  const { context, elements } = harness();
  context.fetchJson = sources({ ok: true, data_status: { state: 'empty' }, ign_eventos: [], risklab_index: { value: 9 } });
  await context.loadAll();
  assert.equal(context.ignDataState, 'empty');
  assert.equal(context.risklabIndex, null);
  assert.match(elements.get('ign-data-status').textContent, /adquisición validada.*sin eventos/);
  assert.match(elements.get('usgs-data-status').textContent, /adquisición correcta, sin eventos/);
  context.updateStatus();
  context.buildInterpretation();
  assert.equal(elements.get('status-title').textContent, 'Índice RiskLab: sin eventos registrados');
  assert.match(elements.get('interpretContent').textContent, /no se evalúan sin eventos/);
});

test('USGS failure is visible while IGN remains usable', async () => {
  const { context, elements } = harness();
  context.fetchJson = sources(goodBundle(), new Error('USGS: tiempo de espera agotado.'));
  await context.loadAll();
  assert.equal(context.ignDataState, 'available');
  assert.equal(context.ignEvents.length, 1);
  assert.equal(context.usgsEvents.length, 0);
  assert.match(elements.get('usgs-data-status').textContent, /USGS no disponible/);
  assert.match(elements.get('usgs-data-status').textContent, /No se puede confirmar la ausencia/);
});

test('successful HTTP response with missing acquisition status is rejected', async () => {
  const { context } = harness();
  context.fetchJson = sources({ ok: true, ign_eventos: [] });
  await context.loadAll();
  assert.equal(context.ignDataState, 'unavailable');
  assert.equal(context.risklabIndex, null);
});

test('a later successful acquisition recovers from an error', async () => {
  const { context } = harness();
  context.fetchJson = sources(new Error('Offline'));
  await context.loadAll();
  context.fetchJson = sources();
  await context.loadAll();
  assert.equal(context.ignDataState, 'available');
  assert.equal(context.ignEvents[0].id, 'new');
});

test('out-of-order requests do not restore old data or overwrite an error', async () => {
  const { context } = harness();
  let resolveOld;
  const normalSources = sources();
  context.fetchJson = url => url.startsWith('/api/risklab-bundle')
    ? new Promise(resolve => { resolveOld = resolve; }) : normalSources(url);
  const oldRequest = context.loadAll();
  assert.equal(context.risklabIndex, null);
  context.fetchJson = sources(new Error('Latest failed'));
  await context.loadAll();
  resolveOld(goodBundle());
  await oldRequest;
  assert.equal(context.ignDataState, 'unavailable');
  assert.equal(context.risklabIndex, null);
});
