"""Standalone, escaped human report and allowlisted evidence package."""
import csv
import hashlib
from html import escape
import io
import json
from pathlib import Path
import zipfile


def selected_csv(run):
    out=io.StringIO();writer=csv.writer(out)
    keys=['id','time','lat','lon','depth_km','magnitude','magnitude_type','source','url']
    writer.writerow(['run_id','period']+keys+['horizontal_error_km','depth_error_km','magnitude_error'])
    def safe(v):return "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v
    for period in ['previous','current']:
        for event in run['periods'][period]['events']:
            values=[run['run_id'],period]+[event.get(k) for k in keys]+[event['uncertainty'][k] for k in ['horizontal_km','depth_km','magnitude']]
            writer.writerow([safe(v) for v in values])
    return out.getvalue()


def report_html(run):
    esc=lambda v:escape(str(v))
    c=run['context'];m=run['manifest'];current=run['periods']['current'];previous=run['periods']['previous']
    def claims(items):return ''.join('<li>'+esc((str(x['year'])+' · '+x.get('name','Referencia documental')+'. ' if x.get('year') else '')+x['claim'])+' <small>['+esc(', '.join(x['sources']))+']</small></li>' for x in items)
    sources=''.join(f'<li id="{esc(s["id"])}"><a rel="noopener noreferrer" href="{esc(s["url"])}">{esc(s["title"])}</a> · consulta {esc(s["consulted_at"])}</li>' for s in c['sources'])
    params=esc(json.dumps(run['parameters'],ensure_ascii=False,indent=2));statistics=esc(json.dumps({k:v for k,v in run.items() if k in ['comparison','spatial','magnitude_sensitivity','territorial_context']},ensure_ascii=False,indent=2))
    annual=''.join(f'<tr><td>{row["year"]}</td><td>{row["returned_records"]}</td><td>{row["catalogue_records_in_study_area"]}</td><td>{esc(row["state"])}</td></tr>' for row in run['annual_series'])
    territory=''.join('<li>'+esc(t['name'])+' · '+esc(t['quality'])+' ['+esc(', '.join(t['sources']))+']</li>' for t in c['territory'])
    limits=''.join('<li>'+esc(v)+'</li>' for v in m['limitations']+c['limits']+run['explanation']['cautions'])
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>RiskLab · Informe reproducible</title>
<style>body{{max-width:960px;margin:40px auto;padding:20px;font:15px/1.65 system-ui;color:#243e42}}h1,h2{{color:#145e62}}code,pre{{font-size:11px;overflow-wrap:anywhere;white-space:pre-wrap}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:7px;border-bottom:1px solid #ccdcd7}}.notice{{background:#fff4dc;padding:16px;border-left:4px solid #aa7827}}a{{color:#146970}}@media print{{body{{margin:0}}h2{{break-after:avoid}}}}</style>
<h1>{esc(c['name'])} · Cuaderno de investigación</h1><p>Volcanes de Canarias · RiskLab NEXT · Informe descriptivo, sin predicción ni alerta oficial.</p>
<p class="notice">{esc(c['study_area_note'])} La completitud instrumental de ComCat no está acreditada: un cero de registros no demuestra inactividad.</p>
<h2>1. Evidencia y reproducibilidad</h2><p>Ejecución: <code>{esc(run['run_id'])}</code><br>Dataset: <code>{esc(run['dataset_hash'])}</code><br>Método: {esc(run['method'])}<br>Código SHA256: <code>{esc(run['method_source_sha256'])}</code><br>Contexto SHA256: <code>{esc(run['context_hash'])}</code></p><pre>{params}</pre>
<h2>2. Observaciones históricas consultadas</h2><p>Fuente: USGS ComCat. {esc(m['verification']['geojson_rows'])} filas reconciliadas entre GeoJSON, CSV y count. Consulta desde {esc(m['coverage']['from'])} hasta {esc(m['coverage']['until'])} (excluido); no acredita cobertura de detección continua.</p><p><a href="{esc(m['query_url'])}">Consulta original</a> · <a href="{esc(m['licence']['url'])}">Política de datos</a></p>
<h2>3. Comparación y patrón espacial</h2><table><tr><th>Periodo</th><th>Desde / hasta excluido</th><th>Días</th><th>Registros</th><th>Tasa del catálogo/año</th></tr><tr><td>Previo</td><td>{esc(previous['from'])} / {esc(previous['until'])}</td><td>{previous['duration_days']}</td><td>{esc(previous['count'])}</td><td>{esc(previous['catalogue_rate_per_year'])}</td></tr><tr><td>Actual</td><td>{esc(current['from'])} / {esc(current['until'])}</td><td>{current['duration_days']}</td><td>{esc(current['count'])}</td><td>{esc(current['catalogue_rate_per_year'])}</td></tr></table><p>{esc(run['explanation']['text'])}</p><p>No se publica p-valor ni significación: faltan comprobaciones de completitud y estabilidad de detección. Vecino más próximo: distancia epicentral esférica, no hipocentral; celdas no son clusters físicos.</p><pre>{statistics}</pre>
<h2>4. Geología, estructuras e historia eruptiva</h2><ul>{claims(c['geology'])}{claims(c['history'])}</ul><h3>Contraste documental sísmico</h3><ul>{claims(c['documented_observations'])}</ul>
<h2>5. Contexto territorial e infraestructuras</h2><ul>{territory}</ul><p>No se calcula exposición, vulnerabilidad, peligrosidad ni riesgo. La referencia hospitalaria carece de geometría acreditada en este paquete: no se inventan coordenadas ni distancias.</p>
<h2>6. Serie anual del catálogo filtrado</h2><table><tr><th>Año</th><th>Seleccionados</th><th>Registros en área</th><th>Lectura</th></tr>{annual}</table>
<h2>7. Incertidumbre y límites</h2><p>Número de registros con error informado en selección actual (no son valores de error): <code>{esc(json.dumps(current['uncertainty_available']))}</code>. La ausencia de error no equivale a cero.</p><ul>{limits}</ul><p>Señales pendientes: {esc('; '.join(c['missing_signals']))}</p>
<h2>8. Fuentes documentales</h2><ol>{sources}</ol><p>Contratos/ecuaciones: method-spec.json en el paquete. Para repetir: <code>python3 tools/reproduce_research.py run.json</code> en la versión de código cuyo SHA coincida. ZIP incluye originales y checksums; la revisión humana sigue siendo necesaria.</p></html>'''


def evidence_zip(run,folder):
    files={'report.html':report_html(run).encode(),'run.json':json.dumps(run,ensure_ascii=False,indent=2).encode(),'events.csv':selected_csv(run).encode()}
    spec={'method':run['method'],'code_sha256':run['method_source_sha256'],'rates':'count / duration_days * 365.25','ratio':'current rate / previous rate; null if previous count is zero or outside coverage','spatial':'Spherical haversine R=6371.0088km, median of nearest epicentral neighbour; no depth correction. Fixed grid origin = study_bounds west/south, degrees as declared.','inference':'No p-value/causal inference without validated detection completeness','windows':'UTC half-open [from,until), previous period immediately preceding with identical duration'}
    files['method-spec.json']=json.dumps(spec,ensure_ascii=False,indent=2).encode()
    for name,meta in run['manifest']['files'].items():
        if name not in {'catalogue.geojson','catalogue.csv','count.txt'}:raise ValueError('Activo no exportable')
        data=(Path(folder)/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Origen histórico modificado')
        files['originals/'+name]=data
    files['checksums.json']=json.dumps({name:hashlib.sha256(body).hexdigest() for name,body in files.items()},indent=2).encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,body in files.items():
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,body)
    return out.getvalue()
