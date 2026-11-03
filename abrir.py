"""Local review launcher; never binds a public interface."""
import os
import threading
import webbrowser

if __name__ == '__main__':
    try:
        from server import app
    except ModuleNotFoundError:
        raise SystemExit('Instala las dependencias: python3 -m pip install -r requirements.txt')
    if os.environ.get('RISKLAB_COLLECTOR', '1') != '0':
        from risklab_next.continuous.worker import Worker
        collector = Worker(app.blueprints['risklab_next'].continuous_store)
        threading.Thread(target=collector.run, name='risklab-collector', daemon=True).start()
    port = int(os.environ.get('RISKLAB_PORT', '8787'))
    url = f'http://127.0.0.1:{port}/next/?mode=continuous'
    print(f'Canarias RiskLab NEXT · revisión local: {url}', flush=True)
    if not os.environ.get('RISKLAB_NO_BROWSER'):
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    app.run(host='127.0.0.1', port=port, debug=False)
