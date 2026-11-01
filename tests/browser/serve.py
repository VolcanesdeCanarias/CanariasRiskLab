"""Local browser-test server only. Never imported by production server:app."""
import os
from pathlib import Path
import sys
from datetime import timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from test_p0 import row, table, response


def fixture_html():
    dt = server.now_utc() - timedelta(hours=1)
    rows = []
    for place, lat, lon in [("ICOD DE LOS VINOS.ITF", 28.27, -16.67),
                             ("EL PASO.ILP", 28.62, -17.86),
                             ("VALVERDE.IHI", 27.8, -17.95),
                             ("TINAJO.ILZ", 29.03, -13.68)]:
        for _ in range(4):
            rows.append(row(**{"Evento": f"es2026browser{len(rows)}", "Fecha": dt.strftime("%d/%m/%Y"),
                               "Hora UTC (*)": dt.strftime("%H:%M:%S"), "Latitud": lat,
                               "Longitud": lon, "Localización": place}))
    return table(rows)


def usgs_response(*args, **kwargs):
    dt = server.now_utc()
    data = {"type": "FeatureCollection", "metadata": {"status": 200, "count": 1,
            "generated": dt.timestamp() * 1000}, "features": [{"type": "Feature",
            "id": "us-browser-test", "geometry": {"type": "Point", "coordinates": [-16.67, 28.27, 10]},
            "properties": {"mag": 1.5, "place": "Browser test fixture", "time": dt.timestamp() * 1000}}]}
    return response(data=data, content_type="application/json")


@server.app.route("/__test__/ready")
def ready():
    return {"test_server": True}


@server.app.route("/__test__/empty-bundle")
def empty_bundle():
    with patch.object(server, "fetch_ign_html", return_value=table(empty_message="No hay terremotos")):
        return server.api_risklab_bundle()


if __name__ == "__main__":
    with patch.object(server, "fetch_ign_html", side_effect=fixture_html), \
            patch.object(server.requests, "get", side_effect=usgs_response):
        server.app.run(host="127.0.0.1", port=int(os.environ.get("TEST_PORT", "8765")), threaded=False)
