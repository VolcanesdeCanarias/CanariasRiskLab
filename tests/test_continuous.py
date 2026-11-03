"""Test-only observations, fake clock and provider failures; never production simulation."""
import copy,gzip,json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from flask import Flask
import server
from risklab_next.api import Geography,create_blueprint
from risklab_next.continuous.connectors import Batch,IGN,USGS,AcquisitionError,event,iso,fingerprint
from risklab_next.continuous.store import Store
from risklab_next.continuous.worker import Worker
from risklab_next.continuous.api import capture
from risklab_next.continuous.analysis import analyze_capture

T=datetime(2026,11,3,12,tzinfo=timezone.utc)
def fixture(mag=1,ident='es2026testa',source='IGN',when=None):
    """Clearly synthetic, confined to tests; raw is a test-only row, not a real HTTP response."""
    e=event(ident,iso(when or T-timedelta(hours=1)),28.27,-16.64,10,mag,'mbLg','TEST ONLY',{'test_only':True,'magnitude':mag})
    return Batch(source,[e],iso(T-timedelta(days=10)),iso(T),b'TEST ONLY - synthetic fixture','https://www.ign.es/test-only')
class Sequence:
    def __init__(self,values):self.values=values;self.calls=0
    def fetch(self,now):
        v=self.values[min(self.calls,len(self.values)-1)];self.calls+=1
        if isinstance(v,Exception):raise v
        return copy.deepcopy(v)
class ContinuousTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.geo=Geography()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'continuous.sqlite';self.s=Store(self.path,self.geo);self.now=T
    def ingest(self,batch,now=None):
        when=now or self.now;self.assertTrue(self.s.claim(batch.source,'test',when,force=True));return self.s.ingest(batch,when,when,'test')
    def run_case(self,p=None):return analyze_capture(capture(self.s,'IGN',self.now),p or {})
    def test_duplicates_persist_and_original_hash_roundtrip(self):
        a=self.ingest(fixture());b=self.ingest(fixture(),T+timedelta(minutes=10));s=Store(self.path,self.geo)
        self.assertEqual((a['new'],b['new'],b['duplicates']),(1,0,1))
        with s.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM revisions').fetchone()[0],1)
            raw=db.execute('SELECT raw_gzip,raw_sha256 FROM acquisitions LIMIT 1').fetchone();import hashlib
            self.assertEqual(hashlib.sha256(gzip.decompress(raw[0])).hexdigest(),raw[1])
        self.assertEqual(len(s.event('IGN','es2026testa')['versions']),1)
    def test_revisions_and_reversion_have_immutable_versions_and_changes(self):
        for i,mag in enumerate([1,2,1]):self.ingest(fixture(mag),T+timedelta(minutes=i*10))
        r=self.s.event('IGN','es2026testa');self.assertEqual(len(r['versions']),2);self.assertEqual([c['kind'] for c in r['changes']],['new','revised','revised'])
        self.assertEqual(r['observation']['current_hash'],r['changes'][0]['hash'])
    def test_conflicting_duplicate_is_atomic_and_does_not_replace_good_data(self):
        self.ingest(fixture());bad=fixture(2);bad.events+=fixture(3).events;self.s.claim('IGN','bad',T+timedelta(minutes=10),force=True)
        with self.assertRaises(AcquisitionError):self.s.ingest(bad,T,T+timedelta(minutes=10),'bad')
        self.assertEqual(len(self.s.event('IGN','es2026testa')['versions']),1)
    def test_exact_duplicates_in_one_response_are_counted_once(self):
        b=fixture();b.events+=copy.deepcopy(b.events);r=self.ingest(b);self.assertEqual((r['count'],r['duplicates']),(1,1))
    def test_sources_with_same_identifier_remain_independent(self):
        self.ingest(fixture());self.ingest(fixture(3,source='USGS'));self.assertEqual(self.s.event('IGN','es2026testa')['versions'][0]['observation']['magnitude'],1);self.assertEqual(self.s.event('USGS','es2026testa')['versions'][0]['observation']['magnitude'],3)
    def test_valid_empty_differs_from_failure_after_prior_events(self):
        self.ingest(fixture());b=fixture();b.events=[];self.now+=timedelta(minutes=10);self.ingest(b)
        r=self.run_case();self.assertEqual(r['current']['count'],0);self.assertEqual(r['excluded_unconfirmed'],1);self.assertEqual(self.run_case({'territory':'La Palma'})['excluded_unconfirmed'],0)
        detail=self.s.event('IGN','es2026testa');self.assertEqual(len(detail['versions']),1);self.assertEqual(detail['changes'][-1]['kind'],'not_returned')
        self.now+=timedelta(minutes=10);self.ingest(fixture());self.assertEqual(self.run_case()['current']['count'],1);self.assertEqual(self.s.event('IGN','es2026testa')['changes'][-1]['kind'],'returned')
    def test_aging_out_does_not_infer_withdrawal(self):
        self.ingest(fixture());self.now+=timedelta(days=12);b=fixture();b.events=[];b.start=iso(self.now-timedelta(days=10));b.until=iso(self.now);self.ingest(b)
        self.assertEqual(self.s.event('IGN','es2026testa')['observation']['presence_state'],'returned')
    def test_worker_restart_uses_persisted_due_time(self):
        c=Sequence([fixture()]);Worker(self.s,{'IGN':c},lambda:T).tick();fresh=Store(self.path,self.geo);Worker(fresh,{'IGN':c},lambda:T+timedelta(seconds=30)).tick();self.assertEqual(c.calls,1)
    def test_leases_exclude_concurrent_collectors_and_expire(self):
        self.assertTrue(self.s.claim('IGN','one',T));self.assertFalse(Store(self.path).claim('IGN','two',T));self.assertTrue(self.s.claim('IGN','two',T+timedelta(seconds=181)))
        with self.assertRaises(AcquisitionError):self.s.ingest(fixture(),T,T,'one')
        from concurrent.futures import ThreadPoolExecutor
        stores=[Store(self.path),Store(self.path)]
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda i:stores[i].claim('IGN','parallel'+str(i),T+timedelta(seconds=400)),[0,1]))
        self.assertEqual(sorted(results),[False,True])
    def test_worker_respects_schedule_without_browser_and_detects_new_data(self):
        second=fixture();second.events+=fixture(2,'es2026testb').events;c=Sequence([fixture(),second]);w=Worker(self.s,{'IGN':c},lambda:self.now)
        self.assertEqual(w.tick()[0]['new'],1);self.assertEqual(w.tick(),[]);self.now+=timedelta(seconds=600);self.assertEqual(w.tick()[0]['new'],1);self.assertEqual(c.calls,2)
    def test_scheduler_loop_advances_without_http_or_manual_requests(self):
        c=Sequence([fixture(),fixture(2)]);w=Worker(self.s,{'IGN':c},lambda:self.now)
        outer=self
        class Stop:
            count=0
            def is_set(self):return self.count>=2
            def wait(self,seconds):self.count+=1;outer.now+=timedelta(seconds=600)
        w.run(Stop());self.assertEqual(c.calls,2);self.assertEqual(len(self.s.event('IGN','es2026testa')['versions']),2)
    def test_failed_acquisition_retains_data_and_recovers_without_fallback(self):
        c=Sequence([fixture(),AcquisitionError('http_error',403),fixture(2)]);w=Worker(self.s,{'IGN':c},lambda:self.now);w.tick();self.now+=timedelta(seconds=600);w.tick()
        status=self.s.status(self.now)['sources'][0];self.assertEqual(status['state'],'delayed');self.assertEqual(status['last_http'],403);self.assertEqual(self.run_case()['current']['observed_count'],1)
        self.now+=timedelta(seconds=600);w.tick();self.assertEqual(self.s.status(self.now)['sources'][0]['state'],'updated');self.assertEqual(c.calls,3)
    def test_bounded_retries_http_429_and_retry_after_cannot_be_bypassed(self):
        c=Sequence([AcquisitionError('http_error',503)]);Worker(self.s,{'IGN':c},lambda:T).tick();self.assertEqual(c.calls,2)
        with self.s.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM request_attempts').fetchone()[0],2)
        self.now+=timedelta(seconds=600);c=Sequence([AcquisitionError('http_error',429,3600)]);Worker(self.s,{'IGN':c},lambda:self.now).tick();self.assertEqual(c.calls,1);self.assertFalse(self.s.queue('IGN',self.now+timedelta(seconds=120)))
    def test_no_coverage_empty_and_partial_are_distinct_and_no_quiet_inference(self):
        self.assertEqual(self.run_case()['current']['coverage']['state'],'no_coverage');self.assertIsNone(self.run_case()['current']['count'])
        b=fixture();b.events=[];self.ingest(b);r=self.run_case();self.assertEqual(r['current']['count'],0);self.assertIn('no estimación',r['warning'])
        r=self.run_case({'period':'1y'});self.assertEqual(r['current']['coverage']['state'],'partial');self.assertIsNone(r['current']['count']);self.assertFalse(r['inference_allowed'])
    def test_response_completion_is_not_assumed_coverage_end(self):
        self.ingest(fixture(),T+timedelta(seconds=30));self.now=T+timedelta(seconds=40);r=self.run_case();self.assertEqual(r['parameters']['until'],iso(T));self.assertEqual(r['current']['coverage']['state'],'covered_nominally')
    def test_equal_duration_and_half_open_boundaries(self):
        b=fixture(when=T-timedelta(days=1));b.events+=fixture(ident='es2026testb',when=T).events;self.ingest(b);r=self.run_case();self.assertEqual(r['current']['observed_count'],1);self.assertEqual(r['parameters']['duration_days'],1)
        p=r['parameters'];from risklab_next.continuous.connectors import parse_time
        self.assertEqual(parse_time(p['until'])-parse_time(p['from_']),parse_time(p['from_'])-parse_time(p['previous_from']))
    def test_queries_and_graphs_preserve_counts_and_scales(self):
        self.ingest(fixture());r=self.run_case();self.assertEqual(sum(b['observed_count'] for b in r['series']),r['current']['observed_count']);self.assertEqual(sum(x['count'] for x in r['groups']),1);self.assertEqual(r['series'][0]['max_magnitude_by_type'],{'mbLg':1})
        self.assertEqual(self.run_case({'min_mag':2})['current']['count'],0)
    def test_ign_parser_rejects_invalid_html_and_recognizes_explicit_empty(self):
        with self.assertRaises(AcquisitionError):IGN.parse(b'<html>Access denied</html>',T)
        head='<table><tr>'+''.join('<th>'+x+'</th>' for x in ['Evento','Fecha','Hora UTC','Latitud','Longitud','Profundidad','Magnitud','Tipo Mag.','Localización'])+'</tr>'
        b=IGN.parse((head+'<tr><td>No hay eventos</td></tr></table>').encode(),T);self.assertEqual(b.events,[])
        with self.assertRaises(AcquisitionError):IGN.parse((head+'</table>').encode(),T)
    def test_usgs_fdsn_empty_without_feed_count_is_valid_and_stale_is_not(self):
        raw=dict(type='FeatureCollection',features=[],metadata={'status':200,'generated':T.timestamp()*1000});self.assertEqual(USGS.parse(json.dumps(raw).encode(),T).events,[])
        raw['metadata']['generated']=(T-timedelta(hours=3)).timestamp()*1000
        with self.assertRaises(AcquisitionError):USGS.parse(json.dumps(raw).encode(),T)
    def test_public_api_queues_only_and_exports_replay_without_private_html(self):
        app=Flask(__name__)
        with patch.dict('os.environ',{'RISKLAB_CONTINUOUS_DB':str(self.path)}),patch('risklab_next.api.Geography',return_value=self.geo):app.register_blueprint(create_blueprint({'IGN':lambda:[],'USGS':lambda:[]},server.acquisition_failure,Path(self.tmp.name)/'old.sqlite'))
        client=app.test_client();self.assertEqual(client.post('/api/v1/continuous/refresh/IGN').status_code,503)
        self.ingest(fixture(),__import__('risklab_next.continuous.connectors',fromlist=['clock']).clock());r=client.get('/api/v1/continuous/analysis').json
        self.assertIn('run_id',r);self.assertEqual(client.get('/api/v1/continuous/analysis').json['run_id'],r['run_id']);download=client.get('/api/v1/continuous/runs/'+r['run_id']+'/run.json');self.assertEqual(download.status_code,200);self.assertNotIn('TEST ONLY - synthetic fixture',download.text)
        self.assertEqual(analyze_capture(r['inputs'],{'period':r['parameters']['period']})['run_id'],r['run_id'])
        detail=client.get('/api/v1/continuous/events/IGN/es2026testa');self.assertEqual(detail.status_code,200);self.assertIn('source_record',detail.json['versions'][0]['observation'])
        with self.s.connect() as db:
            bad=copy.deepcopy(r);bad['current']['count']=999;db.execute('UPDATE continuous_runs SET body=? WHERE id=?',(gzip.compress(json.dumps(bad).encode()),r['run_id']))
        self.assertEqual(client.get('/api/v1/continuous/runs/'+r['run_id']+'/run.json').status_code,503)
        for path in ['/api/v1/continuous/raw','/.risklab-next/continuous.sqlite','/next/continuous/store.py']:self.assertEqual(client.get(path).status_code,404)
        self.assertEqual(client.get('/api/v1/institutional/test').status_code,403)
    def test_expired_heartbeat_is_not_reported_as_running(self):
        self.s.heartbeat(T);self.assertTrue(self.s.status(T)['worker_alive']);self.assertFalse(self.s.status(T+timedelta(seconds=181))['worker_alive'])
    def test_corrupted_stored_version_is_not_analyzed_as_zero(self):
        self.ingest(fixture())
        with self.s.connect() as db:
            row=db.execute('SELECT body FROM revisions').fetchone();e=json.loads(row[0]);e['magnitude']=7;db.execute('UPDATE revisions SET body=?',(json.dumps(e),))
        with self.assertRaises(ValueError):capture(self.s,'IGN',T)

if __name__=='__main__':unittest.main()
