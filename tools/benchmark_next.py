"""Optional local benchmark using a real candidate catalogue; never ingests it.

Usage: python tools/benchmark_next.py --events /path/to/Earth/data/events.json
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.api import analyze
p=argparse.ArgumentParser();p.add_argument('--events',required=True);args=p.parse_args()
raw=json.loads(Path(args.events).read_text())
events=[{'id':e['id'],'time':e['time'],'lat':e['lat'],'lon':e['lon'],'depth_km':e['depth'],'magnitude':e['mag'],'territory':'Tenerife'} for e in raw]
end=max(datetime.fromisoformat(e['time'].replace('Z','+00:00')) for e in events)+timedelta(seconds=1)
snapshot={'snapshot_id':'local-candidate-benchmark','source':'IGN','quality':{'state':'available','count':len(events),'checked_at':end.isoformat()},'events':events}
params={'from':(end-timedelta(days=1)).isoformat(),'until':end.isoformat()}
timings=[]
for _ in range(30):
    start=time.perf_counter();result=analyze(snapshot,params);timings.append((time.perf_counter()-start)*1000)
print(json.dumps({'catalogue_records':len(events),'data':'real historical candidate; provenance not validated','runs':len(timings),'median_ms':sorted(timings)[len(timings)//2],'max_ms':max(timings),'selected_count':result['statistics']['count'],'python':sys.version.split()[0]},indent=2))
