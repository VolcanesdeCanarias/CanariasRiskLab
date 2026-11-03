"""Official archived IGN observations and territorial queries; descriptive only."""
import csv
import gzip
import hashlib
import io
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from collections import Counter, defaultdict
from bs4 import BeautifulSoup
from flask import jsonify, request, Response, send_from_directory
from .research_v1 import digest, date, finite

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/observatory'
METHOD='ign-multinsular-descriptive/1.0'
WARNING='Recuentos de observaciones catalogadas, no actividad real, causalidad, peligro ni alerta. Completitud instrumental no acreditada.'

def polygons(g):return g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
def bounds(poly):
    xs,ys=zip(*poly[0]);return [min(xs),min(ys),max(xs),max(ys)]
def overlap(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def within(x,y,poly):
    from .api import inside_ring
    return inside_ring(x,y,poly[0]) and not any(inside_ring(x,y,h) for h in poly[1:])
def intersects(poly,box):
    if not overlap(bounds(poly),box):return False
    w,s,e,n=box
    if any(within(x,y,poly) for x,y in [(w,s),(w,n),(e,s),(e,n)]):return True
    # Liang–Barsky segment/rectangle clipping; includes edges, preserves holes.
    for ring in poly:
        for (x,y),(xx,yy) in zip(ring,ring[1:]+ring[:1]):
            lo,hi=0.,1.;dx,dy=xx-x,yy-y
            for p,q in [(-dx,x-w),(dx,e-x),(-dy,y-s),(dy,n-y)]:
                if p==0:
                    if q<0:break
                elif p<0:lo=max(lo,q/p)
                else:hi=min(hi,q/p)
                if lo>hi:break
            else:return True
    return False

@lru_cache(maxsize=1)
def official_layer():
    folder=DATA/'ign-administration';m=json.loads((folder/'manifest.json').read_text())
    features=[]
    for name,meta in m['feature_files'].items():
        raw=(folder/name).read_bytes()
        if len(raw)!=meta['bytes'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Geometría municipal alterada')
        features.append(json.loads(raw))
    data=dict(type='FeatureCollection',features=features)
    canonical=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    if hashlib.sha256(canonical).hexdigest()!=m['canonical_geometry_sha256']:raise ValueError('Geometría combinada alterada')
    if len(data['features'])!=88 or m['municipalities']!=88:raise ValueError('Inventario municipal incompleto')
    features=[]
    for f in data['features']:
        parts=polygons(f['geometry']);features.append({**f,'parts':[(bounds(p),p) for p in parts]})
    return m,features

@lru_cache(maxsize=1)
def historical():
    folder=DATA/'ign-2023-2024';m=json.loads((folder/'manifest.json').read_text());rows=[]
    # Full portal HTML includes anonymous session metadata and remains private.
    # Public captures preserve every seismic table field, source hash and checked query.
    for name,meta in m['public_table_capture'].items():
        raw=(folder/name).read_bytes()
        if len(raw)!=meta['bytes'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Captura pública IGN alterada')
    capture=json.loads((folder/'extracted-tables.json').read_text())
    if capture['schema']!='risklab.public-ign-tables/1' or len(capture['pages'])!=len(m['pages']):raise ValueError('Captura incompleta')
    for page,source in zip(capture['pages'],m['pages']):
        if page['original_sha256']!=source['original_sha256'] or page['source_url']!=source['url'] or page['total']!=m['count']:raise ValueError('Procedencia de página inconsistente')
        if len(page['headers'])!=12 or page['headers'][2]!='Hora UTC':raise ValueError('Tabla IGN no reconocida')
        if page['criteria']!={'latMin':'27','latMax':'30','longMin':'-19','longMax':'-13','startDate':'01/01/2023','endDate':'31/12/2024'}:raise ValueError('Criterios de origen incorrectos')
        rows.extend(page['rows'])
    if len(rows)!=m['count'] or len({r[0] for r in rows})!=len(rows):raise ValueError('Histórico truncado o duplicado')
    if hashlib.sha256((folder/'rows.json').read_bytes()).hexdigest()!=m['rows_sha256'] or digest(rows)!=digest(json.loads((folder/'rows.json').read_text())):raise ValueError('Derivado y original discrepan')
    events=[]
    for r in rows:
        if len(r)!=12 or not re.fullmatch(r'[A-Za-z0-9]{6,32}',r[0]):raise ValueError('Fila IGN no admitida')
        ident,day,clock,local,lat,lon,depth,mag,kind,intensity,place=r[:11]
        time=datetime.strptime(day+' '+clock,'%d/%m/%Y %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
        lat,lon=finite(lat),finite(lon);dep=None if depth in ('','-','—') else finite(depth);magnitude=None if mag in ('','-','—') else finite(mag)
        if not (27<=lat<=30 and -19<=lon<=-13 and m['coverage']['from']<=time<m['coverage']['until']):raise ValueError('Registro fuera de consulta')
        if dep is not None and not -10<=dep<=1000 or magnitude is not None and not -10<=magnitude<=10:raise ValueError('Valor IGN no plausible')
        events.append(dict(id=ident,source='IGN histórico · archivo 2023–2024',time=time,lat=lat,lon=lon,depth_km=dep,magnitude=magnitude,magnitude_type=kind or None,place=place,
            uncertainty=dict(horizontal_km=None,depth_km=None,magnitude=None),depth_reference='Profundidad publicada por IGN; datum no especificado en tabla; no transformar a cota MDT.',url='https://www.ign.es/web/ign/portal/ultimos-terremotos/-/ultimos-terremotos/getDetalles?evid='+ident))
    m['dataset_hash']=digest(m)
    return m,sorted(events,key=lambda e:(e['time'],e['id']))

def analyze(parameters,geography):
    m,events=historical();p=parameters
    start,until=date(p.get('from','2024-07-01T00:00:00Z')),date(p.get('until','2025-01-01T00:00:00Z'));duration=until-start
    if not timedelta(0)<duration<=timedelta(days=366):raise ValueError('Periodo positivo de hasta 366 días')
    territory=p.get('territory','Tenerife');compare=p.get('compare','La Palma');municipality=p.get('municipality','');valid={'Canarias','Entorno marítimo',*geography.views}
    if territory not in valid or compare not in valid:raise ValueError('Territorio desconocido')
    if municipality and municipality not in {x['id'] for x in geography.municipalities}:raise ValueError('Municipio desconocido')
    minimum=finite(p.get('min_mag',-10));step=finite(p.get('cell',.1));days=int(p.get('bin_days',7));kind=p.get('mag_type','all')
    if not -10<=minimum<=10 or step not in {.05,.1,.2} or days not in {1,7,30} or kind not in {'all','mbLg','mb','ML','Mw','M','magnitude_unknown'}:raise ValueError('Filtro fuera de presupuesto')
    box=p.get('bounds')
    if box is not None:
        if not isinstance(box,list) or len(box)!=4:raise ValueError('Caja inválida')
        box=list(map(finite,box))
        if not (-19<=box[0]<box[2]<=-13 and 27<=box[1]<box[3]<=30):raise ValueError('Área fuera de cobertura')
    lm,_=official_layer()
    classified=classified_events(geography)
    eligible=[e for e in classified if (e['magnitude'] is not None and e['magnitude']>=minimum or e['magnitude'] is None and minimum==-10) and (kind=='all' or (e['magnitude_type'] or 'magnitude_unknown')==kind) and (not box or box[0]<=e['lon']<=box[2] and box[1]<=e['lat']<=box[3])]
    def select(t,a,b,municipal=False):
        if a<date(m['coverage']['from']) or b>date(m['coverage']['until']):return None
        return [e for e in eligible if a<=date(e['time'])<b and (t=='Canarias' or e['territory']==t) and (not municipal or not municipality or e['municipality_id']==municipality)]
    current=select(territory,start,until,True);previous=select(territory,start-duration,start,True);other=select(compare,start,until)
    def stats(es):
        return dict(state='no_coverage',count=None,events=[]) if es is None else dict(state='available' if es else 'empty_selection',count=len(es),events=es,unknown_magnitude=sum(e['magnitude'] is None for e in es),unknown_depth=sum(e['depth_km'] is None for e in es))
    series=defaultdict(list);cells=Counter()
    for e in current or []:
        k=int((date(e['time'])-start).total_seconds()//(days*86400));series[k].append(e)
        cells[(math.floor((e['lon']+19)/step),math.floor((e['lat']-27)/step),k)]+=1
    temporal=[]
    if current is not None:
        for k in range(math.ceil(duration.total_seconds()/(days*86400))):
            es=series[k];ds=[e['depth_km'] for e in es if e['depth_km'] is not None];ms=[e['magnitude'] for e in es if e['magnitude'] is not None]
            by_type={}
            for event in es:
                if event['magnitude'] is not None and event['magnitude_type']:
                    key=event['magnitude_type'];by_type[key]=max(by_type.get(key,event['magnitude']),event['magnitude'])
            temporal.append(dict(index=k,from_=(start+timedelta(days=k*days)).isoformat(),until=min(until,start+timedelta(days=(k+1)*days)).isoformat(),count=len(es),mean_depth_km=sum(ds)/len(ds) if ds else None,max_magnitude=next(iter(by_type.values())) if len(by_type)==1 else None,max_magnitude_by_type=by_type))
    result=dict(schema='risklab.observatory-run/1',method=METHOD,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),dataset_hash=m['dataset_hash'],layer_hash=lm['canonical_geometry_sha256'],geography_convention_sha256=geography.sha256,geography_method_sha256=hashlib.sha256((ROOT/'api.py').read_bytes()).hexdigest(),
        parameters=dict(from_=start.isoformat(),until=until.isoformat(),previous_from=(start-duration).isoformat(),duration_days=duration.total_seconds()/86400,territory=territory,compare=compare,municipality=municipality,min_mag=minimum,mag_type=kind,cell=step,bin_days=days,bounds=box),
        current=stats(current),previous=stats(previous),comparison=stats(other),series=temporal,
        groups=[dict(bounds=[-19+x*step,27+y*step,-19+(x+1)*step,27+(y+1)*step],time_bin=k,count=c) for (x,y,k),c in sorted(cells.items())],
        group_note='Agrupaciones por celdas angulares y bloques UTC desde el inicio del periodo; no clusters físicos ni test de anomalía. Tamaño métrico no uniforme.',
        comparison_note='Misma fuente y filtros de magnitud, mismo intervalo para territorios; municipio solo aplicado al territorio principal. Periodo previo de duración exacta. Comparación de registros, no de tasas físicas.',
        manifest=m,territorial_source=lm,warning=WARNING,missing=['Completitud de detección y cambios de red','Errores de localización individuales','GNSS/InSAR, gases y series instrumentales','Validación científica de interpretaciones'],inference_allowed=False)
    result['run_id']=digest(result);return result

@lru_cache(maxsize=1)
def classified_events(geography):
    _,events=historical();_,features=official_layer();islands={m['id']:m['island'] for m in geography.municipalities};out=[]
    for e in events:
        ident=next((f['id'] for f in features if any(b[0]<=e['lon']<=b[2] and b[1]<=e['lat']<=b[3] and within(e['lon'],e['lat'],poly) for b,poly in f['parts'])),None)
        island=islands.get(ident,'Entorno marítimo')
        if ident=='35024' and geography.locate(e['lon'],e['lat'])[0]=='La Graciosa':island='La Graciosa'
        out.append({**e,'municipality_id':ident,'territory':island})
    return out

def answer(question,r):
    q=question.lower()
    refs=[{'title':'IGN · Catálogo de terremotos','url':'https://doi.org/10.7419/162.03.2022'},{'title':'IGN · política de datos','url':r['manifest']['licence']['url']}]
    if any(x in q for x in ['erupcion','erupción','predic','alerta','evac','seguro','riesgo']):return dict(state='abstained',text='Estas observaciones no permiten predecir erupciones, fijar alertas ni evaluar seguridad. Consulta a los organismos competentes.',run_id=r['run_id'],sources=refs)
    if re.search(r'\d',q):return dict(state='unsupported_scope',text='Los periodos se eligen en el formulario; no interpreto fechas escritas en la pregunta. Selecciona las fechas y vuelve a calcular.',run_id=r['run_id'],sources=refs)
    named=[x for x in ['tenerife','la palma','el hierro','la graciosa','lanzarote','gran canaria','fuerteventura','la gomera'] if x in q]
    if any(x not in (r['parameters']['territory'].lower(),r['parameters']['compare'].lower()) for x in named):return dict(state='unsupported_scope',text='Selecciona esos territorios y vuelve a calcular: no reutilizo resultados de otra área.',run_id=r['run_id'],sources=refs)
    if 'teide' in q:
        if r['parameters']['territory'] not in {'Tenerife','Canarias'}:return dict(state='unsupported_scope',text='Selecciona Tenerife o Canarias para consultar observaciones en la caja documental Teide–Pico Viejo.',run_id=r['run_id'],sources=refs)
        if r['current']['count'] is None:return dict(state='abstained',text='El periodo seleccionado no tiene cobertura en el archivo; no calculo un recuento cercano al Teide.',run_id=r['run_id'],sources=refs)
        box=[-16.85,28.12,-16.45,28.42]
        selected=[e for e in r['current']['events'] if box[0]<=e['lon']<=box[2] and box[1]<=e['lat']<=box[3]]
        return dict(state='answered',text=f"En la caja de navegación documental Teide–Pico Viejo {box}, hay {len(selected)} registros de la selección actual, entre {r['parameters']['from_']} y {r['parameters']['until']} (fin excluido). Se conservan todos los filtros activos. Es una caja manual de estudio, no límite geológico ni radio de influencia; no atribuye origen volcánico.",fields=['current.events','parameters'],selection=dict(bounds=box,count=len(selected),event_ids=[e['id'] for e in selected]),run_id=r['run_id'],sources=refs+[dict(title='IGN · Geología de Tenerife',url='https://www.ign.es/web/resources/sismologia/tproximos/sismotectonica/pag_sismotectonicas/can_tenerife.html')],engine='Herramientas deterministas, sin modelo generativo')
    if any(x in q for x in ['falta','limita','incertid','cobertura']):text='Falta: '+', '.join(r['missing'])+'. Un vacío del catálogo no acredita inactividad.';fields=['missing','manifest.limitations']
    elif any(x in q for x in ['compara','histori','sismic','observa','registro','sabemos']):
        p=r['parameters'];text=f"{p['from_']} → {p['until']} (fin excluido), {p['duration_days']} días: {p['territory']} {r['current']['count']} registros; {p['compare']} {r['comparison']['count']}. Periodo previo en {p['territory']}: {r['previous']['count']}. No disponible significa falta de cobertura, no cero. "+WARNING;fields=['parameters','current','comparison','previous']
        if 'teide' in q:text+=' La selección es territorial o una caja explícita, no un perímetro geológico del Teide. Usa «área visible» para delimitar tu estudio; no atribuye un origen volcánico.'
    elif any(x in q for x in ['fuente','respal','evidencia']):text='Consulta archivada IGN, páginas originales comprobadas por SHA-256 y total publicado; capa territorial IGN BDDAE. Cada respuesta se vincula a esta ejecución.';fields=['manifest.pages','dataset_hash','territorial_source']
    else:return dict(state='unsupported',text='Puedo comparar los territorios y periodos seleccionados, explicar cobertura, información ausente y fuentes. No interpreto episodios ni causas.',run_id=r['run_id'],sources=refs)
    return dict(state='answered',text=text,fields=fields,run_id=r['run_id'],sources=refs,engine='Herramientas deterministas, sin modelo generativo')

def register_observatory(bp,store,geography):
    with store.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS observatory_runs (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    @bp.get('/next/observatory.mjs')
    @bp.get('/next/observatory.css')
    def observatory_assets():return send_from_directory(ROOT.parent/'next',request.path.rsplit('/',1)[-1])
    @bp.get('/api/v1/observatory/catalog')
    def obs_catalog():
        try:m,es=historical();lm,_=official_layer()
        except (ValueError,OSError,KeyError,StopIteration):return jsonify(state='unavailable',error='Archivo oficial no verificable; no se calcula ausencia de actividad.'),503
        return jsonify(state='available',manifest=m,territorial_layer=lm,territories=['Canarias',*geography.views,'Entorno marítimo'],municipalities=geography.municipalities,views=geography.views,systems=json.loads((ROOT/'volcanic-systems.json').read_text()),warning=WARNING)
    @bp.get('/api/v1/observatory/territory')
    def obs_territory():
        try:
            m,fs=official_layer();box=list(map(finite,request.args.get('bounds','-19,27,-13,30').split(',')))
            if len(box)!=4 or not (-19<=box[0]<box[2]<=-13 and 27<=box[1]<box[3]<=30):raise ValueError('Área inválida')
            selected=[f for f in fs if any(intersects(poly,box) for b,poly in f['parts'] if overlap(b,box))]
            # Sampled outlines only; full source geometry is retained for rectangle intersection.
            features=[]
            for f in selected:
                coords=[]
                for _,poly in f['parts']:
                    rings=[]
                    for ring in poly:
                        stride=max(1,math.ceil(len(ring)/300));r=ring[::stride];rings.append(r+[r[0]] if r[-1]!=r[0] else r)
                    coords.append(rings)
                features.append(dict(type='Feature',properties=f['properties'],geometry=dict(type='MultiPolygon',coordinates=coords)))
            return jsonify(state='available',bounds=box,count=len(features),source=m,visualization='Contornos muestreados, no usar para cálculos. Intersección contra polígonos completos de origen.',geojson=dict(type='FeatureCollection',features=features),warning='Intersección administrativa con el área; no afectación ni riesgo.')
        except (ValueError,TypeError,OSError,KeyError):return jsonify(state='unavailable',error='Consulta territorial inválida o fuente no verificable'),400
    @bp.post('/api/v1/observatory/runs')
    def obs_run():
        if request.content_length is None or request.content_length>4096:return jsonify(error='Presupuesto de consulta excedido'),413
        p=request.get_json()
        if not isinstance(p,dict):return jsonify(error='Se requiere objeto de parámetros'),400
        try:historical();official_layer()
        except (ValueError,OSError,KeyError,StopIteration):return jsonify(state='unavailable',error='Datos oficiales no verificables; no se calcula actividad'),503
        try:r=analyze(p,geography)
        except (OSError,KeyError,StopIteration):return jsonify(state='unavailable',error='Datos oficiales no disponibles; no se calcula actividad'),503
        except (ValueError,TypeError,OverflowError):return jsonify(state='invalid',error='Datos no verificables o parámetros inválidos; no se calcula actividad'),400
        with store.connect() as db:db.execute('INSERT OR IGNORE INTO observatory_runs VALUES (?,?)',(r['run_id'],json.dumps(r,ensure_ascii=False,allow_nan=False)))
        return jsonify(r)
    def read(key):
        with store.connect() as db:row=db.execute('SELECT body FROM observatory_runs WHERE id=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    @bp.post('/api/v1/observatory/runs/<key>/ask')
    def obs_ask(key):
        if request.content_length is None or request.content_length>2048:return jsonify(error='Pregunta demasiado grande'),413
        r=read(key)
        if not r:return jsonify(error='Ejecución no encontrada'),404
        p=request.get_json();q=p.get('question') if isinstance(p,dict) else None
        if not isinstance(q,str) or not q.strip() or len(q)>500:return jsonify(error='Pregunta inválida'),400
        return jsonify(answer(q,r))
    @bp.get('/api/v1/observatory/runs/<key>/<kind>')
    def obs_export(key,kind):
        r=read(key)
        if not r or kind not in {'run.json','events.csv'}:return jsonify(error='No encontrado'),404
        if r['current']['count'] is None:return jsonify(error='No exportar falta de cobertura como cero'),422
        if kind=='run.json':body,mime=json.dumps(r,ensure_ascii=False,indent=2),'application/json'
        else:
            out=io.StringIO();w=csv.writer(out);keys=['id','time','lat','lon','depth_km','magnitude','magnitude_type','territory','municipality_id','url'];w.writerow(['run_id','selection',*keys])
            for part in ['current','previous','comparison']:
                for e in r[part]['events']:
                    row=[r['run_id'],part,*[e.get(k) for k in keys]];w.writerow(["'"+x if isinstance(x,str) and x.startswith(('=','+','-','@','\t','\r')) else x for x in row])
            body,mime=out.getvalue(),'text/csv'
        return Response(body,mimetype=mime,headers={'Content-Disposition':f'attachment; filename=risklab-ign-{key[:12]}-{kind}'})
