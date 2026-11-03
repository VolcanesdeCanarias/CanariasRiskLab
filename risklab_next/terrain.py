"""Optional local, documented numeric DEM. No fabricated or bundled elevations."""
import json
import math
from pathlib import Path
from urllib.parse import urlparse

MAX_BYTES = 3_000_000
MAX_SIDE = 257


def validate_grid(data):
    if data.get('schema') != 'risklab.dem/1':
        raise ValueError('Formato MDT desconocido')
    meta = data['metadata']
    if meta['licence'] != 'CC-BY-4.0' or urlparse(meta['source_url']).scheme != 'https' or urlparse(meta['source_url']).hostname not in {
        'www.ign.es', 'centrodedescargas.cnig.es', 'servicios.idee.es'}:
        raise ValueError('Procedencia/licencia MDT no admitida por este importador')
    if not all(isinstance(meta.get(k), str) and meta[k].strip() for k in
               ['product', 'vertical_datum', 'imported_at', 'attribution', 'original_sha256']):
        raise ValueError('Faltan metadatos de referencia y trazabilidad')
    if not math.isfinite(meta['source_resolution_m']) or meta['source_resolution_m'] <= 0:
        raise ValueError('Resolución de origen inválida')
    if len(meta['original_sha256']) != 64 or any(c not in '0123456789abcdef' for c in meta['original_sha256']):
        raise ValueError('Checksum original inválido')
    w, h = data['width'], data['height']
    if not all(isinstance(v, int) and 2 <= v <= MAX_SIDE for v in [w, h]):
        raise ValueError('Malla fuera del presupuesto de representación')
    b = data['bounds']
    if len(b) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in b) or not (-20 <= b[0] < b[2] <= -11 and 25 <= b[1] < b[3] <= 32):
        raise ValueError('MDT fuera del ámbito Canarias/Atlántico')
    if len(data['values']) != w*h:
        raise ValueError('Malla truncada')
    if not any(v is not None for v in data['values']):
        raise ValueError('MDT sin celdas observadas')
    if any(v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v) or not -500 <= v <= 5000) for v in data['values']):
        raise ValueError('Elevaciones terrestres inválidas')
    return data


def load_grid(path):
    target = Path(path)
    if not target.exists():
        return {'state':'not_configured', 'message':'Sin MDT numérico importado. Globo elipsoidal; WMS no es elevación.'}
    try:
        if target.stat().st_size > MAX_BYTES:
            raise ValueError('MDT excede el presupuesto local')
        data = validate_grid(json.loads(target.read_text()))
        return {'state':'documented_import', 'grid':data,
                'warning':'Malla de representación, no medición geodésica. Datum vertical de origen sin transformar al elipsoide; sin batimetría ni exageración vertical.'}
    except (ValueError, KeyError, TypeError, OSError) as error:
        return {'state':'invalid', 'message':'MDT rechazado: '+str(error)}
