"""Future single-instance Render process supervisor. Does not deploy any service."""
import os
import signal
import subprocess
import sys
import time

if __name__=='__main__':
    from .store import database_path
    path=database_path()
    if os.environ.get('RENDER') and not path.startswith('/var/data/'):
        raise SystemExit('Configure persistent /var/data disk and RISKLAB_CONTINUOUS_DB before starting on Render.')
    children=[];stopping=False
    def stop(*args):
        global stopping
        stopping=True
        for child in children:
            if child.poll() is None:child.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        children.append(subprocess.Popen([sys.executable,'-m','risklab_next.continuous.worker']))
        children.append(subprocess.Popen([sys.executable,'-m','gunicorn','server:app','--bind','0.0.0.0:'+str(int(os.environ.get('PORT','10000'))),'--workers','2','--timeout','60']))
        while not stopping:
            if any(child.poll() is not None for child in children):raise RuntimeError('Collector or web process exited; restart the whole service.')
            time.sleep(1)
    finally:
        stop()
        for child in children:
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
