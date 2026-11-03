"""Read-only analytical APIs; refresh queues work, never calls upstream in HTTP handlers."""
import csv
import gzip
import io
import json
import os
import hashlib
from pathlib import Path
from flask import jsonify,request,Response,send_from_directory
from .connectors import CONFIG,clock,iso,parse_time,fingerprint
from .store import Store
from .analysis import analyze_capture,merge_intervals

ROOT=Path(__file__).resolve().parents[2]

def capture(store,source,now):
    with store.connect() as db:
        db.execute('BEGIN')
        status=next(s for s in store.status(now,db)['sources'] if s['source']==source)
        intervals=[(r['coverage_from'],r['coverage_until']) for r in db.execute("SELECT coverage_from,coverage_until FROM acquisitions WHERE source=? AND state IN ('available','empty') ORDER BY checked_at",(source,))]
        rows=db.execute('SELECT r.body,o.first_seen,o.last_seen,o.presence_state,o.last_absence_acquisition FROM observations o JOIN revisions r ON r.source=o.source AND r.event_id=o.event_id AND r.hash=o.current_hash WHERE o.source=?',(source,)).fetchall()
        if len(rows)>20000:raise ValueError('Más de 20000 versiones actuales: requiere almacenamiento analítico ampliado; no se trunca silenciosamente')
        latest_id=status['latest']['id'] if status['latest'] else None
        if latest_id:
            original=db.execute('SELECT raw_gzip,raw_sha256 FROM acquisitions WHERE id=?',(latest_id,)).fetchone()
            if hashlib.sha256(gzip.decompress(original['raw_gzip'])).hexdigest()!=original['raw_sha256']:raise ValueError('Stored HTTP integrity failure')
        changed={r['event_id']:r['kind'] for r in db.execute('SELECT event_id,kind FROM changes WHERE acquisition_id=?',(latest_id,))}
        events=[]
        for row in rows:
            e=json.loads(row['body'])
            original={k:v for k,v in e.items() if k not in {'id','source','territory','municipality_id','revision_hash'}}
            if fingerprint(original)!=e['revision_hash']:raise ValueError('Stored event integrity failure')
            if store.geography.locate(e['lon'],e['lat'])!=(e['territory'],e['municipality_id']):raise ValueError('Geography normalization mismatch')
            e.update(first_seen=row['first_seen'],last_seen=row['last_seen'],latest_change=changed.get(e['source_id']),presence_state=row['presence_state'],last_absence_acquisition=row['last_absence_acquisition']);events.append(e)
        recent=[dict(r) for r in db.execute('SELECT id,checked_at,state,error_code,http_status,raw_sha256,count,new_count,revised_count,duplicate_count,response_generated_at,integrity_json FROM acquisitions WHERE source=? ORDER BY checked_at DESC,rowid DESC LIMIT 20',(source,))]
    intervals=[(iso(a),iso(b)) for a,b in merge_intervals(intervals)]
    return dict(source=source,as_of=status['latest']['coverage_until'] if status['latest'] else None,status={k:status[k] for k in ['state','last_error','last_http','last_attempt','failures']},last_success=status['last_success'],acquisition_id=status['latest']['id'] if status['latest'] else None,
        evaluated_at=iso(now),intervals=intervals,events=sorted(events,key=lambda e:(e['time'],e['source_id'])),territories=['Canarias',*store.geography.views,'Entorno marítimo'],recent_acquisitions=recent,
        lineage='Immutable source/event/version tuples; source-record fields public, original HTTP bodies private.',geography_sha256=store.geography.sha256,normalization=dict(method='inherited-crs84-municipal/1.1',quality='inherited_unverified_current_validity',note='Asignación terrestre por polígonos heredados, sin isla más próxima para registros marinos. No certificación jurídica ni dato territorial publicado por el proveedor sísmico.'))

