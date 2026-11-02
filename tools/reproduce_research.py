"""Recompute a downloaded run from packaged official data. No network or LLM."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.api import Geography
from risklab_next.research import DATA, load_dataset, run_analysis


def equivalent(a,b):
    # JSON has one number category; browser round-trips may turn 2.0 into 2.
    # Booleans are not numbers and must not pass as zero/one.
    if isinstance(a,bool) or isinstance(b,bool):return type(a) is type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a==b
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return type(a) is type(b) and a==b


def main():
    p=argparse.ArgumentParser();p.add_argument('run_json');args=p.parse_args()
    original=json.loads(Path(args.run_json).read_text())
    context=json.loads((DATA/'teide-context.json').read_text())
    actual=run_analysis(load_dataset(),context,original['parameters'],Geography())
    if actual['run_id']!=original['run_id'] or not equivalent(actual,original):
        raise SystemExit('NO COINCIDE: comprueba versión de código, dataset, geografía, contexto y parámetros. No se modifica la evidencia.')
    print(json.dumps({'verified':True,'run_id':actual['run_id'],'current_count':actual['periods']['current']['count'],
                      'previous_count':actual['periods']['previous']['count'],'method':actual['method']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
