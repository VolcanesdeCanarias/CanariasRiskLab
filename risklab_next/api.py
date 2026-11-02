import csv
import hashlib
import io
import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .terrain import load_grid

from flask import Blueprint, abort, jsonify, request, send_from_directory, Response

ROOT = Path(__file__).resolve().parent.parent
ISLANDS = {
    'ES709': 'Tenerife', 'ES707': 'La Palma', 'ES703': 'El Hierro',
    'ES706': 'La Gomera', 'ES705': 'Gran Canaria', 'ES708': 'Lanzarote',
    'ES704': 'Fuerteventura',
}
TERRITORIES = list(ISLANDS.values()) + ['La Graciosa', 'Entorno marítimo']
SOURCES = {
    'IGN': {'url': 'https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias',
            'coverage': 'Catálogo regional móvil de aproximadamente diez días; no acredita completitud.', 'window_days': 10},
    'USGS': {'url': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson',
             'coverage': 'Feed global de 24 horas recortado a 26–31 N, 19–12 O. No sustituye al catálogo regional.', 'window_days': 1},
}


def utcnow():
    return datetime.now(timezone.utc)


def inside_ring(lon, lat, ring):
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > lat) != (b[1] > lat):
            if lon < (b[0] - a[0]) * (lat - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
    return inside


class Geography:
    def __init__(self):
        original = (ROOT / 'municipios_canarias.geojson').read_bytes()
        self.sha256 = hashlib.sha256(original).hexdigest()
        data = json.loads(original)
        self.parts, self.municipalities, self.outlines = [], [], []
        self.views = {}
        for f in data['features']:
            p, g = f['properties'], f['geometry']
            island = ISLANDS[p['gcd_isla']]
            municipality = {'id': p['geocode'], 'name': p['etiqueta'], 'island': island, 'bounds': None}
            self.municipalities.append(municipality)
            polygons = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            northern = [poly for poly in polygons if min(v[1] for v in poly[0]) > 29.2]
            # Largest northern component of Teguise is La Graciosa. Do not label
            # Alegranza or Montaña Clara as this inhabited island.
            graciosa = max(northern, key=lambda poly: (max(v[0] for v in poly[0])-min(v[0] for v in poly[0])) *
                           (max(v[1] for v in poly[0])-min(v[1] for v in poly[0])), default=None) if p['geocode']=='35024' else None
            for polygon in polygons:
                xs, ys = zip(*[(v[0], v[1]) for v in polygon[0]])
                # Component of Teguise north-west of Lanzarote. Explicit selection rule,
                # not a new administrative boundary or a nearest-island classifier.
                name = 'La Graciosa' if polygon is graciosa else island
                bounds = [min(xs), min(ys), max(xs), max(ys)]
                def union(a, b):
                    return b[:] if a is None else [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                municipality['bounds'] = union(municipality['bounds'], bounds)
                self.views[name] = union(self.views.get(name), bounds)
                self.parts.append((*bounds, polygon, p['geocode'], name))
                stride = max(1, math.ceil(len(polygon[0]) / 150))
                ring = polygon[0][::stride]
                self.outlines.append(ring + [ring[0]])

    def locate(self, lon, lat):
        for x0, y0, x1, y1, polygon, municipality, island in self.parts:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and inside_ring(lon, lat, polygon[0]):
                if not any(inside_ring(lon, lat, hole) for hole in polygon[1:]):
                    return island, municipality
        return 'Entorno marítimo', None


class SnapshotStore:
    """Immutable normalized responses, bounded in-process acquisition cache.

    The HTML/feed itself is NOT archived: raw response retention is a later task.
    SQLite is a local phase-1 adapter, not the target geospatial production store.
    """
    def __init__(self, adapters, failure, geography, database=None, ttl=60):
        self.adapters, self.failure, self.geography = adapters, failure, geography
        self.database = str(database or os.environ.get('RISKLAB_NEXT_DB', ROOT / '.risklab-next' / 'snapshots.sqlite'))
        if self.database != ':memory:':
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self.ttl, self.cache, self.locks = ttl, {}, {s: threading.Lock() for s in SOURCES}
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, body TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def read(self, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM snapshots WHERE id = ?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def acquire(self, source):
        with self.locks[source]:
            cached = self.cache.get(source)
            if cached and time.monotonic() - cached[0] < self.ttl:
                return cached[1]
            checked = utcnow().replace(microsecond=0).isoformat()
            try:
                raw = self.adapters[source]()
                events = []
                for e in raw:
                    island, municipality = self.geography.locate(e['lon'], e['lat'])
                    events.append({
                        'id': str(e['id']), 'source': source, 'time': e['datetime_iso'],
                        'lat': e['lat'], 'lon': e['lon'], 'depth_km': e['profundidad_km'],
                        'magnitude': e['magnitud'], 'magnitude_type': e.get('tipo_magnitud'),
                        'place': e.get('localizacion', ''), 'territory': island,
                        'municipality_id': municipality, 'uncertainty': None,
                        'depth_reference': 'Referencia del catálogo; no transformada a datum vertical geodésico.',
                    })
                events.sort(key=lambda e: (e['time'], e['id']))
                quality = {'state': 'available' if events else 'empty', 'count': len(events), 'checked_at': checked}
            except Exception as error:
                payload, _ = self.failure(error, source)
                events, quality = [], {**payload['data_status'], 'checked_at': checked,
                                       'code': payload['error_code'], 'message': payload['error']}
            snapshot = {'schema': 'risklab.observations/1', 'source': source, 'quality': quality,
                        'normalization': {'method': 'catalogue-normalization/1.1',
                                          'geography_sha256': self.geography.sha256,
                                          'geography_reference': 'Inherited CRS84 municipal polygons; unverified current validity.'},
                        'coverage': SOURCES[source], 'events': events,
                        'limitations': ['Catálogos independientes: no sumar ni deduplicar IGN y USGS sin reconciliación.',
                                        'Sin incertidumbres publicadas en este adaptador; ausencia no significa error cero.',
                                        'Magnitudes ausentes permanecen nulas; se excluyen al aplicar un umbral de magnitud.',
                                        'Asignación territorial por polígonos heredados, no por texto ni proximidad; límites pendientes de validar.']}
            body = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=False)
            snapshot['snapshot_id'] = hashlib.sha256(body.encode()).hexdigest()
            with self.connect() as db:
                db.execute('INSERT OR IGNORE INTO snapshots VALUES (?, ?)',
                           (snapshot['snapshot_id'], json.dumps(snapshot, ensure_ascii=False, allow_nan=False)))
            self.cache[source] = time.monotonic(), snapshot
            return snapshot


def analyze(snapshot, args, municipality_ids=None):
    """Half-open UTC windows; comparisons only when both windows fit acquisition coverage."""
    checked = datetime.fromisoformat(snapshot['quality']['checked_at'])
    try:
        until = datetime.fromisoformat(args.get('until', checked.isoformat()).replace('Z', '+00:00'))
        start = datetime.fromisoformat(args.get('from', (until - timedelta(days=1)).isoformat()).replace('Z', '+00:00'))
        if start.tzinfo is None or until.tzinfo is None or not start < until or until > checked:
            raise ValueError('Intervalo UTC inválido o posterior a la adquisición.')
        minimum = float(args.get('min_mag', '-10'))
        if not math.isfinite(minimum) or not -10 <= minimum <= 10:
            raise ValueError('Magnitud fuera de rango.')
        municipality = args.get('municipality_id', '')
        if municipality and (not municipality.isdigit() or len(municipality) != 5 or
                             (municipality_ids is not None and municipality not in municipality_ids)):
            raise ValueError('Municipio desconocido.')
        depth_min, depth_max = float(args.get('min_depth', '-10')), float(args.get('max_depth', '1000'))
        if not all(math.isfinite(v) for v in [depth_min, depth_max]) or not -10 <= depth_min <= depth_max <= 1000:
            raise ValueError('Intervalo de profundidad inválido.')
        territory = args.get('territory', 'Canarias')
        if territory not in ['Canarias'] + TERRITORIES:
            raise ValueError('Territorio desconocido.')
    except (ValueError, TypeError) as error:
        raise ValueError('Parámetros de consulta inválidos: ' + str(error)) from error
    eligible = [e for e in snapshot['events'] if (territory == 'Canarias' or e['territory'] == territory)
                and (not municipality or e.get('municipality_id') == municipality)
                and depth_min <= e['depth_km'] <= depth_max
                and ((e['magnitude'] is None and minimum == -10)
                     or (e['magnitude'] is not None and e['magnitude'] >= minimum))]
    def select(a, b):
        return [e for e in eligible if a <= datetime.fromisoformat(e['time'].replace('Z', '+00:00')) < b]
    events = select(start, until)
    duration = until - start
    coverage_start = checked - timedelta(days=SOURCES[snapshot['source']]['window_days'])
    covered = start >= coverage_start
    comparable = start - duration >= coverage_start
    state = snapshot['quality']['state']
    overlap = until > coverage_start
    valid = state != 'unavailable' and overlap
    def stats(values):
        return {'count': len(values), 'max_magnitude': max((e['magnitude'] for e in values if e['magnitude'] is not None), default=None),
                'missing_magnitude': sum(e['magnitude'] is None for e in values)}
    result = {'schema': 'risklab.descriptive/1', 'method': 'descriptive-counts/1.1',
              'snapshot_id': snapshot['snapshot_id'], 'quality': snapshot['quality'],
              'parameters': {'from': start.isoformat(), 'until': until.isoformat(), 'territory': territory, 'min_mag': minimum,
                             'municipality_id': municipality, 'min_depth': depth_min, 'max_depth': depth_max},
              'duration_hours': duration.total_seconds() / 3600,
              'state': 'unavailable' if state == 'unavailable' else 'no_coverage' if not overlap else 'partial_coverage' if not covered else 'filtered_empty' if not events and state != 'empty' else state,
              'statistics': stats(events) if valid else {'count': None, 'max_magnitude': None},
              'comparison': {'state': 'available' if valid and comparable else 'insufficient_coverage',
                             'previous_from': (start - duration).isoformat(), 'previous_until': start.isoformat(),
                             'duration_hours': duration.total_seconds() / 3600,
                             'statistics': stats(select(start - duration, start)) if valid and comparable else None},
              'events': events if valid else []}
    if state != 'unavailable' and not overlap:
        explanation = 'El periodo no solapa la cobertura nominal de esta adquisición. No se puede calcular un recuento histórico ni inferir ausencia de actividad.'
    elif not valid:
        explanation = 'Adquisición no disponible. No se puede inferir ausencia de actividad ni calcular un índice.'
    elif not events:
        explanation = 'No hay registros en esta selección. No demuestra ausencia de actividad ni modifica ningún nivel oficial.'
    else:
        explanation = f"La selección contiene {len(events)} registros de {snapshot['source']}. Es un recuento descriptivo, no una predicción ni una evaluación de peligrosidad."
    if not covered:
        explanation += ' El periodo solicitado excede la cobertura nominal; el recuento es parcial.'
    result['explanation'] = {'kind': 'deterministic_template', 'text': explanation, 'evidence': snapshot['snapshot_id'],
                             'review': 'No constituye interpretación científica validada ni comunicación oficial.'}
    return result


def create_blueprint(adapters, failure, database=None):
    blueprint = Blueprint('risklab_next', __name__)
    geography = Geography()
    store = SnapshotStore(adapters, failure, geography, database)
    blueprint.snapshot_store = store

    @blueprint.get('/next')
    @blueprint.get('/next/')
    def home():
        return send_from_directory(ROOT / 'next', 'index.html')

    @blueprint.get('/next/assets/<path:name>')
    def assets(name):
        if name not in {'app.mjs', 'style.css', 'earth.mjs', 'view-state.mjs', 'cartography.mjs', 'research.mjs'}:
            abort(404)
        return send_from_directory(ROOT / 'next', name)

    @blueprint.get('/next/vendor/<library>/<path:name>')
    def vendor(library, name):
        roots = {'leaflet': ROOT / 'node_modules/leaflet/dist', 'cesium': ROOT / 'node_modules/cesium/Build/Cesium'}
        if library not in roots or '..' in Path(name).parts or Path(name).suffix not in {'.js', '.css', '.png', '.jpg', '.json', '.wasm', '.svg', '.gif'}:
            abort(404)
        return send_from_directory(roots[library], name)

    @blueprint.get('/api/v1/catalog')
    def catalog():
        references = json.loads((ROOT / 'risklab_next/references.json').read_text())
        return jsonify({'territories': TERRITORIES, 'municipalities': geography.municipalities,
                        'sources': SOURCES, 'references': references,
                        'territory_views': geography.views,
                        'volcanic_catalogue': json.loads((ROOT / 'risklab_next/volcanic-systems.json').read_text()),
                        'cartography': json.loads((ROOT / 'risklab_next/cartography.json').read_text()),
                        'instrumentation': {'state': 'manual_unverified', 'operational_status': 'not_verified',
                                            'stations': [{k: v for k, v in item.items() if k != 'estado'} for item in json.loads((ROOT / 'ign_instrumentation.json').read_text())['stations']]},
                        'capabilities': {'observation': True, 'descriptive_analysis': True,
                                         'grounded_templates': True, 'predictive_ai': False,
                                         'institutional': False, 'gnss_series': False, 'insar': False},
                        'official_status': {'state': 'not_verified', 'message': 'No hay un comunicado oficial vigente verificado en esta integración.'}})

    @blueprint.get('/api/v1/terrain')
    def terrain():
        # Fixed local import path; never arbitrary file paths from HTTP parameters.
        return jsonify(load_grid(ROOT / '.risklab-next/terrain.json'))

    @blueprint.get('/api/v1/territory-outlines')
    def outlines():
        return jsonify({'rings': geography.outlines, 'purpose': 'display_only',
                        'warning': 'Contornos muestreados del GeoJSON heredado: no usar para cálculos ni límites oficiales.'})

    @blueprint.get('/api/v1/observations/<source>')
    def observations(source):
        if source not in SOURCES:
            abort(404)
        snapshot = store.acquire(source)
        return jsonify(snapshot), 503 if snapshot['quality']['state'] == 'unavailable' else 200

    @blueprint.get('/api/v1/analysis/<key>')
    def analysis(key):
        snapshot = store.read(key)
        if snapshot is None:
            abort(404)
        try:
            result = analyze(snapshot, request.args, {m['id'] for m in geography.municipalities})
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        if request.args.get('format') == 'csv':
            if result['state'] in {'unavailable', 'no_coverage'}:
                return jsonify({'error': 'No se exporta un fallo o ausencia de cobertura como catálogo vacío.'}), 503
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(['snapshot_id', 'source', 'id', 'time_utc', 'latitude', 'longitude', 'depth_km', 'magnitude', 'territory'])
            for e in result['events']:
                row = [key, e['source'], e['id'], e['time'], e['lat'], e['lon'], e['depth_km'], e['magnitude'], e['territory']]
                writer.writerow(["'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in row])
            return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=risklab-observations.csv'})
        return jsonify(result)

    @blueprint.get('/api/v1/institutional/<path:action>')
    def institutional(action):
        return jsonify({'error': 'Espacio no habilitado: requiere autenticación, permisos y revisión institucional.'}), 403

    @blueprint.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control'] = 'no-store'
        return response

    from .research import register_research
    register_research(blueprint, store, geography)
    return blueprint
