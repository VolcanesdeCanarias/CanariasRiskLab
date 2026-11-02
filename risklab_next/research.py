"""Versioned, evidence-bound research case. No predictions or inferred alert levels."""
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import math
import re
from pathlib import Path
import statistics
import unicodedata

from flask import jsonify, request, Response

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/research'
METHOD='catalogue-rates-spatial/1.0'
RADIUS_KM=6371.0088


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def date(value):
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Se requiere zona horaria UTC explícita')
    return d.astimezone(timezone.utc)


def finite(value):
    n=float(value)
    if not math.isfinite(n):raise ValueError('Número no finito')
    return n


def load_dataset(directory=None):
    folder=Path(directory or DATA/'usgs-tenerife-2000-2026')
    m=json.loads((folder/'manifest.json').read_text())
    if set(m['files'])!={'catalogue.geojson','catalogue.csv','count.txt'}:raise ValueError('Manifiesto no reconocido')
    for name,meta in m['files'].items():
        raw=(folder/name).read_bytes()
        if len(raw)!=meta['bytes'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Integridad histórica no válida')
    raw=json.loads((folder/'catalogue.geojson').read_text()); rows=list(csv.DictReader(io.StringIO((folder/'catalogue.csv').read_text())))
    if raw.get('type')!='FeatureCollection' or raw['metadata']['status']!=200:raise ValueError('Respuesta histórica inválida')
    n=int((folder/'count.txt').read_text())
    if len(raw['features'])!=n or len(rows)!=n or n>=10000:raise ValueError('Catálogo truncado/inconsistente')
    csv_by_id={row['id']:row for row in rows}
    if len(csv_by_id)!=n:raise ValueError('IDs CSV repetidos')
    events=[];seen=set();coverage=m['coverage'];start,end=date(coverage['from']),date(coverage['until']);w,s,e,north=coverage['bounds']
    for feature in raw['features']:
        p,g=feature['properties'],feature['geometry'];ident=feature['id'];row=csv_by_id[ident]
        if ident in seen or feature['type']!='Feature' or g['type']!='Point' or p['type']!='earthquake' or p['net']!='us':raise ValueError('Registro no admitido')
        seen.add(ident);lon,lat,depth=map(finite,g['coordinates']);time=datetime.fromtimestamp(finite(p['time'])/1000,timezone.utc)
        if not (w<=lon<=e and s<=lat<=north and -10<=depth<=1000 and start<=time<end):raise ValueError('Registro fuera del contrato')
        if date(row['time'])!=time or any(abs(a-finite(row[k]))>1e-7 for a,k in [(lat,'latitude'),(lon,'longitude'),(depth,'depth')]):raise ValueError('CSV y GeoJSON discrepan')
        mag=None if p['mag'] is None else finite(p['mag'])
        if (mag is None)!=(row['mag']=='') or (mag is not None and (abs(mag-finite(row['mag']))>1e-7 or not -10<=mag<=10)):raise ValueError('Magnitud inconsistente')
        if (p.get('magType') or '')!=row['magType']:raise ValueError('Tipo magnitud inconsistente')
        errors={k:None if row[col]=='' else finite(row[col]) for k,col in [('horizontal_km','horizontalError'),('depth_km','depthError'),('magnitude','magError')]}
        if any(v is not None and v<0 for v in errors.values()):raise ValueError('Incertidumbre inválida')
        events.append({'id':ident,'source':'USGS ComCat histórico','time':time.isoformat(),'lat':lat,'lon':lon,'depth_km':depth,
                       'magnitude':mag,'magnitude_type':p.get('magType'),'place':p.get('place') or ident,'territory':'Área de estudio Tenerife/mar',
                       'uncertainty':errors,'source_review_status':p['status'],'url':p['url'],
                       'depth_reference':'Profundidad publicada por ComCat; sin transformación vertical al MDT.'})
    if seen!=set(csv_by_id):raise ValueError('IDs históricos inconsistentes')
    m['dataset_hash']=digest(m)
    return {'manifest':m,'events':sorted(events,key=lambda e:(e['time'],e['id']))}


def haversine(a,b):
    lat1,lat2=map(math.radians,[a['lat'],b['lat']]);dl=math.radians(b['lon']-a['lon']);dp=lat2-lat1
    v=math.sin(dp/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2
    return RADIUS_KM*2*math.atan2(math.sqrt(max(0,min(1,v))),math.sqrt(max(0,1-v)))


def spatial(events,step,bounds):
    cells={};west,south=bounds[:2]
    for e in events:
        col,row=math.floor((e['lon']-west)/step),math.floor((e['lat']-south)/step)
        cells[(col,row)]=cells.get((col,row),0)+1
    grid=[{'id':f'{x}:{y}','count':count,'bounds':[west+x*step,south+y*step,west+(x+1)*step,south+(y+1)*step]} for (x,y),count in sorted(cells.items())]
    distances=[min(haversine(a,b) for j,b in enumerate(events) if i!=j) for i,a in enumerate(events)] if len(events)>1 else []
    return {'grid_degrees':step,'origin':[west,south],'occupied_cells':len(grid),'cells':grid,
            'nearest_neighbour_median_km':round(statistics.median(distances),9) if distances else None,
            'nearest_neighbour_n':len(distances),'colocated_coordinates':len(events)-len({(e['lat'],e['lon']) for e in events}),
            'interpretation':'Descriptores de localizaciones publicadas. Las celdas no son clusters físicos; no hay test de significación ni modelo de peligro.'}


def run_analysis(dataset,context,parameters=None,geography=None):
    p=parameters or {};m=dataset['manifest'];coverage=m['coverage'];start=date(p.get('from','2004-01-01T00:00:00Z'));until=date(p.get('until','2005-01-01T00:00:00Z'))
    if not start<until or until-start>timedelta(days=3660):raise ValueError('Periodo positivo y máximo de 3660 días requerido')
    minimum=finite(p.get('min_mag',2));magtype=p.get('mag_type','mblg');step=finite(p.get('grid_degrees',.05))
    if not -10<=minimum<=10 or magtype not in {'all','mblg','mb','m'} or step not in {.025,.05,.1}:raise ValueError('Parámetro de análisis no admitido')
    bounds=context['study_bounds'];w,s,e,n=bounds
    eligible=[x for x in dataset['events'] if w<=x['lon']<=e and s<=x['lat']<=n and x['magnitude'] is not None and x['magnitude']>=minimum and (magtype=='all' or (x['magnitude_type'] or '').lower()==magtype)]
    duration=until-start;previous=start-duration
    def period(a,b):
        covered=date(coverage['from'])<=a and b<=date(coverage['until'])
        events=[x for x in eligible if a<=date(x['time'])<b] if covered else []
        days=(b-a).total_seconds()/86400
        return {'from':a.isoformat(),'until':b.isoformat(),'duration_days':days,'coverage':'queried_catalogue; detection_completeness_unknown' if covered else 'outside_query',
                'count':len(events) if covered else None,'catalogue_rate_per_year':len(events)/days*365.25 if covered else None,
                'magnitude_median':statistics.median(x['magnitude'] for x in events) if events and len({x['magnitude_type'] for x in events})==1 and events[0]['magnitude_type'] not in {None,'m'} else None,
                'depth_median_km':statistics.median(x['depth_km'] for x in events) if events else None,
                'uncertainty_available':{key:sum(x['uncertainty'][key] is not None for x in events) for key in ['horizontal_km','depth_km','magnitude']},'events':events}
    current,prior=period(start,until),period(previous,start)
    if len(current['events'])>2000:raise ValueError('Presupuesto espacial excedido: máximo 2000 registros por ejecución')
    both=current['count'] is not None and prior['count'] is not None
    ratio=current['catalogue_rate_per_year']/prior['catalogue_rate_per_year'] if both and prior['count'] else None
    years=[]
    for year in range(date(coverage['from']).year,date(coverage['until']).year):
        vals=[x for x in eligible if date(x['time']).year==year]
        source=[x for x in dataset['events'] if date(x['time']).year==year]
        area=[x for x in source if w<=x['lon']<=e and s<=x['lat']<=n]
        years.append({'year':year,'returned_records':len(vals),'catalogue_records_in_study_area':len(area),'source_records_in_query_box':len(source),
                      'state':'records_selected' if vals else 'filtered_empty' if area else 'empty_study_area' if source else 'no_records_returned_not_proof_of_inactivity'})
    geo=[]
    if geography:
        counts={}
        for event in current['events']:
            island,mun=geography.locate(event['lon'],event['lat']);key=(island,mun);counts[key]=counts.get(key,0)+1
        geo=[{'territory':k[0],'municipality_id':k[1],'records':v,'quality':'polygon assignment from inherited boundaries, current validity unverified'} for k,v in sorted(counts.items(),key=lambda item:str(item[0]))]
    sensitivity=[]
    for threshold in sorted({minimum,minimum+.5,minimum+1}):
        if threshold<=10:sensitivity.append({'min_mag':threshold,'current_count':sum(x['magnitude']>=threshold for x in current['events']) if current['count'] is not None else None,'previous_count':sum(x['magnitude']>=threshold for x in prior['events']) if prior['count'] is not None else None})
    text=('Periodo fuera de la ventana consultada: no se calcula actividad.' if current['count'] is None else
          f"USGS devuelve {current['count']} registros para el periodo actual y {prior['count'] if prior['count'] is not None else 'un periodo previo sin cobertura'} para el previo. Son registros del catálogo, no una medida completa de actividad.")
    if ratio is not None:text+=f' La razón de tasas publicadas es {ratio:.3f}, con duraciones iguales de {current["duration_days"]:g} días.'
    result={'schema':'risklab.research-run/1','method':METHOD,'method_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dataset_hash':m['dataset_hash'],'context_hash':digest(context),'geography_sha256':getattr(geography,'sha256',None),'geography_method_sha256':hashlib.sha256((ROOT/'api.py').read_bytes()).hexdigest(),
            'parameters':{'case_id':context['case_id'],'from':start.isoformat(),'until':until.isoformat(),'min_mag':minimum,'mag_type':magtype,'grid_degrees':step,'study_bounds':bounds},
            'state':'available' if current['count'] is not None else 'no_coverage','periods':{'current':current,'previous':prior},
            'comparison':{'catalogue_rate_ratio':ratio,'inference_allowed':False,'p_value':None,'reason':'Completitud y estabilidad de detección no acreditadas; no se prueba un cambio de actividad geofísica.'},
            'annual_series':years,'spatial':spatial(current['events'],step,bounds) if current['count'] is not None else None,
            'magnitude_sensitivity':sensitivity,'territorial_context':geo,
            'explanation':{'text':text,'kind':'deterministic evidence-bound interpretation','evidence':['periods.current','periods.previous','comparison','dataset_hash'],
                           'cautions':['El umbral de consulta no es una estimación de magnitud de completitud.','El documento IGN describe actividad regional que ComCat puede omitir; no concluir quietud en años sin registros.','Proximidad espacial no atribuye origen volcánico ni actividad al sistema.','No se ha validado un modelo de exposición, vulnerabilidad, peligro o riesgo.']},
            'context':context,'manifest':m}
    result['run_id']=digest(result)
    return result


def answer(question,run):
    q=''.join(c for c in unicodedata.normalize('NFD',question.lower()) if unicodedata.category(c)!='Mn')
    if len(question)>500:raise ValueError('Pregunta demasiado larga')
    if any(x in q for x in ['predec','predic','va a erup','erupcionara','evacua','alerta','causa','por que']):
        return {'state':'abstained','text':'No puedo deducir causas, predicciones eruptivas, alertas o instrucciones de emergencia con este análisis. Consulta las fuentes oficiales y una evaluación humana.','evidence':['comparison.reason']}
    routes=[(['tasa','cambio','periodo','recuento'],'rates'),(['espaci','patron','celd','vecino'],'spatial'),(['cobertura','2016','incertid','faltan'],'coverage'),(['geolog','historia','eruptiv','estructura'],'geology'),(['territor','infraestructura','hospital','riesgo'],'territory')]
    intent='territory' if any(w in q for w in ['infraestruct','hospital','territor','riesgo']) else next((intent for words,intent in routes if any(w in q for w in words)),None)
    if any(place in q for place in ['la palma','el hierro','la gomera','gran canaria','lanzarote','fuerteventura','la graciosa']):
        return {'state':'unsupported_scope','text':'Esta ejecución corresponde al caso Tenerife/Teide–Pico Viejo y su caja marina de estudio. No hay una investigación histórica implementada para el territorio solicitado.','evidence':['parameters.case_id','parameters.study_bounds']}
    if intent in {'rates','spatial'} and (re.search(r'\d',q) or any(word in q for word in ['hoy','ahora','reciente'])):
        return {'state':'unsupported_scope','text':'La pregunta no cambia filtros ni periodos de esta ejecución histórica. Ajusta el formulario y ejecuta de nuevo. Periodo actual: '+run['periods']['current']['from']+' → '+run['periods']['current']['until']+' (excluido).','evidence':['parameters','periods.current']}
    if intent=='rates':text='Área de estudio Tenerife/mar, no perímetro del volcán. Periodo actual '+run['periods']['current']['from']+' → '+run['periods']['current']['until']+' (excluido). '+run['explanation']['text'];evidence=['parameters','periods.current','periods.previous','comparison']
    elif intent=='spatial':
        s=run['spatial'];text='No hay cobertura espacial para la selección.' if s is None else f"La selección ocupa {s['occupied_cells']} celdas de {s['grid_degrees']} grados. Mediana de distancia al vecino: {s['nearest_neighbour_median_km']} km. Es geometría de localizaciones publicadas, no detección de focos físicos.";evidence=['spatial']
    elif intent=='coverage':text='La consulta USGS es verificable, pero su completitud instrumental y estabilidad temporal no están acreditadas. Un año sin registros no implica inactividad; IGN documenta sismicidad regional en 2016 y 2019. Los errores ausentes no equivalen a cero.';evidence=['manifest.limitations','context.documented_observations','periods.current.uncertainty_available']
    elif intent=='geology':text=' '.join(x['claim'] for x in run['context']['geology'])+' Las observaciones se asocian por caja de estudio, sin inferencia causal.';evidence=['context.geology','context.sources','parameters.study_bounds']
    elif intent=='territory':text='El contexto incluye el Parque Nacional del Teide y una referencia documental del Hospital Universitario de Canarias. Sus geometrías acreditadas no están incorporadas: no calculo exposición ni distancias a ubicaciones sin validar.';evidence=['context.territory','territorial_context']
    else:return {'state':'unsupported','text':'Esta primera asistencia admite consultas sobre tasas, patrones espaciales, cobertura, geología y contexto territorial. No utiliza un modelo generativo ni inventa respuestas.','evidence':[]}
    return {'state':'answered','intent':intent,'text':text,'evidence':evidence,'run_id':run['run_id'],'engine':'bounded deterministic tools, no LLM'}


def register_research(blueprint,store,geography):
    from .research_report import report_html, evidence_zip, selected_csv
    with store.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS research_runs (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    def read_run(key):
        with store.connect() as db:row=db.execute('SELECT body FROM research_runs WHERE id=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    @blueprint.get('/api/v1/research/cases')
    def cases():
        context=json.loads((DATA/'teide-context.json').read_text())
        try:
            d=load_dataset();state='available';meta=d['manifest']
        except (ValueError,KeyError,TypeError,OSError):state='unavailable';meta=None
        return jsonify({'case':context,'dataset_state':state,'manifest':meta,'implemented_territories':['Tenerife and study marine area'],'other_territories':'Navigation preserved; historical research case not implemented.'})
    @blueprint.get('/api/v1/research/catalogue')
    def catalogue():
        try:
            d=load_dataset()
            return jsonify({'events':d['events'],'manifest':d['manifest'],'state':'available'})
        except (ValueError,KeyError,TypeError,OSError):
            return jsonify({'state':'unavailable','error':'Catálogo histórico no verificado; no se calcula ausencia de actividad.'}),503
    @blueprint.post('/api/v1/research/runs')
    def run():
        if request.content_length is not None and request.content_length>4096:return jsonify({'error':'Consulta demasiado grande'}),413
        p=request.get_json()
        if not isinstance(p,dict):return jsonify({'error':'Objeto de parámetros requerido'}),400
        if p.get('case_id','teide-pico-viejo')!='teide-pico-viejo':return jsonify({'state':'not_implemented','error':'Caso histórico no implementado para ese territorio; el piloto es Tenerife/Teide–Pico Viejo.'}),404
        try:
            dataset=load_dataset();context=json.loads((DATA/'teide-context.json').read_text())
        except (ValueError,KeyError,TypeError,OSError):return jsonify({'state':'unavailable','error':'No se pudo verificar el dataset/caso histórico. No se calcula actividad.'}),503
        try:result=run_analysis(dataset,context,p,geography)
        except (ValueError,TypeError,OverflowError):return jsonify({'error':'Parámetros históricos inválidos o fuera de presupuesto'}),400
        with store.connect() as db:db.execute('INSERT OR IGNORE INTO research_runs VALUES (?,?)',(result['run_id'],json.dumps(result,ensure_ascii=False,allow_nan=False)))
        return jsonify(result)
    @blueprint.get('/api/v1/research/runs/<key>')
    def saved(key):
        r=read_run(key)
        return (jsonify(r),200) if r else (jsonify({'error':'Ejecución no encontrada'}),404)
    @blueprint.post('/api/v1/research/runs/<key>/ask')
    def ask(key):
        r=read_run(key)
        if not r:return jsonify({'error':'Ejecución no encontrada'}),404
        if request.content_length is not None and request.content_length>2048:return jsonify({'error':'Pregunta demasiado larga'}),413
        p=request.get_json();q=p.get('question') if isinstance(p,dict) else None
        if not isinstance(q,str) or not q.strip():return jsonify({'error':'Pregunta requerida'}),400
        try:return jsonify(answer(q,r))
        except ValueError:return jsonify({'error':'Pregunta demasiado larga'}),400
    @blueprint.get('/api/v1/research/runs/<key>/export/<kind>')
    def export(key,kind):
        r=read_run(key)
        if not r:return jsonify({'error':'Ejecución no encontrada'}),404
        if kind not in {'report.html','evidence.zip','run.json','events.csv'}:return jsonify({'error':'Formato no admitido'}),404
        if r['state']!='available':return jsonify({'error':'Fuera de cobertura: no se exporta como cero'}),422
        if kind=='report.html':body,mime=report_html(r),'text/html'
        elif kind=='run.json':body,mime=json.dumps(r,ensure_ascii=False,indent=2),'application/json'
        elif kind=='events.csv':body,mime=selected_csv(r),'text/csv'
        else:
            try:body,mime=evidence_zip(r,DATA/'usgs-tenerife-2000-2026'),'application/zip'
            except (ValueError,OSError):return jsonify({'error':'No se pudo verificar el paquete original de evidencias'}),503
        response=Response(body,mimetype=mime,headers={'Content-Disposition':f'attachment; filename=risklab-{key[:12]}-{kind}'})
        response.headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        return response
