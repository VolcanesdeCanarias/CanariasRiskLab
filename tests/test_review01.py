"""Review 01 contracts. All fabricated grids below are testing fixtures only."""
from datetime import timedelta
import copy
import json
from pathlib import Path
import tempfile
import unittest
from risklab_next.api import Geography, analyze
from risklab_next.terrain import validate_grid, load_grid
from test_next import NextTests


class ReviewNavigationTests(NextTests):
    # Reuse setup, not inherited tests (the loader below excludes inherited methods).
    def test_review_catalogue_has_island_and_municipal_bounds(self):
        c=self.client.get('/api/v1/catalog').json
        self.assertEqual(len(c['territory_views']),8)
        b=c['territory_views']['La Graciosa'];self.assertLess(b[3],29.31);self.assertGreater(b[1],29.2)
        self.assertEqual(self.geo.locate(-13.51,29.25)[0],'La Graciosa')
        self.assertNotEqual(self.geo.locate(-13.51,29.40)[0],'La Graciosa')
        self.assertTrue(all(len(m['bounds'])==4 for m in c['municipalities']))

    def test_review_municipality_and_depth_filters_are_reproducible(self):
        s=self.snapshot();m=s['events'][0]['municipality_id'];self.assertIsNotNone(m)
        url='/api/v1/analysis/'+s['snapshot_id']
        a=self.client.get(url+'?municipality_id='+m+'&min_depth=11&max_depth=13').json
        self.assertEqual(a['statistics']['count'],1)
        self.assertEqual(a['parameters']['municipality_id'],m)
        self.assertEqual(self.client.get(url+'?min_depth=13&max_depth=20').json['state'],'filtered_empty')
        for q in ['municipality_id=99999','min_depth=nan','min_depth=20&max_depth=1','max_depth=2000']:
            self.assertEqual(self.client.get(url+'?'+q).status_code,400,q)
        csv=self.client.get(url+'?municipality_id='+m+'&max_depth=11&format=csv')
        self.assertEqual(len(csv.text.strip().splitlines()),1)

    def test_review_period_without_coverage_is_not_zero_or_empty(self):
        s=self.snapshot();url='/api/v1/analysis/'+s['snapshot_id']
        query='?from='+ (self.now-timedelta(days=30)).isoformat().replace('+00:00','Z')+'&until='+(self.now-timedelta(days=20)).isoformat().replace('+00:00','Z')
        r=self.client.get(url+query).json
        self.assertEqual(r['state'],'no_coverage');self.assertIsNone(r['statistics']['count'])
        self.assertIn('no solapa',r['explanation']['text']);self.assertEqual(self.client.get(url+query+'&format=csv').status_code,503)

    def test_review_documentary_cards_are_cited_not_current_alerts(self):
        c=self.client.get('/api/v1/catalog').json
        self.assertEqual({s['catalogue_id'] for s in c['volcanic_catalogue']['systems']},{'383010','383020','383030','383040','383060'})
        for card in c['volcanic_catalogue']['systems']:
            self.assertIn('volcano.si.edu',card['sources'][0]['url']);self.assertNotIn('alert',card)
        self.assertEqual(c['instrumentation']['operational_status'],'not_verified')
        self.assertEqual(len(c['instrumentation']['stations']),4)
        self.assertTrue(all('estado' not in s for s in c['instrumentation']['stations']))

    def test_review_cartography_uses_fixed_official_sources_and_attribution(self):
        c=self.client.get('/api/v1/catalog').json['cartography']
        self.assertEqual(len(c['basemaps']),4)
        for b in c['basemaps'][1:]:
            self.assertTrue(b['url'].startswith('https://www.ign.es/'))
            self.assertIn('CC BY 4.0',b['attribution']);self.assertIn('licence_url',b)
        self.assertEqual(self.client.get('/api/v1/terrain').json['state'],'not_configured')
        self.assertEqual(self.client.get('/.risklab-next/terrain.json').status_code,404)


class TerrainTests(unittest.TestCase):
    def fixture(self):
        return {'schema':'risklab.dem/1','width':2,'height':2,'bounds':[-16.7,28.2,-16.6,28.3],
                'values':[100,200,None,300], 'metadata':{'licence':'CC-BY-4.0','source_url':'https://www.ign.es/example-test-only',
                'product':'TEST ONLY','vertical_datum':'test datum','imported_at':'2026-11-02',
                'attribution':'test only','original_sha256':'a'*64,'source_resolution_m':25}}

    def test_grid_budget_nodata_and_no_manufactured_heights(self):
        grid=self.fixture();self.assertIsNone(validate_grid(grid)['values'][2])
        for bad in [dict(grid,width=1000),dict(grid,values=[100]),dict(grid,values=[float('nan'),1,1,1]),dict(grid,values=[None]*4),dict(grid,bounds=[0,0,1,1])]:
            with self.assertRaises(ValueError):validate_grid(bad)

    def test_unsupported_licence_or_missing_provenance_is_rejected(self):
        for changes in [{'licence':'unknown'},{'source_url':'https://private.example/earth'},{'vertical_datum':''}]:
            grid=self.fixture();grid['metadata'].update(changes)
            with self.assertRaises(ValueError):validate_grid(grid)

    def test_missing_invalid_and_documented_local_import_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'terrain.json';self.assertEqual(load_grid(p)['state'],'not_configured')
            p.write_text('oops');self.assertEqual(load_grid(p)['state'],'invalid')
            p.write_text(json.dumps(self.fixture()));self.assertEqual(load_grid(p)['state'],'documented_import')


def load_tests(loader,tests,pattern):
    suite=unittest.TestSuite()
    for name in ReviewNavigationTests.__dict__:
        if name.startswith('test_review_'):suite.addTest(ReviewNavigationTests(name))
    suite.addTests(loader.loadTestsFromTestCase(TerrainTests))
    return suite
