"""Contract and integrity tests; invented responses are confined to tests."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from flask import Flask
import server
from risklab_next.api import create_blueprint, Geography, analyze
from test_p0 import response, usgs_feature, NOW


class NextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = Geography()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.events = [{'id': 'fixture-only', 'datetime_iso': (self.now-timedelta(hours=2)).isoformat(),
                        'lat': 28.2724, 'lon': -16.6425, 'profundidad_km': 12, 'magnitud': -.1,
                        'tipo_magnitud': 'mbLg', 'localizacion': '=untrusted'}]
        self.adapters = {'IGN': lambda: self.events, 'USGS': lambda: []}
        self.app = Flask(__name__)
        with patch('risklab_next.api.Geography', return_value=self.geo):
            self.bp = create_blueprint(self.adapters, server.acquisition_failure, Path(self.temp.name)/'snapshots.sqlite')
        self.app.register_blueprint(self.bp)
        self.client = self.app.test_client()

    def snapshot(self):
        return self.client.get('/api/v1/observations/IGN').json

    def test_all_islands_and_88_municipalities_without_bad_hardcoded_list(self):
        r=self.client.get('/api/v1/catalog').json
        self.assertEqual(len(r['territories']),9)
        self.assertIn('La Graciosa',r['territories'])
        self.assertEqual(len(r['municipalities']),88)
        self.assertIn('San Miguel de Abona',[m['name'] for m in r['municipalities']])
        self.assertFalse(r['capabilities']['predictive_ai'])
        self.assertEqual(r['official_status']['state'],'not_verified')

    def test_polygon_assignment_and_marine_not_nearest_island(self):
        self.assertEqual(self.geo.locate(-16.6425,28.2724)[0],'Tenerife')
        self.assertEqual(self.geo.locate(-13.51,29.25)[0],'La Graciosa')
        self.assertEqual(self.geo.locate(-17,28.2),('Entorno marítimo',None))

    def test_snapshot_content_hash_and_reproducibility(self):
        s=self.snapshot(); key=s.pop('snapshot_id')
        self.assertEqual(key,hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest())
        a=self.client.get('/api/v1/analysis/'+key).json
        self.assertEqual(a['statistics']['count'],1)
        self.assertEqual(a['statistics']['max_magnitude'],-.1)
        self.events.clear()
        b=self.client.get('/api/v1/analysis/'+key).json
        self.assertEqual(a,b)

    def test_cached_acquisition_does_not_refetch_within_ttl(self):
        a=self.snapshot();self.events.clear();b=self.snapshot()
        self.assertEqual(a,b)

    def test_empty_is_distinct_from_failure_and_filtered_empty(self):
        self.events.clear();s=self.snapshot()
        self.assertEqual(s['quality']['state'],'empty')
        self.assertEqual(self.client.get('/api/v1/analysis/'+s['snapshot_id']).json['statistics']['count'],0)
        self.bp.snapshot_store.cache.clear()
        def fail():raise server.DataAcquisitionError('IGN','http_error','IGN no disponible',403)
        self.adapters['IGN']=fail
        r=self.client.get('/api/v1/observations/IGN');self.assertEqual(r.status_code,503)
        key=r.json['snapshot_id'];r=self.client.get('/api/v1/analysis/'+key).json
        self.assertIsNone(r['statistics']['count']);self.assertIn('no disponible',r['explanation']['text'])
        self.assertEqual(self.client.get('/api/v1/analysis/'+key+'?format=csv').status_code,503)
        self.bp.snapshot_store.cache.clear();self.adapters['IGN']=lambda:[{'id':'recovery','datetime_iso':(self.now-timedelta(hours=2)).isoformat(),'lat':28.2724,'lon':-16.6425,'profundidad_km':12,'magnitud':2}]
        s=self.snapshot();r=self.client.get('/api/v1/analysis/'+s['snapshot_id']+'?min_mag=4').json
        self.assertEqual(r['state'],'filtered_empty');self.assertEqual(r['statistics']['count'],0)

    def test_query_validation_and_institutional_server_denial(self):
        key=self.snapshot()['snapshot_id']
        for query in ['min_mag=nan','territory=unknown','from=2026-01-01','until=2099-01-01T00:00:00Z','min_mag=12']:
            self.assertEqual(self.client.get('/api/v1/analysis/'+key+'?'+query).status_code,400)
        self.assertEqual(self.client.get('/api/v1/institutional/reports').status_code,403)
        self.assertEqual(self.client.get('/api/v1/analysis/missing').status_code,404)

    def test_equal_duration_comparison_and_coverage_gate(self):
        s=self.snapshot();r=analyze(s,{})
        self.assertEqual(r['duration_hours'],r['comparison']['duration_hours'])
        self.assertEqual(r['comparison']['previous_until'],r['parameters']['from'])
        self.assertEqual(r['comparison']['state'],'available')
        r=analyze(s,{'from':(self.now-timedelta(days=6)).isoformat()})
        self.assertEqual(r['comparison']['state'],'insufficient_coverage')
        r=analyze(s,{'from':(self.now-timedelta(days=20)).isoformat()})
        self.assertEqual(r['state'],'partial_coverage')

    def test_half_open_utc_interval_and_negative_magnitude(self):
        s=self.snapshot();end=self.events[0]['datetime_iso']
        r=analyze(s,{'until':end,'from':(self.now-timedelta(days=1)).isoformat()})
        self.assertEqual(r['statistics']['count'],0)
        r=analyze(s,{'from':end})
        self.assertEqual(r['statistics']['max_magnitude'],-.1)

    def test_export_is_bound_to_snapshot_and_contains_provenance(self):
        s=self.snapshot();r=self.client.get('/api/v1/analysis/'+s['snapshot_id']+'?format=csv')
        self.assertEqual(r.status_code,200)
        self.assertIn(s['snapshot_id'],r.text)
        self.assertIn('depth_km',r.text)

    def test_usgs_unknown_magnitude_preserved_only_in_new_contract(self):
        f=usgs_feature();f['properties']['mag']=None
        data={'type':'FeatureCollection','metadata':{'status':200,'count':1,'generated':NOW.timestamp()*1000},'features':[f]}
        with patch.object(server,'now_utc',return_value=NOW),patch.object(server.requests,'get',return_value=response(data=data,content_type='application/json')):
            self.assertEqual(server.fetch_usgs_canarias()[0]['magnitud'],0)
            self.assertIsNone(server.fetch_usgs_canarias(preserve_missing_magnitude=True)[0]['magnitud'])
        self.events[0]['magnitud']=None
        s=self.snapshot();a=analyze(s,{})
        self.assertEqual(a['statistics']['missing_magnitude'],1)
        self.assertIsNone(a['statistics']['max_magnitude'])
        self.assertEqual(analyze(s,{'min_mag':'0'})['statistics']['count'],0)

    def test_new_routes_do_not_expose_sources_database_or_node_packages(self):
        c=server.app.test_client()
        for path in ['/next/assets/../server.py','/next/assets/index.html','/.risklab-next/snapshots.sqlite','/risklab_next/references.json','/next/vendor/cesium/../../package.json','/next/vendor/playwright/index.js']:
            self.assertEqual(c.get(path).status_code,404,path)
        for path in ['/next/', '/']:
            result=c.get(path);self.assertEqual(result.status_code,200);result.close()

    def test_tagoro_conflict_is_not_silently_resolved(self):
        refs=self.client.get('/api/v1/catalog').json['references']
        self.assertEqual(len(refs['infrastructures']),32)
        self.assertNotIn('Tagoro',[v['name'] for v in refs['volcanoes']])
        self.assertEqual(refs['provenance']['status'],'manual_unverified')

    def test_original_public_application_data_and_render_are_byte_identical(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'docs/next/INTEGRITY.json').read_text())
        for name,item in manifest['files'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),item['sha256'],name)
