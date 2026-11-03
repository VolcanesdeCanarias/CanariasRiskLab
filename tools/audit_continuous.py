"""Private local integrity audit and SQLite online backup; never exports HTTP session data publicly."""
import argparse,gzip,hashlib,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.continuous.store import Store
from risklab_next.continuous.connectors import fingerprint
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database');p.add_argument('--backup',type=Path);a=p.parse_args();s=Store(a.database)
    if a.backup:
        if a.backup.exists():raise SystemExit('No se sobrescribe una copia existente.')
        a.backup.parent.mkdir(parents=True,exist_ok=True)
        with s.connect() as source,sqlite3.connect(a.backup) as target:source.backup(target)
        a.backup.chmod(0o600)
    with s.connect() as db:
        db.execute('BEGIN')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise SystemExit('Integridad SQLite no válida')
        raw_count=version_count=0
        for row in db.execute('SELECT raw_sha256,raw_gzip FROM acquisitions WHERE raw_gzip IS NOT NULL'):
            if hashlib.sha256(gzip.decompress(row['raw_gzip'])).hexdigest()!=row['raw_sha256']:raise SystemExit('Respuesta original alterada')
            raw_count+=1
        for row in db.execute('SELECT hash,body FROM revisions'):
            body=json.loads(row['body']);original={k:v for k,v in body.items() if k not in {'id','source','territory','municipality_id','revision_hash'}}
            if fingerprint(original)!=row['hash']:raise SystemExit('Versión alterada')
            version_count+=1
    print(json.dumps(dict(sqlite='ok',raw_responses_verified=raw_count,versions_verified=version_count,backup_created=bool(a.backup))))
