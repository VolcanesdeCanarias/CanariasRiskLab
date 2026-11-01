"""Offline regression tests. Synthetic responses exist only in these tests."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

import requests
import server


NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
HEADERS = ["Evento", "Fecha", "Hora UTC (*)", "Latitud", "Longitud",
           "Profundidad (km)", "Int. max.", "Magnitud", "Tipo Mag.", "Localización", "Más info"]


def table(rows=(), empty_message=None):
    head = "<tr>" + "".join(f"<th>{h}</th>" for h in HEADERS) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows)
    if empty_message is not None:
        body += f'<tr><td colspan="11">{empty_message}</td></tr>'
    return f"<html><table>{head}{body}</table></html>"


def row(**changes):
    values = dict(zip(HEADERS, ["es2026abc", "01/11/2026", "11:00:00", "28.2", "-16.6",
                               "10.0", "", "1.5", "mbLg", "ICOD DE LOS VINOS.ITF", ""]))
    values.update(changes)
    return list(values.values())


def response(text="", data=None, status=200, content_type="text/html;charset=UTF-8"):
    result = Mock(status_code=status, text=text, headers={"Content-Type": content_type})
    result.json.return_value = data
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


def usgs_feature(lat=28.2, lon=-16.6):
    return {"type": "Feature", "id": "us-test", "geometry": {"type": "Point", "coordinates": [lon, lat, 10]},
            "properties": {"mag": 1.5, "place": "Canarias", "time": (NOW - timedelta(hours=1)).timestamp() * 1000}}


def feed(features):
    return {"type": "FeatureCollection", "features": features,
            "metadata": {"status": 200, "count": len(features), "generated": NOW.timestamp() * 1000}}


class P0Tests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(server, "now_utc", return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.client = server.app.test_client()

    def parse(self, html):
        with patch.object(server, "fetch_ign_html", return_value=html):
            return server.parse_ign_canarias()

    def test_public_assets_remain_accessible(self):
        for path in ["/", *["/" + p for p in server.PUBLIC_FILES]]:
            with self.subTest(path=path):
                result = self.client.get(path)
                self.assertEqual(result.status_code, 200)
                result.close()

    def test_internal_files_and_traversal_are_not_public(self):
        for path in ["/server.py", "/requirements.txt", "/render.yaml", "/.git/config", "/.git/HEAD",
                     "/.env", "/tests/test_p0.py", "/README.md", "/static/server.py",
                     "/static/.git/config", "/../server.py", "/%2e%2e/server.py",
                     "/%2egit/config", "/foo/../index.html", "/index.html/extra"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_automatic_static_route(self):
        self.assertNotIn("static", server.app.view_functions)

    def test_valid_ign_preserves_event_contract(self):
        result = self.parse(table([row()]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["magnitud"], 1.5)
        self.assertEqual(result[0]["source"], "IGN_live")
        self.assertEqual(result[0]["municipio"], "Icod de los Vinos")
        self.assertEqual(result[0]["datetime_iso"], "2026-11-01T11:00:00+00:00")

    def test_integer_and_decimal_comma_magnitudes(self):
        for magnitude in ["2", "1,5", "-0.2"]:
            with self.subTest(magnitude=magnitude):
                self.assertEqual(self.parse(table([row(Magnitud=magnitude)]))[0]["magnitud"], float(magnitude.replace(",", ".")))

    def test_intensity_is_not_misread_as_magnitude(self):
        result = self.parse(table([row(**{"Int. max.": "2.0", "Magnitud": "1.2"})]))
        self.assertEqual(result[0]["magnitud"], 1.2)

    def test_explicit_empty_ign_is_success(self):
        html = table(empty_message="No se han encontrado terremotos.")
        self.assertEqual(self.parse(html), [])
        with patch.object(server, "fetch_ign_html", return_value=html):
            result = self.client.get("/api/ign-canarias")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["data_status"]["state"], "empty")
        self.assertEqual(result.json["count"], 0)

    def test_ambiguous_empty_or_changed_pages_fail(self):
        for html in ["", "<html>Access denied</html>", "<table><tr><td>01/11/2026</td></tr></table>", table()]:
            with self.subTest(html=html), self.assertRaises(server.DataAcquisitionError):
                self.parse(html)

    def test_invalid_event_rejects_entire_catalogue(self):
        for changes in [{"Latitud": "nan"}, {"Longitud": "181"}, {"Profundidad (km)": ""},
                        {"Magnitud": "inf"}, {"Fecha": "31/02/2026"}, {"Evento": ""},
                        {"Hora UTC (*)": "18:00:00"}]:
            with self.subTest(changes=changes), self.assertRaises(server.DataAcquisitionError):
                self.parse(table([row(Evento="es2026first"), row(**changes)]))

    def test_truncated_row_fails(self):
        with self.assertRaises(server.DataAcquisitionError):
            self.parse(table([row()[:5]]))

    def test_duplicate_events_fail_instead_of_inflating_indicators(self):
        with self.assertRaises(server.DataAcquisitionError):
            self.parse(table([row(), row()]))

    def test_stale_ign_catalogue_fails(self):
        with self.assertRaises(server.DataAcquisitionError) as raised:
            self.parse(table([row(Fecha="01/10/2026")]))
        self.assertEqual(raised.exception.code, "stale_data")

    def test_contradictory_empty_message_fails(self):
        with self.assertRaises(server.DataAcquisitionError):
            self.parse(table([row()], empty_message="No hay eventos"))

    def test_http_errors_keep_upstream_status_without_leaking_response(self):
        for source, url in [("IGN", "/api/ign-canarias"), ("USGS", "/api/usgs-canarias")]:
            for status in [403, 429, 500, 503]:
                with self.subTest(source=source, status=status), patch.object(server.requests, "get", return_value=response(status=status)):
                    result = self.client.get(url)
                self.assertEqual(result.status_code, 502)
                self.assertEqual(result.json["data_status"]["upstream_status"], status)
                self.assertIsNone(result.json["count"])
                self.assertEqual(result.json["error_code"], "http_error")

    def test_timeout_and_connection_failures(self):
        for url in ["/api/ign-canarias", "/api/usgs-canarias"]:
            for failure, status in [(requests.Timeout(), 504), (requests.ConnectionError(), 502)]:
                with self.subTest(url=url, failure=type(failure)), patch.object(server.requests, "get", side_effect=failure):
                    result = self.client.get(url)
                self.assertEqual(result.status_code, status)
                self.assertFalse(result.json["ok"])
                self.assertEqual(result.json["data_status"]["state"], "unavailable")

    def test_wrong_ign_content_type(self):
        with patch.object(server.requests, "get", return_value=response(table([row()]), content_type="application/json")):
            self.assertEqual(self.client.get("/api/ign-canarias").status_code, 502)

    def test_failed_ign_never_calls_indicators(self):
        for url in ["/api/risklab-bundle", "/api/risklab-clusters"]:
            with self.subTest(url=url), patch.object(server, "fetch_ign_html", return_value="<html>Maintenance</html>"), \
                    patch.object(server, "compute_risklab_index") as index, \
                    patch.object(server, "auto_interpretation") as interpretation, \
                    patch.object(server, "build_focus_ranking") as focuses:
                result = self.client.get(url)
                self.assertEqual(result.status_code, 502)
                self.assertFalse(result.json["ok"])
                index.assert_not_called()
                interpretation.assert_not_called()
                focuses.assert_not_called()
                self.assertIsNone(result.json["focus_summary"]["focos_detectados"])
                if "risklab_index" in result.json:
                    self.assertIsNone(result.json["risklab_index"])
                    self.assertIsNone(result.json["interpretation"])
                    self.assertIsNone(result.json["territorial"])
                    self.assertTrue(result.json["official_status"])

    def test_bundle_valid_empty_differs_from_failure(self):
        with patch.object(server, "fetch_ign_html", return_value=table(empty_message="No hay terremotos")):
            result = self.client.get("/api/risklab-bundle")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["data_status"]["state"], "empty")
        # P0 does not change the experimental indicator methodology, including its empty input value.
        self.assertEqual(result.json["risklab_index"]["value"], 9.0)

    def test_success_bundle_retains_all_existing_features(self):
        with patch.object(server, "fetch_ign_html", return_value=table([row()])):
            result = self.client.get("/api/risklab-bundle?island=Tenerife&municipio=Icod%20de%20los%20Vinos")
        self.assertEqual(result.status_code, 200)
        for key in ["summary", "risklab_index", "interpretation", "depth_profile", "compare", "acceleration",
                    "baseline", "regime", "migration", "anomaly", "territorial", "serie", "official_status",
                    "municipal_stats", "municipal_ranking", "selected_municipality", "municipal_clusters",
                    "infra_expuestas", "focus_clusters", "focus_temporal_clusters", "focus_summary", "enjambres", "instrumentation"]:
            self.assertIn(key, result.json)
        self.assertEqual(result.json["data_status"]["state"], "available")
        self.assertEqual(len(result.json["ign_eventos"]), 1)

    def test_unexpected_failure_does_not_leak_details(self):
        with patch.object(server, "parse_ign_canarias", side_effect=RuntimeError("private-path secret-token")):
            result = self.client.get("/api/risklab-bundle")
        self.assertEqual(result.status_code, 500)
        self.assertNotIn("private-path", result.get_data(as_text=True))

    def usgs(self, data):
        with patch.object(server.requests, "get", return_value=response(data=data, content_type="application/json")):
            return server.fetch_usgs_canarias()

    def test_valid_usgs_with_events_and_without_regional_events(self):
        self.assertEqual(len(self.usgs(feed([usgs_feature()]))), 1)
        self.assertEqual(self.usgs(feed([usgs_feature(lat=60, lon=-150)])), [])
        self.assertEqual(self.usgs(feed([])), [])

    def test_usgs_bad_json(self):
        res = response(content_type="application/json")
        res.json.side_effect = ValueError("invalid json")
        with patch.object(server.requests, "get", return_value=res):
            result = self.client.get("/api/usgs-canarias")
        self.assertEqual(result.status_code, 502)
        self.assertEqual(result.json["error_code"], "invalid_response")

    def test_usgs_malformed_catalogue_fails(self):
        invalid = [None, {}, {"type": "FeatureCollection", "features": []}, feed([{}])]
        bad_count = feed([]); bad_count["metadata"]["count"] = 1; invalid.append(bad_count)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(server.DataAcquisitionError):
                self.usgs(value)

    def test_usgs_stale_feed_fails_even_when_empty(self):
        data = feed([])
        data["metadata"]["generated"] = (NOW - timedelta(hours=3)).timestamp() * 1000
        with self.assertRaises(server.DataAcquisitionError) as raised:
            self.usgs(data)
        self.assertEqual(raised.exception.code, "stale_data")

    def test_usgs_invalid_event_does_not_become_zero_events(self):
        for coordinates in [["nan", 28, 10], [-16, 91, 10], [-16, 28], [-16, 28, None]]:
            feature = usgs_feature(); feature["geometry"]["coordinates"] = coordinates
            with self.subTest(coordinates=coordinates), self.assertRaises(server.DataAcquisitionError):
                self.usgs(feed([feature]))

    def test_scientific_functions_are_unchanged_from_audited_commit(self):
        audited = subprocess.check_output(["git", "show", "647bec9544e2bc2fbee36731e850cca60b685c2a:server.py"], text=True)
        current = Path(server.__file__).read_text()
        def functions(source):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        before, after = functions(audited), functions(current)
        names = [name for name in before if name.startswith(("compute_", "detect_", "build_", "cluster_level_"))]
        names += ["depth_profile", "serie_temporal", "auto_interpretation", "grouped_summary_by_island",
                  "municipality_score", "municipality_ranking", "municipality_summary", "exposed_infrastructures",
                  "events_in_hours", "events_in_days", "classify_island", "infer_municipality"]
        for name in names:
            with self.subTest(function=name):
                self.assertEqual(before[name], after[name])


if __name__ == "__main__":
    unittest.main()
