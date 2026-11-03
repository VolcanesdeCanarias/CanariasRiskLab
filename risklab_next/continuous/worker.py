"""Server-side scheduler, independent from browsers and guarded by SQLite leases."""
import argparse
from datetime import timedelta
import json
import logging
import os
from pathlib import Path
import shutil
import threading
import uuid
from .connectors import CONFIG,IGN,USGS,AcquisitionError,clock
from .store import Store

class Worker:
    def __init__(self,store,connectors=None,now=clock):self.store=store;self.connectors=connectors or {'IGN':IGN(),'USGS':USGS()};self.now=now;self.owner=uuid.uuid4().hex
    def tick(self):
        self.store.heartbeat(self.now());results=[]
        for source,connector in self.connectors.items():
            started=self.now()
            if not self.store.claim(source,self.owner,started):continue
            try:
                if Path(self.store.path).stat().st_size>5_000_000_000 or shutil.disk_usage(Path(self.store.path).parent).free<100_000_000:raise AcquisitionError('storage_budget_exceeded')
                for attempt in range(2):
                    attempt_started=self.now()
                    try:
                        batch=connector.fetch(self.now());self.store.attempt(source,attempt_started,self.now());break
                    except AcquisitionError as e:
                        self.store.attempt(source,attempt_started,self.now(),e)
                        if attempt or e.code not in {'connection_error','timeout'} and not (e.status and 500<=e.status<=599):raise
                results.append(self.store.ingest(batch,started,self.now(),self.owner))
            except Exception as error:
                self.store.fail(source,started,self.now(),self.owner,error);results.append(dict(source=source,state='unavailable',error=getattr(error,'code','internal_error')))
            self.store.heartbeat(self.now())
        return results
    def run(self,stop=None):
        stop=stop or threading.Event()
        while not stop.is_set():
            try:
                results=self.tick()
                if results:logging.info('Acquisition summaries: %s',json.dumps(results))
            except Exception:logging.error('Collector storage/runtime error; heartbeat will expire. Check private server logs and disk.')
            stop.wait(5)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');args=p.parse_args()
    from ..api import Geography
    w=Worker(Store(geography=Geography()));logging.basicConfig(level=logging.INFO)
    if args.once:print(json.dumps(w.tick()))
    else:w.run()
