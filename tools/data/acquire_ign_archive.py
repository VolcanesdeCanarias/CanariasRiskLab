"""Public IGN portal pagination, exact bytes + query validation; no guessed FDSN endpoint."""
import requests,re,json,hashlib,gzip,concurrent.futures
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime,timezone
import argparse
parser=argparse.ArgumentParser(description='Archive the public IGN 2023–2024 query; never overwrite bundled evidence.')
parser.add_argument('output',type=Path);args=parser.parse_args();out=args.output
if out.exists():raise SystemExit('Use a new, empty output directory; existing evidence is immutable.')
out.mkdir(parents=True)
u='https://www.ign.es/web/ign/portal/sis-catalogo-terremotos/-/catalogo-terremotos/searchTerremoto'
p=dict(latMin=27,latMax=30,longMin=-19,longMax=-13,startDate='01/01/2023',endDate='31/12/2024',selIntensidad='N',selMagnitud='N',selProf='N',fases='no',intMin='0',intMax='8',magMin='0',magMax='8',profMin='',profMax='',cond='')
def get(index):
 params=({**p,'indice':index} if index else p); name=f'page-{index:05d}.html.gz'; cached=out/name
 if cached.exists():
  r=requests.Response();r.status_code=200;r._content=gzip.decompress(cached.read_bytes());r.url=requests.Request('GET',u,params=params).prepare().url
 else:r=requests.get(u,params=params,timeout=60);r.raise_for_status()
 s=BeautifulSoup(r.content,'html.parser');match=re.search(r'Se han encontrado\s+(\d+)\s+terremotos',s.get_text(' ',strip=True))
 if not match:raise ValueError('No validated total')
 for key in ('latMin','latMax','longMin','longMax','startDate','endDate'):
  el=s.find('input',id=lambda v:v and v.endswith('portlet_'+key))
  if not el or el.get('value')!=str(p[key]):raise ValueError('Query mismatch '+key)
 table=next(t for t in s.select('table') if 'Hora UTC' in t.text);rows=[[c.get_text(' ',strip=True) for c in tr.select('td')] for tr in table.select('tr')[1:]]
 original=r.content;name=f'page-{index:05d}.html.gz';(out/name).write_bytes(gzip.compress(original,mtime=0))
 return int(match[1]),rows,dict(file=name,url=r.url,original_sha256=hashlib.sha256(original).hexdigest(),compressed_sha256=hashlib.sha256((out/name).read_bytes()).hexdigest())
total,rows,meta=get(0);print('Total',total,'First',rows[0],flush=True);pages=[meta]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for n,rr,mm in pool.map(get,range(100,total+50,50)):
  if n!=total:raise ValueError('Catalogue changed during acquisition')
  rows+=rr;pages.append(mm);print(len(rows),'/',total,flush=True)
if len(rows)!=total or len({r[0] for r in rows})!=total:raise ValueError('Incomplete or duplicate')
(out/'rows.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
m=dict(schema='risklab.ign-archive/1',provider='Instituto Geográfico Nacional',citation='IGN. Catálogo de terremotos. https://doi.org/10.7419/162.03.2022',acquired_at=datetime.now(timezone.utc).isoformat(),coverage={'from':'2023-01-01T00:00:00+00:00','until':'2025-01-01T00:00:00+00:00','bounds':[-19,27,-13,30]},count=total,licence={'name':'CC BY 4.0 ign.es','url':'https://www.ign.es/web/ign/portal/politica-datos'},pages=pages,rows_sha256=hashlib.sha256((out/'rows.json').read_bytes()).hexdigest(),limitations=['Archivo de una consulta, no catálogo completo histórico del IGN.','Cobertura consultada no garantiza completitud de detección ni homogeneidad.','Profundidad y magnitud según publicación; incertidumbre no incluida en tabla.','Páginas adquiridas en un intervalo; no instantánea transaccional del proveedor.','No asociar proximidad a origen volcánico ni ausencia de registros a ausencia de actividad.'])
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print('COMPLETE',flush=True)
