"""Publish only seismic table content; keep original portal session HTML private."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup

def prepare(originals,output):
    if output.exists():raise ValueError('Output must be new; never overwrite evidence')
    m=json.loads((originals/'manifest.json').read_text());pages=[];allrows=[]
    for entry in m['pages']:
        z=(originals/entry['file']).read_bytes();raw=gzip.decompress(z)
        if hashlib.sha256(z).hexdigest()!=entry['compressed_sha256'] or hashlib.sha256(raw).hexdigest()!=entry['original_sha256']:raise ValueError('Original hash mismatch')
        soup=BeautifulSoup(raw,'html.parser');table=next(t for t in soup.select('table') if 'Hora UTC' in t.text)
        rows=[[c.get_text(' ',strip=True) for c in tr.select('td')] for tr in table.select('tr')[1:]]
        criteria={key:soup.find('input',id=lambda s:s and s.endswith('portlet_'+key))['value'] for key in ['latMin','latMax','longMin','longMax','startDate','endDate']}
        pages.append(dict(source_file=entry['file'],source_url=entry['url'],original_sha256=entry['original_sha256'],criteria=criteria,total=m['count'],headers=[c.get_text(' ',strip=True) for c in table.select('tr')[0].select('th')],rows=rows));allrows.extend(rows)
    if allrows!=json.loads((originals/'rows.json').read_text()) or len(allrows)!=m['count'] or len({r[0] for r in allrows})!=m['count']:raise ValueError('Extract and original disagree')
    output.mkdir(parents=True)
    (output/'extracted-tables.json').write_text(json.dumps(dict(schema='risklab.public-ign-tables/1',pages=pages),ensure_ascii=False,separators=(',',':')))
    (output/'rows.json').write_bytes((originals/'rows.json').read_bytes())
    m['public_table_capture']={name:dict(bytes=(output/name).stat().st_size,sha256=hashlib.sha256((output/name).read_bytes()).hexdigest()) for name in ['extracted-tables.json','rows.json']}
    m['publication_note']='Full original portal HTML retained locally, excluded from public package because it contains anonymous session metadata. All seismic table fields, source URLs, original hashes and validated query criteria are included. Tables are a transparent extraction, not original full HTML.'
    (output/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));return m

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('public_output',type=Path);a=p.parse_args();m=prepare(a.originals,a.public_output);print('Prepared public seismic tables:',m['count'],'records; original HTML unchanged outside public package')
