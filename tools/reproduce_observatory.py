"""Reproduce an IGN multinsular run locally, without network access."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.api import Geography
from risklab_next.observatory import analyze
from tools.reproduce_research import equivalent

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_json');args=parser.parse_args()
    original=json.loads(Path(args.run_json).read_text());p=original['parameters'];params={**p,'from':p['from_']}
    actual=analyze(params,Geography())
    if not equivalent(original,actual):raise SystemExit('NO COINCIDE: comprueba código, originales IGN, capa administrativa y parámetros.')
    print(json.dumps(dict(verified=True,run_id=actual['run_id'],current=actual['current']['count'],previous=actual['previous']['count'],comparison=actual['comparison']['count']),indent=2))
