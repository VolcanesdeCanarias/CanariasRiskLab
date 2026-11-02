"""Import a real, licensed IGN/CNIG geographic GeoTIFF for local review only.

Requires optional `python3 -m pip install rasterio`; never downloads or changes originals.
Output goes to ignored .risklab-next/terrain.json, not to public repository data.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab_next.terrain import validate_grid


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('geotiff');p.add_argument('--source-url',required=True);p.add_argument('--product',required=True)
    p.add_argument('--vertical-datum',required=True);p.add_argument('--resolution-m',required=True,type=float)
    p.add_argument('--output',default=str(Path(__file__).resolve().parents[1]/'.risklab-next/terrain.json'))
    p.add_argument('--side',type=int,default=129,choices=[65,129,257])
    args=p.parse_args()
    try:import rasterio
    except ImportError:raise SystemExit('Instala el importador opcional: python3 -m pip install rasterio')
    source=Path(args.geotiff)
    with rasterio.open(source) as ds:
        # No silent reprojection or orthometric/ellipsoidal transformation.
        if ds.crs is None or ds.crs.to_epsg()!=4326 or ds.transform.b or ds.transform.d:
            raise SystemExit('Se requiere GeoTIFF norte-arriba en EPSG:4326. Reproyecta explícitamente, conservando referencia y resolución.')
        if ds.transform.a<=0 or ds.transform.e>=0:raise SystemExit('Orientación no admitida')
        width,height=min(args.side,ds.width),min(args.side,ds.height)
        if width<2 or height<2:raise SystemExit('Malla insuficiente')
        # Nearest measured pixel only: no synthetic upsampling, zero fill, or smoothing.
        xs=[round(i*(ds.width-1)/(width-1)) for i in range(width)]
        ys=[round(i*(ds.height-1)/(height-1)) for i in range(height)]
        # Read selected one-pixel windows; bounded memory even for a large original.
        values=[]
        for row in ys:
            for col in xs:
                value=ds.read(1,window=rasterio.windows.Window(col,row,1,1),masked=True)[0,0]
                values.append(None if getattr(value,'mask',False) else float(value))
        x0,y0=ds.xy(ys[0],xs[0]);x1,y1=ds.xy(ys[-1],xs[-1])
    digest=hashlib.sha256()
    with source.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    data={'schema':'risklab.dem/1','width':width,'height':height,'bounds':[x0,y1,x1,y0],'values':values,
          'metadata':{'product':args.product,'source_url':args.source_url,'licence':'CC-BY-4.0',
                      'vertical_datum':args.vertical_datum,'source_resolution_m':args.resolution_m,
                      'imported_at':datetime.now(timezone.utc).isoformat(),'original_sha256':digest.hexdigest(),
                      'attribution':'Obra derivada de '+args.product+' · CC BY 4.0 ign.es',
                      'sampling':'Nearest source pixels; rows north to south; no upsampling. Triangles are visual interpolation only.'}}
    validate_grid(data)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(data,allow_nan=False))
    print('MDT importado localmente:',output,'· malla',width,'×',height,'· sin transformación vertical')


if __name__=='__main__':main()
