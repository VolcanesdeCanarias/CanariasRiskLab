"""Transactional acquisition ledger and immutable event versions on a private disk."""
from datetime import timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid
from contextlib import nullcontext,contextmanager
from .connectors import CONFIG,AcquisitionError,clock,iso,parse_time,fingerprint

ROOT=Path(__file__).resolve().parents[2]

def database_path():return os.environ.get('RISKLAB_CONTINUOUS_DB',str(Path(os.environ.get('RISKLAB_NEXT_DB',str(ROOT/'.risklab-next/snapshots.sqlite'))).parent/'continuous.sqlite'))

class Store:
    def __init__(self,path=None,geography=None):
        self.path=str(path or database_path());self.geography=geography
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        if Path(self.path).parent.name=='.risklab-next':Path(self.path).parent.chmod(0o700)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sources(source TEXT PRIMARY KEY, next_due TEXT, lease_owner TEXT, lease_until TEXT,
                last_attempt TEXT,last_success TEXT,last_error TEXT,last_http INTEGER,failures INTEGER DEFAULT 0,next_manual TEXT);
            CREATE TABLE IF NOT EXISTS acquisitions(id TEXT PRIMARY KEY,source TEXT,started_at TEXT,checked_at TEXT,state TEXT,
                error_code TEXT,http_status INTEGER,url TEXT,coverage_from TEXT,coverage_until TEXT,response_generated_at TEXT,http_date TEXT,
                raw_sha256 TEXT,raw_gzip BLOB,event_keys TEXT,count INTEGER,new_count INTEGER,revised_count INTEGER,duplicate_count INTEGER);
            CREATE INDEX IF NOT EXISTS acquisitions_source ON acquisitions(source,checked_at);
            CREATE TABLE IF NOT EXISTS observations(source TEXT,event_id TEXT,current_hash TEXT,first_seen TEXT,last_seen TEXT,
                PRIMARY KEY(source,event_id));
            CREATE TABLE IF NOT EXISTS revisions(source TEXT,event_id TEXT,hash TEXT,body TEXT,first_seen TEXT,acquisition_id TEXT,
                PRIMARY KEY(source,event_id,hash));
            CREATE TABLE IF NOT EXISTS changes(acquisition_id TEXT,source TEXT,event_id TEXT,kind TEXT,previous_hash TEXT,hash TEXT,
                PRIMARY KEY(acquisition_id,event_id));
            CREATE TABLE IF NOT EXISTS runtime(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE IF NOT EXISTS continuous_runs(id TEXT PRIMARY KEY,body TEXT);
            CREATE TABLE IF NOT EXISTS continuous_cache(key TEXT PRIMARY KEY,run_id TEXT);
            ''')
            db.execute('BEGIN IMMEDIATE')
            obs_cols={r[1] for r in db.execute('PRAGMA table_info(observations)')}
            if 'presence_state' not in obs_cols:db.execute("ALTER TABLE observations ADD COLUMN presence_state TEXT NOT NULL DEFAULT 'returned'")
            if 'last_absence_acquisition' not in obs_cols:db.execute('ALTER TABLE observations ADD COLUMN last_absence_acquisition TEXT')
            cols={r[1] for r in db.execute('PRAGMA table_info(acquisitions)')}
            if 'integrity_json' not in cols:db.execute('ALTER TABLE acquisitions ADD COLUMN integrity_json TEXT')
            source_cols={r[1] for r in db.execute('PRAGMA table_info(sources)')}
            if 'retry_until' not in source_cols:db.execute('ALTER TABLE sources ADD COLUMN retry_until TEXT')
            db.execute('CREATE TABLE IF NOT EXISTS request_attempts(source TEXT,started_at TEXT,finished_at TEXT,state TEXT,error_code TEXT,http_status INTEGER)')
            for s in CONFIG:db.execute('INSERT OR IGNORE INTO sources(source) VALUES (?)',(s,))
        Path(self.path).chmod(0o600)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:yield db
        finally:db.close()
    def heartbeat(self,now):
        with self.connect() as db:db.execute('INSERT OR REPLACE INTO runtime VALUES (?,?)',('heartbeat',iso(now)))
    def claim(self,source,owner,now,force=False):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM sources WHERE source=?',(source,)).fetchone()
            if r['lease_until'] and parse_time(r['lease_until'])>now:return False
            if not force and r['next_due'] and parse_time(r['next_due'])>now:return False
            db.execute('UPDATE sources SET lease_owner=?,lease_until=?,last_attempt=? WHERE source=?',(owner,iso(now+timedelta(seconds=180)),iso(now),source));return True
    def queue(self,source,now):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM sources WHERE source=?',(source,)).fetchone()
            if r['retry_until'] and parse_time(r['retry_until'])>now:return False
            if r['lease_until'] and parse_time(r['lease_until'])>now:return False
            if r['next_manual'] and parse_time(r['next_manual'])>now:return False
            if r['last_attempt'] and (now-parse_time(r['last_attempt'])).total_seconds()<60:return False
            db.execute('UPDATE sources SET next_due=?,next_manual=? WHERE source=?',(iso(now),iso(now+timedelta(seconds=60)),source));return True
    def ingest(self,batch,started,checked,owner):
        # Validate duplicates before opening transaction: conflicting identities invalidate whole batch.
        unique={};duplicates=0
        for e in batch.events:
            h=fingerprint(e)
            if e['source_id'] in unique:
                if unique[e['source_id']][0]!=h:raise AcquisitionError('conflicting_duplicate')
                duplicates+=1;continue
            unique[e['source_id']]=(h,e)
        if len(unique)>20000 or batch.source not in CONFIG or batch.observation_type!='seismic_event':raise AcquisitionError('invalid_batch')
        acq=uuid.uuid4().hex;new=revised=0;keys=[]
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');lease=db.execute('SELECT lease_owner FROM sources WHERE source=?',(batch.source,)).fetchone()
            if lease['lease_owner']!=owner:raise AcquisitionError('lease_lost')
            for ident,(h,e) in sorted(unique.items()):
                old=db.execute('SELECT * FROM observations WHERE source=? AND event_id=?',(batch.source,ident)).fetchone()
                if old is None:kind='new';new+=1
                elif old['current_hash']!=h:kind='revised';revised+=1
                else:kind='returned' if old['presence_state']=='not_returned' else None;duplicates+=1
                island,municipality=self.geography.locate(e['lon'],e['lat']) if self.geography else ('Sin asignación',None)
                body={**e,'id':batch.source+':'+ident,'source':batch.source,'territory':island,'municipality_id':municipality,'revision_hash':h}
                db.execute('INSERT OR IGNORE INTO revisions VALUES (?,?,?,?,?,?)',(batch.source,ident,h,json.dumps(body,ensure_ascii=False,allow_nan=False),iso(checked),acq))
                db.execute("INSERT INTO observations(source,event_id,current_hash,first_seen,last_seen) VALUES (?,?,?,?,?) ON CONFLICT(source,event_id) DO UPDATE SET current_hash=excluded.current_hash,last_seen=excluded.last_seen,presence_state='returned'",(batch.source,ident,h,iso(checked),iso(checked)))
                if kind:db.execute('INSERT INTO changes VALUES (?,?,?,?,?,?)',(acq,batch.source,ident,kind,old['current_hash'] if old else None,h))
                keys.append([ident,h])
            prior=db.execute('SELECT o.*,r.body FROM observations o JOIN revisions r ON r.source=o.source AND r.event_id=o.event_id AND r.hash=o.current_hash WHERE o.source=?',(batch.source,)).fetchall()
            for row in prior:
                t=parse_time(json.loads(row['body'])['time'])
                if row['event_id'] not in unique and parse_time(batch.start)<=t<parse_time(batch.until) and row['presence_state']!='not_returned':
                    db.execute("UPDATE observations SET presence_state='not_returned',last_absence_acquisition=? WHERE source=? AND event_id=?",(acq,batch.source,row['event_id']))
                    db.execute('INSERT INTO changes VALUES (?,?,?,?,?,?)',(acq,batch.source,row['event_id'],'not_returned',row['current_hash'],row['current_hash']))
            raw_hash=hashlib.sha256(batch.raw).hexdigest()
            db.execute('INSERT INTO acquisitions(id,source,started_at,checked_at,state,error_code,http_status,url,coverage_from,coverage_until,response_generated_at,http_date,raw_sha256,raw_gzip,event_keys,count,new_count,revised_count,duplicate_count) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(acq,batch.source,iso(started),iso(checked),'available' if keys else 'empty',None,200,batch.url,batch.start,batch.until,batch.response_generated_at,batch.http_date,raw_hash,gzip.compress(batch.raw,mtime=0),json.dumps(keys),len(keys),new,revised,duplicates))
            db.execute('UPDATE acquisitions SET integrity_json=? WHERE id=?',(json.dumps(dict(connector_version=batch.version,kind=batch.observation_type,count_check=batch.count_check,raw_sha256=raw_hash)),acq))
            db.execute('UPDATE sources SET last_success=?,last_error=NULL,last_http=200,failures=0,retry_until=NULL,next_due=?,lease_owner=NULL,lease_until=NULL WHERE source=?',(iso(checked),iso(checked+timedelta(seconds=CONFIG[batch.source]['interval'])),batch.source))
        return dict(acquisition_id=acq,source=batch.source,new=new,revised=revised,duplicates=duplicates,count=len(keys),raw_sha256=raw_hash)
    def fail(self,source,started,checked,owner,error):
        code=error.code if isinstance(error,AcquisitionError) else 'internal_error';http=getattr(error,'status',None);retry=getattr(error,'retry_after',None)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM sources WHERE source=?',(source,)).fetchone()
            if r['lease_owner']!=owner:return
            delay=max(CONFIG[source]['interval'],retry or 0,min(3600,60*2**min(r['failures'],5)))
            db.execute('INSERT INTO acquisitions(id,source,started_at,checked_at,state,error_code,http_status) VALUES (?,?,?,?,?,?,?)',(uuid.uuid4().hex,source,iso(started),iso(checked),'unavailable',code,http))
            retry_until=iso(checked+timedelta(seconds=delay)) if http==429 or retry else None
            db.execute('UPDATE sources SET retry_until=? WHERE source=?',(retry_until,source))
            db.execute('UPDATE sources SET last_error=?,last_http=?,failures=failures+1,next_due=?,lease_owner=NULL,lease_until=NULL WHERE source=?',(code,http,iso(checked+timedelta(seconds=delay)),source))
    def status(self,now=None,connection=None):
        now=now or clock()
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            heartbeat=db.execute("SELECT value FROM runtime WHERE key='heartbeat'").fetchone();alive=bool(heartbeat and (now-parse_time(heartbeat[0])).total_seconds()<180)
            sources=[]
            for row in db.execute('SELECT * FROM sources ORDER BY source'):
                r=dict(row);age=(now-parse_time(r['last_success'])).total_seconds() if r['last_success'] else None
                r['state']='unavailable' if age is None else 'delayed' if r['last_error'] or age>CONFIG[r['source']]['interval']*2+60 else 'updated'
                r['age_seconds']=age;r['frequency_seconds']=CONFIG[r['source']]['interval'];r['publication_latency']='unknown';r.pop('lease_owner',None)
                latest=db.execute("SELECT id,count,new_count,revised_count,state,response_generated_at,coverage_until FROM acquisitions WHERE source=? AND state!='unavailable' ORDER BY checked_at DESC,rowid DESC LIMIT 1",(r['source'],)).fetchone()
                r['latest']=dict(latest) if latest else None
                if latest:
                    r['latest']['not_returned_count']=db.execute("SELECT count(*) FROM changes WHERE acquisition_id=? AND kind='not_returned'",(latest['id'],)).fetchone()[0]
                sources.append(r)
            return dict(worker_alive=alive,worker_heartbeat=heartbeat[0] if heartbeat else None,sources=sources,now=iso(now),warning='Actualización de consultas, no tiempo real instrumental. Latencia de publicación no garantizada; fuentes independientes, sin sustitución automática.')
    def event(self,source,ident):
        with self.connect() as db:
            o=db.execute('SELECT * FROM observations WHERE source=? AND event_id=?',(source,ident)).fetchone()
            if o is None:return None
            versions=[dict(r) for r in db.execute('SELECT hash,body,first_seen,acquisition_id FROM revisions WHERE source=? AND event_id=? ORDER BY first_seen',(source,ident))]
            for r in versions:r['observation']=json.loads(r.pop('body'))
            changes=[dict(r) for r in db.execute('SELECT c.*,a.checked_at,a.raw_sha256,a.url FROM changes c JOIN acquisitions a ON a.id=c.acquisition_id WHERE c.source=? AND c.event_id=? ORDER BY a.checked_at,a.rowid',(source,ident))]
            return dict(observation=dict(o),versions=versions,changes=changes,raw_access='Original HTTP privado; registros originales públicos por evento incluidos sin sesión ni cabeceras sensibles.')
    def attempt(self,source,started,finished,error=None):
        with self.connect() as db:db.execute('INSERT INTO request_attempts VALUES (?,?,?,?,?,?)',(source,iso(started),iso(finished),'failed' if error else 'valid',getattr(error,'code',None),getattr(error,'status',None)))
    def read_run(self,key):
        with self.connect() as db:r=db.execute('SELECT body FROM continuous_runs WHERE id=?',(key,)).fetchone()
        if r is None:return None
        result=json.loads(gzip.decompress(r[0]) if isinstance(r[0],bytes) else r[0])
        if result.get('run_id')!=key or fingerprint({k:v for k,v in result.items() if k!='run_id'})!=key:raise ValueError('Stored run integrity failure')
        return result