def register_continuous(bp,old_store,geography):
    path=os.environ.get('RISKLAB_CONTINUOUS_DB') or str(Path(old_store.database).parent/'continuous.sqlite')
    store=Store(path,geography);bp.continuous_store=store
    @bp.get('/next/continuous.mjs')
    @bp.get('/next/continuous.css')
    def continuous_assets():return send_from_directory(ROOT/'next',request.path.rsplit('/',1)[-1])
    @bp.get('/api/v1/continuous/status')
    def continuous_status():return jsonify(store.status())
    @bp.get('/api/v1/continuous/health')
    def continuous_health():
        alive=store.status()['worker_alive']
        return jsonify(collector_alive=alive),200 if alive else 503
    @bp.post('/api/v1/continuous/refresh/<source>')
    def continuous_refresh(source):
        if source not in CONFIG:return jsonify(error='Fuente desconocida'),404
        if not store.status()['worker_alive']:return jsonify(error='Recolector no activo. Arranca abrir.py o el proceso worker; no se consulta el proveedor desde el navegador.'),503
        if not store.queue(source,clock()):return jsonify(error='Actualización limitada: esperar el mínimo de 60 segundos, la adquisición en curso o el backoff indicado por la fuente.'),429
        return jsonify(state='queued',source=source),202
    @bp.get('/api/v1/continuous/events/<source>/<ident>')
    def continuous_event(source,ident):
        if source not in CONFIG or len(ident)>80:return jsonify(error='No encontrado'),404
        e=store.event(source,ident);return (jsonify(e),200) if e else (jsonify(error='No encontrado'),404)
    @bp.get('/api/v1/continuous/analysis')
    def continuous_analysis():
        source=request.args.get('source','IGN')
        if source not in CONFIG:return jsonify(error='Fuente desconocida'),400
        try:data=capture(store,source,clock())
        except (ValueError,TypeError,KeyError,OSError):return jsonify(error='Integridad o capacidad del almacén no verificable; no se calcula actividad'),503
        params={k:request.args[k] for k in ['period','from','until','territory','compare','min_mag','min_depth','max_depth','mag_type'] if k in request.args}
        signature=fingerprint(dict(capture={k:v for k,v in data.items() if k!='evaluated_at'},parameters=params,method_sha256=hashlib.sha256((Path(__file__).with_name('analysis.py')).read_bytes()).hexdigest()))
        with store.connect() as db:cached=db.execute('SELECT run_id FROM continuous_cache WHERE key=?',(signature,)).fetchone()
        if cached:
            try:saved=store.read_run(cached['run_id'])
            except (ValueError,OSError):return jsonify(error='Captura almacenada no verificable'),503
            if saved is not None:return jsonify(saved)
        try:r=analyze_capture(data,params)
        except (ValueError,TypeError,KeyError,OverflowError):return jsonify(error='Parámetros inválidos o presupuesto de consulta excedido; no se calcula ausencia de actividad.'),400
        # Immutable compressed private records; no HTTP raw-response export.
        if Path(store.path).stat().st_size>5_000_000_000:return jsonify(error='Presupuesto de almacenamiento agotado. Se conserva la evidencia anterior; requiere intervención del operador.'),503
        with store.connect() as db:
            db.execute('INSERT OR IGNORE INTO continuous_runs VALUES (?,?)',(r['run_id'],gzip.compress(json.dumps(r,ensure_ascii=False,allow_nan=False).encode(),mtime=0)))
            db.execute('INSERT OR REPLACE INTO continuous_cache VALUES (?,?)',(signature,r['run_id']))
        return jsonify(r)
    @bp.get('/api/v1/continuous/runs/<key>/<kind>')
    def continuous_export(key,kind):
        try:r=store.read_run(key)
        except (ValueError,OSError):return jsonify(error='Captura almacenada no verificable'),503
        if r is None or kind not in {'run.json','events.csv'}:return jsonify(error='No encontrado'),404
        if r['current']['coverage']['state']=='no_coverage':return jsonify(error='Sin cobertura: no se exporta como catálogo vacío'),422
        if kind=='run.json':body,mime=json.dumps(r,ensure_ascii=False,indent=2),'application/json'
        else:
            out=io.StringIO();w=csv.writer(out);keys=['source','source_id','revision_hash','time','source_updated_at','publication_at','first_seen','last_seen','lat','lon','depth_km','magnitude','magnitude_type','territory'];w.writerow(['run_id','selection',*keys])
            for part in ['current','previous','comparison']:
                for e in r[part]['events']:
                    vals=[r['run_id'],part,*[e.get(k) for k in keys]];w.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v for v in vals])
            body,mime=out.getvalue(),'text/csv'
        return Response(body,mimetype=mime,headers={'Content-Disposition':f'attachment; filename=risklab-continuous-{key[:12]}-{kind}'})
    @bp.post('/api/v1/continuous/runs/<key>/ask')
    def continuous_ask(key):
        if request.content_length is None or request.content_length>2048:return jsonify(error='Pregunta demasiado grande'),413
        try:r=store.read_run(key)
        except (ValueError,OSError):return jsonify(error='Captura almacenada no verificable'),503
        if not r:return jsonify(error='Ejecución no encontrada'),404
        data=request.get_json();q=data.get('question') if isinstance(data,dict) else None
        if not isinstance(q,str) or not q.strip() or len(q)>500:return jsonify(error='Pregunta inválida'),400
        s=q.lower();p=r['parameters']
        if any(x in s for x in ['alerta','erup','predic','peligro','riesgo','anomali','anomalí','aceler','régimen']):text='Estas herramientas descriptivas no permiten inferir anomalías, cambios de régimen, erupciones o alertas.';state='abstained'
        elif any(x in s for x in ['compara','registro','sismic','observa']):text=f"Fuente {r['source']}, {p['from_']} → {p['until']} (excluido). {p['territory']}: {r['current']['observed_count']} registros disponibles ({r['current']['coverage']['state']}); {p['compare']}: {r['comparison']['observed_count']}. Previo: {r['previous']['observed_count']} disponibles ({r['previous']['coverage']['state']}). "+r['warning'];state='answered'
        elif any(x in s for x in ['falta','cobertura','latencia','fuente','retras','actual']):text=f"Última consulta válida: {r['last_success']}. Estado capturado: {r['source_status']['state']}. "+r['publication_latency']+' Falta acreditar completitud de detección, incertidumbres no publicadas y otras señales. '+r['warning'];state='answered'
        else:text='Admite consultas sobre registros comparados, cobertura, fuentes y actualización de esta ejecución. No es IA generativa.';state='unsupported'
        return jsonify(state=state,text=text,run_id=key,source=r['source'],acquisition_id=r['acquisition_id'],source_url=CONFIG[r['source']]['url'],engine='deterministic evidence tools, no LLM')
