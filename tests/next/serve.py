"""Review server: fixtures and scenario endpoints are confined to this test file."""
import sys
import os
import importlib.util
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('browser_fixture',Path(__file__).resolve().parents[1]/'browser/serve.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
server=fixture.server
store=server.app.blueprints['risklab_next'].snapshot_store
originals=store.adapters.copy()

@server.app.post('/__test__/next-scenario/<source>/<mode>')
def scenario(source,mode):
    def fail():raise server.DataAcquisitionError(source,'http_error',source+': HTTP 403 (test fixture)',403)
    if source not in originals or mode not in ['ok','empty','error']:return {},400
    store.adapters[source]=originals[source] if mode=='ok' else (lambda:[]) if mode=='empty' else fail
    store.cache.pop(source,None)
    return {'test_only':True}

if __name__=='__main__':
    with patch.object(server,'fetch_ign_html',side_effect=fixture.fixture_html),patch.object(server.requests,'get',side_effect=fixture.usgs_response):
        server.app.run(host='127.0.0.1',port=int(os.environ.get('TEST_PORT','8766')),threaded=True)
