"""Reproducible descriptive tools over an explicit, versioned observation capture."""
from collections import Counter,defaultdict
from datetime import timedelta
import math
from pathlib import Path
import hashlib
from .connectors import CONFIG,iso,parse_time,number,fingerprint

METHOD='continuous-catalogue-descriptive/1.0'
WARNING='Observaciones publicadas, no estimación de actividad real, anomalía, peligro ni alerta. Cobertura nominal no acredita completitud instrumental.'

def merge_intervals(intervals):
    out=[]
    for a,b in sorted((parse_time(a),parse_time(b)) for a,b in intervals):
        if not a<b:continue
        if out and a<=out[-1][1]:out[-1]=(out[-1][0],max(b,out[-1][1]))
        else:out.append((a,b))
    return out

def coverage(a,b,intervals):
    seconds=sum(max(0,(min(b,y)-max(a,x)).total_seconds()) for x,y in intervals);total=(b-a).total_seconds()
    return dict(state='covered_nominally' if seconds>=total-.001 else 'partial' if seconds>0 else 'no_coverage',fraction=round(min(1,seconds/total),8),meaning='Ventanas solicitadas al proveedor; no completitud de detección ni garantía de publicación inmediata.')

def analyze_capture(capture,p):
    source=capture['source'];intervals=merge_intervals(capture['intervals']);end=parse_time(capture['as_of']) if capture.get('as_of') else None
    preset=p.get('period','24h');days={'24h':1,'7d':7,'30d':30,'1y':365}
    if preset not in {*days,'history','custom'}:raise ValueError('Periodo desconocido')
    if preset=='custom':a,b=parse_time(p['from']),parse_time(p['until'])
    elif end:
        b=end;a=min([x for x,y in intervals]+[parse_time(e['time']) for e in capture['events']],default=b-timedelta(days=1)) if preset=='history' else b-timedelta(days=days[preset])
        if a==b:a=b-timedelta(seconds=1)
    else:
        b=parse_time(capture['evaluated_at']);a=b-timedelta(days=days.get(preset,1))
    if not a<b or (b-a)>timedelta(days=3660):raise ValueError('Intervalo inválido o excesivo')
    territory=p.get('territory','Canarias');other=p.get('compare','La Palma');allowed=capture['territories']
    if territory not in allowed or other not in allowed:raise ValueError('Territorio desconocido')
    low=number(p.get('min_mag',-10));dmin=number(p.get('min_depth',-10));dmax=number(p.get('max_depth',1000));kind=p.get('mag_type','all')
    if not -10<=low<=10 or not -10<=dmin<=dmax<=1000 or kind not in {'all','mbLg','mblg','mb','ML','ml','Mw','mw','M','m'}:raise ValueError('Filtros inválidos')
    duration=b-a;previous=a-duration
    def matches(e):return ((e['magnitude'] is None and low==-10) or e['magnitude'] is not None and e['magnitude']>=low) and (kind=='all' or (e['magnitude_type'] or '').lower()==kind.lower()) and dmin<=e['depth_km']<=dmax
    events=[e for e in capture['events'] if e.get('presence_state','returned')!='not_returned' and matches(e)]
    unconfirmed=[e for e in capture['events'] if e.get('presence_state')=='not_returned' and matches(e) and a<=parse_time(e['time'])<b and (territory=='Canarias' or e['territory']==territory)]
    def selection(t,x,y):
        values=[e for e in events if x<=parse_time(e['time'])<y and (t=='Canarias' or e['territory']==t)]
        cov=coverage(x,y,intervals)
        return dict(count=len(values) if cov['state']=='covered_nominally' else None,observed_count=len(values),coverage=cov,events=values)
    current=selection(territory,a,b);prev=selection(territory,previous,a);comparison=selection(other,a,b)
    step_days=max(1,math.ceil(duration.total_seconds()/86400/180));bins=defaultdict(list);groups=Counter()
    for e in current['events']:
        k=int((parse_time(e['time'])-a).total_seconds()//(step_days*86400));bins[k].append(e);groups[(math.floor((e['lon']+19)/.1),math.floor((e['lat']-26)/.1),k)]+=1
    series=[]
    for k in range(math.ceil(duration.total_seconds()/86400/step_days)):
        es=bins[k];by_kind={}
        for e in es:
            if e['magnitude'] is not None and e['magnitude_type']:
                s=e['magnitude_type'];by_kind[s]=max(by_kind.get(s,e['magnitude']),e['magnitude'])
        series.append(dict(start=iso(a+timedelta(days=k*step_days)),until=iso(min(b,a+timedelta(days=(k+1)*step_days))),observed_count=len(es),coverage=coverage(a+timedelta(days=k*step_days),min(b,a+timedelta(days=(k+1)*step_days)),intervals)['state'],max_magnitude_by_type=by_kind))
    depth=Counter();magnitudes=Counter()
    for e in current['events']:
        depth['<5' if e['depth_km']<5 else '5–15' if e['depth_km']<15 else '15–30' if e['depth_km']<30 else '≥30']+=1
        if e['magnitude'] is not None:magnitudes[(e['magnitude_type'] or 'sin escala',math.floor(e['magnitude']*2)/2)]+=1
    compact={**capture,'events':[e for e in capture['events'] if previous<=parse_time(e['time'])<b]}
    result=dict(schema='risklab.continuous-run/1',method=METHOD,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source=source,source_status=capture['status'],last_success=capture['last_success'],acquisition_id=capture['acquisition_id'],
        parameters=dict(period=preset,from_=iso(a),until=iso(b),previous_from=iso(previous),duration_days=duration.total_seconds()/86400,territory=territory,compare=other,min_mag=low,min_depth=dmin,max_depth=dmax,mag_type=kind),
        current=current,previous=prev,comparison=comparison,series=series,depth_distribution=dict(depth),magnitude_distribution=[dict(scale=k[0],lower=k[1],count=v) for k,v in sorted(magnitudes.items())],
        groups=[dict(bounds=[-19+x*.1,26+y*.1,-19+(x+1)*.1,26+(y+1)*.1],time_bin=k,count=v) for (x,y,k),v in sorted(groups.items())],
        group_note='Agrupación descriptiva por celdas de 0,1° y bloques UTC; no clusters físicos ni focos activos.',warning=WARNING,
        excluded_unconfirmed=len(unconfirmed),unconfirmed_events=unconfirmed,
        publication_latency='No conocida. Fecha de evento, primera detección local y revisión de origen son conceptos distintos.',inference_allowed=False,inputs=compact)
    result['run_id']=fingerprint(result);return result
