"""Replay a public continuous observation capture without network or private SQLite."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.continuous.analysis import analyze_capture
from tools.reproduce_research import equivalent
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_json');args=p.parse_args();r=json.loads(Path(args.run_json).read_text());params={**r['parameters'],'from':r['parameters']['from_']};actual=analyze_capture(r['inputs'],params)
    if not equivalent(actual,r):raise SystemExit('NO COINCIDE: revisa versión del método, parámetros y captura. No se modifica la evidencia.')
    print(json.dumps(dict(verified=True,run_id=r['run_id'],source=r['source'],available_records=r['current']['observed_count'],coverage=r['current']['coverage']['state']),indent=2))
