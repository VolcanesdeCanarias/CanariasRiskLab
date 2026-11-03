"""TEST ONLY collector scenarios. No network acquisition and no production simulated data."""
import os,sys,importlib.util
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
spec=importlib.util.spec_from_file_location('next_fixtures',Path(__file__).with_name('serve.py'));fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
server=fixture.server
from risklab_next.continuous.connectors import Batch,event,iso,AcquisitionError
store=server.app.blueprints['risklab_next'].continuous_store
step=0

def ingest(mode):
    global step
    step+=1;now=datetime.now(timezone.utc)+timedelta(microseconds=step)
    store.heartbeat(now)
    for source in ['IGN','USGS']:
        owner='test-only';assert store.claim(source,owner,now,force=True)
        if mode=='error' and source=='IGN':store.fail(source,now,now,owner,AcquisitionError('http_error',403));continue
        events=[]
        if source=='IGN' and mode!='empty':
            e=event('es2026fixturea',iso(now-timedelta(hours=1)),28.27,-16.64,10,2 if mode=='revised' else 1,'mbLg','TEST ONLY · synthetic fixture',{'test_only':True,'magnitude':2 if mode=='revised' else 1});events=[e]
            # Fixed source time across polls, allowing true identical version checks.
            e['time']=iso(base-timedelta(hours=1))
            if mode in ['new','revised']:events.append(event('es2026fixtureb',iso(base-timedelta(minutes=20)),28.6,-17.85,20,2,'mbLg','TEST ONLY · La Palma',{'test_only':True}))
        b=Batch(source,events,iso(now-timedelta(days=10 if source=='IGN' else 30)),iso(now),b'TEST ONLY synthetic HTTP response','https://example.invalid/test-only')
        store.ingest(b,now,now,owner)
base=datetime.now(timezone.utc);ingest('initial')
@server.app.post('/__test__/continuous/<mode>')
def continuous_scenario(mode):
    if mode not in ['initial','new','revised','error','empty']:return {},400
    ingest(mode);return {'test_only':True}
if __name__=='__main__':
    from unittest.mock import patch
    with patch.object(server,'fetch_ign_html',side_effect=fixture.fixture.fixture_html),patch.object(server.requests,'get',side_effect=fixture.fixture.usgs_response):
        server.app.run(host='127.0.0.1',port=int(os.environ.get('TEST_PORT','8770')),threaded=True)
