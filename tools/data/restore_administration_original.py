"""Restore private local original or download the official public WFS response."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args()
    if args.output.exists():raise SystemExit('Output exists; choose a new path.')
    m=json.loads((ROOT/'risklab_next/data/observatory/ign-administration/manifest.json').read_text());private=ROOT/'.risklab-next/source-originals/ign-administration'
    if (private/'manifest.json').exists():
        meta=json.loads((private/'manifest.json').read_text());parts=[]
        for item in meta['original_gzip_parts']:
            raw=(private/item['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise SystemExit('Original chunk mismatch')
            parts.append(raw)
        raw=gzip.decompress(b''.join(parts))
    else:
        print('Downloading large original from official IGN WFS; local public geometry is already included.')
        r=requests.get(m['source_url'],timeout=90);r.raise_for_status();raw=r.content
    if hashlib.sha256(raw).hexdigest()!=m['original_sha256']:raise SystemExit('Original differs: provider may have updated its response. No existing evidence changed.')
    args.output.write_bytes(raw);print('Exact original WFS response verified:',args.output)
