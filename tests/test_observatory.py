"""Official archived data integration, independent cross-checks and security boundaries."""
import copy
import csv
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from flask import Flask
import server
from risklab_next.api import Geography,create_blueprint
from risklab_next.observatory import historical,official_layer,classified_events,analyze,intersects,answer,date

class ObservatoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo=Geography();cls.manifest,cls.events=historical();cls.layer,cls.features=official_layer();cls.classified=classified_events(cls.geo)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.app=Flask(__name__)
        with patch('risklab_next.api.Geography',return_value=self.geo):self.app.register_blueprint(create_blueprint({'IGN':lambda:[],'USGS':lambda:[]},server.acquisition_failure,Path(self.tmp.name)/'db.sqlite'))
        self.client=self.app.test_client()
    def post(self,p=None):return self.client.post('/api/v1/observatory/runs',json=p or {})
    def test_original_pages_reconciled_and_full_year_end_present(self):
        self.assertEqual(len(self.events),3609);self.assertEqual(len({e['id'] for e in self.events}),3609);self.assertEqual(len(self.manifest['pages']),73)
        self.assertTrue(self.events[-1]['time'].startswith('2024-12-31T23:'))
        self.assertTrue(all(e['uncertainty']['depth_km'] is None for e in self.events));self.assertIn('CC BY',self.manifest['licence']['name'])
        capture=Path('risklab_next/data/observatory/ign-2023-2024/extracted-tables.json').read_text();self.assertNotIn('authToken',capture);self.assertNotIn('JSESSIONID',capture)
    def test_archipelago_partition_has_no_duplicate_or_lost_records(self):
        self.assertEqual(len(self.classified),3609);self.assertEqual(len({e['id'] for e in self.classified}),3609)
        total=0
        for name in ['Tenerife','La Palma','El Hierro','La Gomera','Gran Canaria','Fuerteventura','Lanzarote','La Graciosa','Entorno marítimo']:
            a=analyze({'territory':name},self.geo);total+=a['current']['count'];self.assertFalse(a['inference_allowed'])
        self.assertEqual(total,analyze({'territory':'Canarias'},self.geo)['current']['count'])
    def test_independent_sql_counts_periods_and_spatiotemporal_sum(self):
        r=analyze({},self.geo);db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.execute('CREATE TABLE e(time TEXT, island TEXT)');db.executemany('INSERT INTO e VALUES (?,?)',[(e['time'],e['territory']) for e in self.classified])
        p=r['parameters'];current=db.execute('SELECT count(*) FROM e WHERE island=? AND time>=? AND time<?',('Tenerife',p['from_'],p['until'])).fetchone()[0]
        previous=db.execute('SELECT count(*) FROM e WHERE island=? AND time>=? AND time<?',('Tenerife',p['previous_from'],p['from_'])).fetchone()[0]
        other=db.execute('SELECT count(*) FROM e WHERE island=? AND time>=? AND time<?',('La Palma',p['from_'],p['until'])).fetchone()[0]
        self.assertEqual((current,previous,other),(238,232,90));self.assertEqual((r['current']['count'],r['previous']['count'],r['comparison']['count']),(current,previous,other))
        self.assertEqual(sum(b['count'] for b in r['series']),current);self.assertEqual(sum(g['count'] for g in r['groups']),current)
        mixed=[b for b in r['series'] if len(b['max_magnitude_by_type'])>1];self.assertTrue(mixed);self.assertTrue(all(b['max_magnitude'] is None for b in mixed))
        self.assertEqual(date(p['until'])-date(p['from_']),date(p['from_'])-date(p['previous_from']))
    def test_empty_filter_and_no_coverage_cannot_be_confused(self):
        empty=self.post({'min_mag':9}).json;self.assertEqual(empty['current']['count'],0);self.assertEqual(empty['current']['state'],'empty_selection')
        no=self.post({'from':'2025-01-01T00:00:00Z','until':'2025-02-01T00:00:00Z'}).json;self.assertIsNone(no['current']['count']);self.assertEqual(no['current']['state'],'no_coverage')
        self.assertEqual(self.client.get('/api/v1/observatory/runs/'+no['run_id']+'/events.csv').status_code,422)
    def test_failed_source_is_503_then_recovers_without_fake_zero(self):
        with patch('risklab_next.observatory.historical',side_effect=ValueError('bad hash')):
            response=self.post();self.assertEqual(response.status_code,503);self.assertEqual(response.json['state'],'unavailable');self.assertNotIn('current',response.json)
            self.assertEqual(self.client.get('/api/v1/observatory/catalog').status_code,503)
        self.assertEqual(self.post().json['current']['count'],238)
    def test_parameters_are_bounded_no_nonfinite_or_implicit_dates(self):
        for p in [{'territory':'Atlantis'},{'compare':'x'},{'cell':0},{'bin_days':2},{'min_mag':'NaN'},{'from':'2024-01-01'},{'municipality':'../x'},{'bounds':[-180,-90,180,90]}]:self.assertEqual(self.post(p).status_code,400,p)
        self.assertEqual(self.client.post('/api/v1/observatory/runs',json={'x':'x'*5000}).status_code,413)
    def test_rectangle_intersection_handles_edges_containment_and_holes(self):
        poly=[[[0,0],[10,0],[10,10],[0,10],[0,0]],[[3,3],[7,3],[7,7],[3,7],[3,3]]]
        self.assertTrue(intersects(poly,[-1,1,11,2]));self.assertTrue(intersects(poly,[1,1,2,2]));self.assertTrue(intersects(poly,[-1,-1,11,11]));self.assertFalse(intersects(poly,[4,4,6,6]));self.assertFalse(intersects(poly,[11,11,12,12]))
    def test_official_layer_includes_88_municipalities_and_graciosa_in_teguise(self):
        self.assertEqual(len(self.features),88);self.assertIn('35024',{f['id'] for f in self.features})
        response=self.client.get('/api/v1/observatory/territory?bounds=-13.56,29.2,-13.43,29.32');self.assertEqual(response.status_code,200)
        self.assertIn('35024',{f['properties']['id'] for f in response.json['geojson']['features']});self.assertIn('no afectación',response.json['warning'])
        self.assertEqual(self.client.get('/api/v1/observatory/territory?bounds=nan,27,-13,30').status_code,400)
    def test_assistance_is_grounded_and_abstains_outside_scope(self):
        r=analyze({},self.geo);a=answer('Compara Tenerife y La Palma',r);self.assertEqual(a['state'],'answered');self.assertIn('238',a['text']);self.assertEqual(a['run_id'],r['run_id']);self.assertTrue(a['sources'])
        self.assertEqual(answer('¿Habrá una erupción?',r)['state'],'abstained');self.assertEqual(answer('Compara El Hierro y Tenerife',r)['state'],'unsupported_scope');self.assertEqual(answer('Compara 2010',r)['state'],'unsupported_scope');self.assertIn('GNSS',answer('¿Qué falta?',r)['text'])
        teide=answer('¿Qué observaciones hay cerca del Teide?',r);self.assertEqual(teide['selection']['count'],sum(-16.85<=e['lon']<=-16.45 and 28.12<=e['lat']<=28.42 for e in r['current']['events']));self.assertIn('caja manual',teide['text'])
    def test_exports_bind_saved_run_and_preserve_observation_ids(self):
        r=self.post().json;url='/api/v1/observatory/runs/'+r['run_id']+'/';a=self.client.get(url+'run.json');self.assertEqual(a.json['run_id'],r['run_id'])
        rows=list(csv.DictReader(io.StringIO(self.client.get(url+'events.csv').text)));self.assertEqual(sum(x['selection']=='current' for x in rows),238);self.assertEqual(self.client.get(url+'server.py').status_code,404)
        self.assertEqual(self.post().json['run_id'],r['run_id']);self.assertNotEqual(self.post({'min_mag':1}).json['run_id'],r['run_id'])
    def test_legacy_and_private_http_boundaries_remain(self):
        self.assertEqual(self.client.get('/api/v1/institutional/evidence').status_code,403)
        for u in ['/next/server.py','/next/observatory.py','/next/../../server.py','/api/v1/observatory/../../server.py']:self.assertEqual(self.client.get(u).status_code,404)
        self.assertEqual(self.client.get('/next/observatory.mjs').status_code,200)

if __name__=='__main__':unittest.main()
