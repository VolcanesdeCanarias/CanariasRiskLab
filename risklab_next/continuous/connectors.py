"""Fixed official endpoints; bounded HTTP and explicit source-time semantics."""
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
import hashlib
import json
import math
import re
import unicodedata
from email.utils import parsedate_to_datetime
from typing import Protocol
import requests
from bs4 import BeautifulSoup

UTC=timezone.utc
IGN_URL='https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias'
USGS_URL='https://earthquake.usgs.gov/fdsnws/event/1/query'
MAX_BYTES=8_000_000
CONFIG={'IGN':dict(url=IGN_URL,interval=600,window_days=10), 'USGS':dict(url=USGS_URL,interval=900,window_days=30)}

def iso(d):return d.astimezone(UTC).isoformat()
def clock():return datetime.now(UTC)
def parse_time(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('UTC timezone required')
    return d.astimezone(UTC)
def number(x):
    if isinstance(x,bool):raise ValueError('Boolean is not a measurement')
    n=float(x)
    if not math.isfinite(n):raise ValueError('Non-finite measurement')
    return n
def fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def normalize(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').strip()

class AcquisitionError(Exception):
    def __init__(self,code,status=None,retry_after=None):self.code,self.status,self.retry_after=code,status,retry_after;super().__init__(code)

@dataclass
class Batch:
    source:str
    events:list
    start:str
    until:str
    raw:bytes
    url:str
    response_generated_at:str|None=None
    http_date:str|None=None
    observation_type:str='seismic_event'
    version:str='official-seismic/1.0'
    count_check:dict|None=None

class Connector(Protocol):
    """Future signals need their own unit/datum validator and analysis projector."""
    def fetch(self,now:datetime)->Batch:...

def download(url,params=None):
    try:
        with requests.get(url,params=params,headers={'User-Agent':'CanariasRiskLab-NEXT/0.5 (scientific catalogue polling)'},timeout=(8,25),stream=True,allow_redirects=False) as r:
            if r.status_code!=200:
                retry=r.headers.get('Retry-After','');
                try:retry=int(retry) if retry.isdigit() else max(0,int((parsedate_to_datetime(retry)-clock()).total_seconds())) if retry else None
                except (ValueError,TypeError,OverflowError):retry=None
                raise AcquisitionError('http_error',r.status_code,retry)
            raw=bytearray()
            for part in r.iter_content(65536):
                raw.extend(part)
                if len(raw)>MAX_BYTES:raise AcquisitionError('response_too_large')
            return bytes(raw),r.headers.get('Content-Type','').lower(),r.headers.get('Date'),r.url
    except requests.Timeout as e:raise AcquisitionError('timeout') from e
    except requests.RequestException as e:raise AcquisitionError('connection_error') from e

def event(ident,time,lat,lon,depth,mag,kind,place,original,updated=None,uncertainty=None):
    t=parse_time(time);lat,lon,depth=number(lat),number(lon),number(depth)
    mag=None if mag is None else number(mag)
    if not re.fullmatch(r'[a-zA-Z0-9_-]{3,80}',ident) or not (26<=lat<=31 and -19<=lon<=-12 and -10<=depth<=1000) or mag is not None and not -10<=mag<=10:raise ValueError('Invalid seismic observation')
    return dict(source_id=ident,time=iso(t),lat=lat,lon=lon,depth_km=depth,magnitude=mag,magnitude_type=kind or None,place=place or ident,
        source_updated_at=updated,publication_at=None,publication_time_status='not_published_by_this_interface',
        uncertainty=uncertainty or dict(horizontal_km=None,depth_km=None,magnitude=None),source_record=original,
        depth_reference='Profundidad publicada por el proveedor; datum vertical no acreditado aquí. Sin conversión al MDT.')

class IGN:
    def fetch(self,now):
        raw,ctype,http_date,url=download(IGN_URL)
        if 'text/html' not in ctype:raise AcquisitionError('invalid_content_type',200)
        return self.parse(raw,now,url,http_date)
    @staticmethod
    def parse(raw,now,url=IGN_URL,http_date=None):
        try:
            soup=BeautifulSoup(raw,'html.parser');required={'id':'evento','date':'fecha','time':'hora utc','lat':'latitud','lon':'longitud','depth':'profundidad','mag':'magnitud','kind':'tipo mag','place':'localizacion'}
            table=header=None;mapping={}
            for candidate in soup.select('table'):
                for row in candidate.select('tr'):
                    labels=[normalize(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'])]
                    m={k:next((i for i,s in enumerate(labels) if s.startswith(v)),None) for k,v in required.items()}
                    if all(v is not None for v in m.values()):table,header,mapping=candidate,row,m;break
                if table is not None:break
            if table is None:raise ValueError('Unknown table')
            events=[];empty=False
            for row in table.select('tr'):
                if row is header or not row.find('td'):continue
                cells=[c.get_text(' ',strip=True) for c in row.find_all(['td','th'])]
                if not any(cells):continue
                if normalize(' '.join(cells)).rstrip('.') in {'no se han encontrado terremotos','no hay terremotos','no hay eventos'}:empty=True;continue
                v={k:cells[i] for k,i in mapping.items()}
                if not re.fullmatch(r'es\d+[a-z0-9]+',v['id'].lower()):raise ValueError('IGN identity')
                dt=datetime.strptime(v['date']+' '+v['time'],'%d/%m/%Y %H:%M:%S').replace(tzinfo=UTC)
                if dt>now+timedelta(minutes=5) or dt<now-timedelta(days=11):raise AcquisitionError('stale_or_invalid_response',200)
                original=dict(zip(['event_id','date','time_utc','latitude','longitude','depth_km','magnitude','magnitude_type','place'],[v[k] for k in ['id','date','time','lat','lon','depth','mag','kind','place']]))
                events.append(event(v['id'],iso(dt),v['lat'],v['lon'],v['depth'],v['mag'] or None,v['kind'],v['place'],original))
            if empty and events or not events and not empty:raise ValueError('Ambiguous empty response')
            return Batch('IGN',events,iso(now-timedelta(days=10)),iso(now),raw,url,http_date=http_date)
        except AcquisitionError:raise
        except (ValueError,TypeError,IndexError,KeyError,AttributeError,OverflowError) as e:raise AcquisitionError('invalid_response',200) from e

class USGS:
    def fetch(self,now):
        p=dict(format='geojson',starttime=iso(now-timedelta(days=30)),endtime=iso(now),minlatitude=26,maxlatitude=31,minlongitude=-19,maxlongitude=-12,orderby='time-asc',limit=10000,eventtype='earthquake')
        raw,ctype,http_date,url=download(USGS_URL,p)
        if not any(t in ctype for t in ['application/json','application/geo+json']):raise AcquisitionError('invalid_content_type',200)
        batch=self.parse(raw,now,url,http_date)
        count_params={k:v for k,v in p.items() if k not in {'format','orderby','limit'}}
        count_raw,_,_,count_url=download(USGS_URL.replace('/query','/count'),count_params)
        if not re.fullmatch(rb'\s*\d+\s*',count_raw) or int(count_raw)!=len(batch.events):raise AcquisitionError('count_mismatch',200)
        batch.count_check=dict(url=count_url,count=int(count_raw),sha256=hashlib.sha256(count_raw).hexdigest())
        return batch
    @staticmethod
    def parse(raw,now,url=USGS_URL,http_date=None):
        try:
            d=json.loads(raw);meta=d['metadata'];fs=d['features'];generated=datetime.fromtimestamp(number(meta['generated'])/1000,UTC)
            if d['type']!='FeatureCollection' or meta['status']!=200 or meta.get('count',len(fs))!=len(fs) or len(fs)>=10000:raise ValueError('Truncated/invalid catalogue')
            if not now-timedelta(hours=2)<=generated<=now+timedelta(minutes=5):raise AcquisitionError('stale_response_generation',200)
            events=[]
            for f in fs:
                p=f['properties'];g=f['geometry'];lon,lat,depth=g['coordinates'];dt=datetime.fromtimestamp(number(p['time'])/1000,UTC)
                if f['type']!='Feature' or g['type']!='Point' or p['type']!='earthquake' or not now-timedelta(days=30)<=dt<=now+timedelta(minutes=5):raise ValueError('Invalid event')
                updated=None if p.get('updated') is None else iso(datetime.fromtimestamp(number(p['updated'])/1000,UTC))
                if updated and parse_time(updated)>now+timedelta(minutes=5):raise ValueError('Future revision')
                errors={key:None if p.get(field) is None else number(p[field]) for key,field in [('horizontal_km','horizontalError'),('depth_km','depthError'),('magnitude','magError')]}
                if any(v is not None and v<0 for v in errors.values()):raise ValueError('Invalid uncertainty')
                original=dict(id=f['id'],geometry=g,properties={k:p.get(k) for k in ['time','updated','mag','magType','place','type','status','net','code','horizontalError','depthError','magError']})
                events.append(event(f['id'],iso(dt),lat,lon,depth,p.get('mag'),p.get('magType'),p.get('place'),original,updated,errors))
            return Batch('USGS',events,iso(now-timedelta(days=30)),iso(now),raw,url,iso(generated),http_date)
        except AcquisitionError:raise
        except (ValueError,KeyError,TypeError,IndexError,OverflowError,OSError) as e:raise AcquisitionError('invalid_response',200) from e
