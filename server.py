from flask import Flask, jsonify, send_from_directory, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os
import zipfile
import xml.etree.ElementTree as ET
import html

app = Flask(__name__, static_folder='.')

IGN_URL = "https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias"
KMZ_PATH = os.path.join(os.path.dirname(__file__), "catalogo.kmz")

CATALOG_START_DATE = datetime(2011, 1, 1, tzinfo=timezone.utc)

HISTORICAL_CACHE = {
    "loaded": False,
    "events": [],
    "error": None
}

ANALYTICS_CACHE = {}
CACHE_TTL_SECONDS = 300


# =========================
# Utilidades
# =========================
def clean_text(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_float(value):
    value = str(value).replace(",", ".").strip()
    return float(value)


def now_utc():
    return datetime.now(timezone.utc)


def parse_event_datetime(event):
    if event.get("datetime_iso"):
        try:
            dt = datetime.fromisoformat(event["datetime_iso"])
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    fecha = event.get("fecha")
    hora = event.get("hora_utc")
    if fecha and hora:
        try:
            dt = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def classify_island(lat, lon):
    if 28.00 <= lat <= 28.70 and -16.95 <= lon <= -16.05:
        return "Tenerife"
    if 28.35 <= lat <= 28.95 and -18.10 <= lon <= -17.60:
        return "La Palma"
    if 27.60 <= lat <= 27.90 and -18.30 <= lon <= -17.90:
        return "El Hierro"
    if 27.80 <= lat <= 28.25 and -15.90 <= lon <= -15.10:
        return "Gran Canaria"
    if 28.80 <= lat <= 29.35 and -14.10 <= lon <= -13.30:
        return "Lanzarote"
    if 28.00 <= lat <= 28.85 and -14.60 <= lon <= -13.80:
        return "Fuerteventura"
    if 28.00 <= lat <= 28.30 and -17.45 <= lon <= -16.90:
        return "La Gomera"
    return "Atlántico-Canarias"


def events_in_hours(eventos, hours):
    cutoff = now_utc() - timedelta(hours=hours)
    out = []
    for e in eventos:
        dt = parse_event_datetime(e)
        if dt and dt >= cutoff:
            out.append(e)
    return out


def events_in_days(eventos, days):
    cutoff = now_utc() - timedelta(days=days)
    out = []
    for e in eventos:
        dt = parse_event_datetime(e)
        if dt and dt >= cutoff:
            out.append(e)
    return out


def events_between_days_ago(eventos, start_days_ago, end_days_ago):
    now = now_utc()
    start_cut = now - timedelta(days=start_days_ago)
    end_cut = now - timedelta(days=end_days_ago)
    out = []
    for e in eventos:
        dt = parse_event_datetime(e)
        if dt and start_cut <= dt < end_cut:
            out.append(e)
    return out


def merge_recent_and_historical(recent_events, historical_events):
    by_id = {}
    for e in historical_events:
        key = e.get("id") or f'{e.get("fecha")}_{e.get("hora_utc")}_{e.get("lat")}_{e.get("lon")}'
        by_id[key] = e

    for e in recent_events:
        key = e.get("id") or f'{e.get("fecha")}_{e.get("hora_utc")}_{e.get("lat")}_{e.get("lon")}'
        by_id[key] = e

    merged = list(by_id.values())
    merged.sort(key=lambda x: parse_event_datetime(x) or datetime(1970, 1, 1, tzinfo=timezone.utc))
    return merged


def make_cache_key(prefix, island_name=None):
    return f"{prefix}:{island_name or 'Todas'}"


def cache_valid(entry, seconds=CACHE_TTL_SECONDS):
    if not entry:
        return False
    ts = entry.get("timestamp")
    if not ts:
        return False
    return (now_utc() - ts).total_seconds() < seconds


def get_or_build_cached(prefix, island_name, builder):
    key = make_cache_key(prefix, island_name)
    entry = ANALYTICS_CACHE.get(key)

    if cache_valid(entry):
        return entry["data"]

    data = builder()
    ANALYTICS_CACHE[key] = {
        "timestamp": now_utc(),
        "data": data
    }
    return data


# =========================
# IGN reciente
# =========================
def fetch_ign_html():
    headers = {"User-Agent": "Mozilla/5.0 CanariasRiskLab/1.0"}
    response = requests.get(IGN_URL, headers=headers, timeout=25)
    response.raise_for_status()
    return response.text


def parse_ign_canarias():
    html_text = fetch_ign_html()
    soup = BeautifulSoup(html_text, "html.parser")

    eventos = []

    rows = soup.select("tr")
    for row in rows:
        cells = [clean_text(td.get_text(" ", strip=True)) for td in row.find_all(["td", "th"])]
        if len(cells) < 8:
            continue

        joined = " ".join(cells)
        if not re.search(r"\d{2}/\d{2}/\d{4}", joined):
            continue
        if not re.search(r"\d{2}:\d{2}:\d{2}", joined):
            continue

        try:
            fecha_idx = next(i for i, c in enumerate(cells) if re.fullmatch(r"\d{2}/\d{2}/\d{4}", c))
            hora_idx = fecha_idx + 1

            fecha = cells[fecha_idx]
            hora = cells[hora_idx]
            lat = parse_float(cells[hora_idx + 1])
            lon = parse_float(cells[hora_idx + 2])
            profundidad = parse_float(cells[hora_idx + 3])

            mag = None
            tipo_mag = ""
            localizacion = ""

            for i in range(hora_idx + 4, min(len(cells), hora_idx + 8)):
                if re.fullmatch(r"\d+[.,]\d+", cells[i]):
                    mag = parse_float(cells[i])
                    if i + 1 < len(cells):
                        tipo_mag = cells[i + 1]
                        localizacion = " ".join(cells[i + 2:]).strip()
                    break

            if mag is None:
                continue

            try:
                dt = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                dt = None

            evento_id = ""
            for c in cells:
                if re.fullmatch(r"es\d+[a-z0-9]+", c.lower()):
                    evento_id = c
                    break

            eventos.append({
                "id": evento_id,
                "fecha": fecha,
                "hora_utc": hora,
                "datetime_iso": dt.isoformat() if dt else None,
                "lat": lat,
                "lon": lon,
                "profundidad_km": profundidad,
                "magnitud": mag,
                "tipo_magnitud": tipo_mag,
                "localizacion": localizacion or "Canarias",
                "isla": classify_island(lat, lon),
                "source": "IGN_live"
            })
        except Exception:
            pass

    if eventos:
        return eventos

    text = soup.get_text("\n", strip=True)
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]

    pattern = re.compile(
        r'^(es\d+[a-z0-9]+)?\s*'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'(\d{2}:\d{2}:\d{2})\s+'
        r'(-?\d+[.,]\d+)\s+'
        r'(-?\d+[.,]\d+)\s+'
        r'(\d+[.,]\d+)\s+'
        r'(?:\S+\s+)?'
        r'(\d+[.,]\d+)\s+'
        r'([A-Za-z]+)\s+'
        r'(.+)$'
    )

    for line in lines:
        m = pattern.match(line)
        if not m:
            continue

        try:
            evento_id = m.group(1) or ""
            fecha = m.group(2)
            hora = m.group(3)
            lat = parse_float(m.group(4))
            lon = parse_float(m.group(5))
            profundidad = parse_float(m.group(6))
            magnitud = parse_float(m.group(7))
            tipo_mag = m.group(8)
            localizacion = m.group(9).strip()

            try:
                dt = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                dt = None

            eventos.append({
                "id": evento_id,
                "fecha": fecha,
                "hora_utc": hora,
                "datetime_iso": dt.isoformat() if dt else None,
                "lat": lat,
                "lon": lon,
                "profundidad_km": profundidad,
                "magnitud": magnitud,
                "tipo_magnitud": tipo_mag,
                "localizacion": localizacion,
                "isla": classify_island(lat, lon),
                "source": "IGN_live"
            })
        except Exception:
            pass

    return eventos


# =========================
# USGS backend
# =========================
def fetch_usgs_canarias():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    data = requests.get(url, timeout=20).json()

    eventos = []

    for feature in data.get("features", []):
        coords = feature.get("geometry", {}).get("coordinates", [])
        props = feature.get("properties", {})

        if len(coords) < 3:
            continue

        lon, lat, depth = coords[:3]

        if not (26 <= lat <= 31 and -19 <= lon <= -12):
            continue

        timestamp_ms = props.get("time", 0) or 0

        eventos.append({
            "id": feature.get("id"),
            "lat": lat,
            "lon": lon,
            "profundidad_km": depth,
            "magnitud": props.get("mag", 0) or 0,
            "localizacion": props.get("place", "Canarias"),
            "datetime_iso": datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(),
            "source": "USGS",
            "isla": classify_island(lat, lon)
        })

    return eventos


# =========================
# KMZ histórico
# =========================
def parse_kmz_description(desc_html):
    desc = html.unescape(desc_html or "")
    pairs = re.findall(r'<td>(.*?)</td>\s*<td>(.*?)</td>', desc, flags=re.I | re.S)

    data = {}
    for k, v in pairs:
        key = clean_text(BeautifulSoup(str(k), "html.parser").get_text(" ", strip=True)).upper()
        val = clean_text(BeautifulSoup(v, "html.parser").get_text(" ", strip=True))
        data[key] = val

    return data


def load_historical_catalog():
    if HISTORICAL_CACHE["loaded"]:
        return HISTORICAL_CACHE["events"]

    if not os.path.exists(KMZ_PATH):
        HISTORICAL_CACHE["loaded"] = True
        HISTORICAL_CACHE["events"] = []
        HISTORICAL_CACHE["error"] = f"No se encontró {KMZ_PATH}"
        return []

    events = []

    try:
        with zipfile.ZipFile(KMZ_PATH, "r") as zf:
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise RuntimeError("No hay ningún KML dentro del KMZ")

            kml_name = kml_names[0]

            with zf.open(kml_name) as kml_file:
                context = ET.iterparse(kml_file, events=("end",))
                for _, elem in context:
                    tag = elem.tag.split("}")[-1]

                    if tag != "Placemark":
                        continue

                    try:
                        name_el = elem.find(".//{*}name")
                        desc_el = elem.find(".//{*}description")
                        coords_el = elem.find(".//{*}coordinates")

                        if desc_el is None or coords_el is None:
                            elem.clear()
                            continue

                        desc_data = parse_kmz_description(desc_el.text or "")
                        coords_text = clean_text(coords_el.text or "")
                        lon_str, lat_str = coords_text.split(",")[:2]

                        lat = float(lat_str)
                        lon = float(lon_str)

                        fecha_raw = desc_data.get("FECHA", "")
                        dt = None
                        if fecha_raw:
                            try:
                                dt = datetime.strptime(fecha_raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            except Exception:
                                dt = None

                        if dt and dt < CATALOG_START_DATE:
                            elem.clear()
                            continue

                        magnitud = 0.0
                        for key in ["MAGNITUD", "MBLG", "ML", "MW", "MB"]:
                            val = desc_data.get(key)
                            if val:
                                try:
                                    x = float(str(val).replace(",", "."))
                                    if x > 0:
                                        magnitud = x
                                        break
                                except Exception:
                                    pass

                        profundidad = 0.0
                        try:
                            profundidad = float(str(desc_data.get("PROFUNDIDAD", "0")).replace(",", "."))
                        except Exception:
                            profundidad = 0.0

                        localizacion = desc_data.get("LOCALIZACIÓN") or desc_data.get("LOCALIZACION") or ""
                        evid = desc_data.get("EVID", "")

                        fecha = dt.strftime("%d/%m/%Y") if dt else ""
                        hora = dt.strftime("%H:%M:%S") if dt else ""

                        events.append({
                            "id": str(evid),
                            "fecha": fecha,
                            "hora_utc": hora,
                            "datetime_iso": dt.isoformat() if dt else None,
                            "lat": lat,
                            "lon": lon,
                            "profundidad_km": profundidad,
                            "magnitud": magnitud,
                            "tipo_magnitud": "MbLg",
                            "localizacion": localizacion or (name_el.text if name_el is not None else ""),
                            "isla": classify_island(lat, lon),
                            "source": "IGN_kmz"
                        })

                    except Exception:
                        pass

                    elem.clear()

        HISTORICAL_CACHE["loaded"] = True
        HISTORICAL_CACHE["events"] = events
        HISTORICAL_CACHE["error"] = None
        return events

    except Exception as e:
        HISTORICAL_CACHE["loaded"] = True
        HISTORICAL_CACHE["events"] = []
        HISTORICAL_CACHE["error"] = str(e)
        return []


# =========================
# Analítica
# =========================
def depth_profile(eventos):
    bins = {
        "< 5 km": 0,
        "5–10 km": 0,
        "10–15 km": 0,
        "15–20 km": 0,
        "> 20 km": 0
    }

    for e in eventos:
        p = e.get("profundidad_km", 0)
        if p < 5:
            bins["< 5 km"] += 1
        elif p < 10:
            bins["5–10 km"] += 1
        elif p < 15:
            bins["10–15 km"] += 1
        elif p < 20:
            bins["15–20 km"] += 1
        else:
            bins["> 20 km"] += 1

    return bins


def serie_temporal(eventos):
    dias = defaultdict(lambda: {"count": 0, "mmax": 0})

    for e in eventos:
        dt = parse_event_datetime(e)
        if not dt:
            continue
        clave = dt.strftime("%d/%m")
        dias[clave]["count"] += 1
        dias[clave]["mmax"] = max(dias[clave]["mmax"], e["magnitud"])

    ordenadas = sorted(
        dias.items(),
        key=lambda item: datetime.strptime(item[0], "%d/%m")
    )

    return {
        "labels": [k for k, _ in ordenadas],
        "counts": [v["count"] for _, v in ordenadas],
        "mmax": [v["mmax"] for _, v in ordenadas]
    }


def detect_swarm_candidates(eventos):
    recientes = events_in_days(eventos, 3)
    buckets = {}

    for e in recientes:
        key = (round(e["lat"], 2), round(e["lon"], 2))
        buckets.setdefault(key, []).append(e)

    resultados = []
    for _, grupo in buckets.items():
        n = len(grupo)
        if n < 4:
            continue

        lat_c = sum(x["lat"] for x in grupo) / n
        lon_c = sum(x["lon"] for x in grupo) / n
        mag_max = max(x["magnitud"] for x in grupo)
        mag_media = round(sum(x["magnitud"] for x in grupo) / n, 2)
        profundidad_media = round(sum(x["profundidad_km"] for x in grupo) / n, 1)
        isla = classify_island(lat_c, lon_c)

        if n >= 12:
            nivel = "alto"
            color = "red"
        elif n >= 7:
            nivel = "medio"
            color = "orange"
        else:
            nivel = "bajo"
            color = "green"

        resultados.append({
            "lat": round(lat_c, 4),
            "lon": round(lon_c, 4),
            "count": n,
            "magnitud_max": mag_max,
            "magnitud_media": mag_media,
            "profundidad_media_km": profundidad_media,
            "isla": isla,
            "nivel": nivel,
            "color": color,
            "label": f"Posible enjambre {nivel} ({n} eventos / 3 días)"
        })

    resultados.sort(key=lambda x: (x["count"], x["magnitud_max"]), reverse=True)
    return resultados


def compute_baseline(events_recent, events_historical, island_name=None):
    merged = merge_recent_and_historical(events_recent, events_historical)

    if island_name and island_name != "Todas":
        merged = [e for e in merged if e["isla"] == island_name]

    baseline_window = events_between_days_ago(merged, 60, 30)

    if not baseline_window:
        baseline_window = events_between_days_ago(merged, 90, 30)

    if not baseline_window:
        cutoff = now_utc() - timedelta(days=7)
        baseline_window = [e for e in merged if (parse_event_datetime(e) and parse_event_datetime(e) < cutoff)]

    total_days = 30
    eventos_totales = len(baseline_window)
    media_diaria = round(eventos_totales / total_days, 2) if total_days else 0
    media_7d = round(media_diaria * 7, 2)
    magnitud_media = round(sum(e["magnitud"] for e in baseline_window) / len(baseline_window), 2) if baseline_window else 0
    profundidad_media = round(sum(e["profundidad_km"] for e in baseline_window) / len(baseline_window), 2) if baseline_window else 0

    return {
        "sample_size": len(baseline_window),
        "media_diaria": media_diaria,
        "media_7d": media_7d,
        "magnitud_media": magnitud_media,
        "profundidad_media_km": profundidad_media,
        "window_note": "Baseline calculado sobre actividad histórica reciente previa (preferencia 60–30 días atrás)."
    }


def compare_windows(events_recent, events_historical):
    merged = merge_recent_and_historical(events_recent, events_historical)

    return {
        "24h": len(events_in_hours(merged, 24)),
        "7d": len(events_in_days(merged, 7)),
        "10d": len(events_in_days(merged, 10)),
        "30d": len(events_in_days(merged, 30))
    }


def compute_acceleration(events_recent, events_historical):
    merged = merge_recent_and_historical(events_recent, events_historical)

    e24 = len(events_in_hours(merged, 24))
    e72 = len(events_in_hours(merged, 72))
    previous_48_within_72 = max(0, e72 - e24)

    if previous_48_within_72 == 0:
        ratio = float(e24) if e24 > 0 else 0.0
    else:
        ratio = e24 / previous_48_within_72

    if e24 >= 4 and ratio >= 2:
        label = "marcada"
    elif ratio >= 1.5 and e24 >= 2:
        label = "apreciable"
    else:
        label = "sin aceleración clara"

    return {
        "eventos_24h": e24,
        "eventos_72h": e72,
        "previas_48h_en_72h": previous_48_within_72,
        "ratio": round(ratio, 2),
        "label": label
    }


def detect_depth_migration(events_recent, events_historical, island_name=None):
    merged = merge_recent_and_historical(events_recent, events_historical)

    if island_name and island_name != "Todas":
        merged = [e for e in merged if e["isla"] == island_name]
        events_recent = [e for e in events_recent if e["isla"] == island_name]
        events_historical = [e for e in events_historical if e["isla"] == island_name]

    last_7d = events_in_days(merged, 7)
    last_72h = events_in_hours(merged, 72)
    prev_7d_window = events_between_days_ago(merged, 14, 7)

    mean_72h = round(sum(e["profundidad_km"] for e in last_72h) / len(last_72h), 2) if last_72h else None
    mean_prev7 = round(sum(e["profundidad_km"] for e in prev_7d_window) / len(prev_7d_window), 2) if prev_7d_window else None
    mean_7d = round(sum(e["profundidad_km"] for e in last_7d) / len(last_7d), 2) if last_7d else None

    trend = "sin datos suficientes"
    color = "green"
    shift_km = None
    score = 0
    drivers = []

    if mean_72h is not None and mean_prev7 is not None:
        shift_km = round(mean_prev7 - mean_72h, 2)

        if shift_km >= 5:
            trend = "migración superficial marcada"
            color = "red"
            score = 3
            drivers.append(f"la profundidad media reciente es {shift_km} km más superficial que la ventana previa")
        elif shift_km >= 2:
            trend = "migración superficial moderada"
            color = "orange"
            score = 2
            drivers.append(f"la profundidad media reciente es {shift_km} km más superficial que la ventana previa")
        elif shift_km <= -5:
            trend = "migración a mayor profundidad marcada"
            color = "orange"
            score = 2
            drivers.append(f"la profundidad media reciente es {abs(shift_km)} km más profunda que la ventana previa")
        else:
            trend = "sin migración clara"
            color = "green"
            score = 0
            drivers.append("no se observa un desplazamiento vertical claro de la sismicidad")

    shallow_recent = len([e for e in last_72h if e["profundidad_km"] < 10])
    total_recent = len(last_72h)
    shallow_ratio = round(shallow_recent / total_recent, 2) if total_recent > 0 else 0

    if shallow_ratio >= 0.7 and total_recent >= 5:
        drivers.append("predominio de sismicidad superficial en 72h")

    return {
        "headline": trend.capitalize(),
        "trend": trend,
        "color": color,
        "score": score,
        "metrics": {
            "prof_media_72h_km": mean_72h,
            "prof_media_prev7_km": mean_prev7,
            "prof_media_7d_km": mean_7d,
            "shift_towards_surface_km": shift_km,
            "shallow_ratio_72h": shallow_ratio,
            "eventos_72h": total_recent
        },
        "drivers": drivers,
        "note": "Detector experimental de migración sísmica en profundidad. No implica por sí mismo ascenso magmático."
    }


def detect_regime_change(events_recent, events_historical, island_name=None):
    merged = merge_recent_and_historical(events_recent, events_historical)

    if island_name and island_name != "Todas":
        merged = [e for e in merged if e["isla"] == island_name]
        events_recent = [e for e in events_recent if e["isla"] == island_name]
        events_historical = [e for e in events_historical if e["isla"] == island_name]

    last_24h = events_in_hours(merged, 24)
    last_7d = events_in_days(merged, 7)
    last_30d = events_in_days(merged, 30)

    baseline = compute_baseline(events_recent, events_historical, island_name)
    acceleration = compute_acceleration(events_recent, events_historical)
    migration = detect_depth_migration(events_recent, events_historical, island_name)

    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_7d = len(last_7d) / baseline_7d

    mag_mean_30d = round(sum(e["magnitud"] for e in last_30d) / len(last_30d), 2) if last_30d else 0
    depth_mean_30d = round(sum(e["profundidad_km"] for e in last_30d) / len(last_30d), 2) if last_30d else 0

    baseline_mag = baseline["magnitud_media"] if baseline["magnitud_media"] > 0 else 0
    baseline_depth = baseline["profundidad_media_km"] if baseline["profundidad_media_km"] > 0 else depth_mean_30d

    mag_shift = round(mag_mean_30d - baseline_mag, 2)
    depth_shift = round(baseline_depth - depth_mean_30d, 2)

    score = 0

    if deviation_7d >= 2.0:
        score += 3
    elif deviation_7d >= 1.3:
        score += 2
    elif deviation_7d >= 1.1:
        score += 1

    if acceleration["ratio"] >= 2 and acceleration["eventos_24h"] >= 4:
        score += 3
    elif acceleration["ratio"] >= 1.5 and acceleration["eventos_24h"] >= 2:
        score += 2
    elif acceleration["ratio"] >= 1.2:
        score += 1

    if mag_shift >= 0.5:
        score += 2
    elif mag_shift >= 0.2:
        score += 1

    if depth_shift >= 5:
        score += 2
    elif depth_shift >= 2:
        score += 1

    score += migration["score"]

    if score <= 2:
        level = "estable"
        color = "green"
        headline = "Sin cambio claro de régimen"
    elif score <= 6:
        level = "moderado"
        color = "orange"
        headline = "Cambio moderado de régimen"
    else:
        level = "marcado"
        color = "red"
        headline = "Cambio marcado de régimen"

    bullets = []

    if deviation_7d >= 1.3:
        bullets.append(f"actividad 7d por encima del baseline ({deviation_7d:.2f}x)")
    elif deviation_7d < 0.9:
        bullets.append(f"actividad 7d por debajo del baseline ({deviation_7d:.2f}x)")

    if acceleration["label"] == "marcada":
        bullets.append("aceleración reciente marcada")
    elif acceleration["label"] == "apreciable":
        bullets.append("aceleración reciente apreciable")

    if mag_shift >= 0.2:
        bullets.append(f"magnitud media superior al baseline (+{mag_shift:.2f})")

    if depth_shift >= 2:
        bullets.append(f"sismicidad más superficial que el baseline ({depth_shift:.1f} km)")

    for d in migration["drivers"]:
        if d not in bullets:
            bullets.append(d)

    if not bullets:
        bullets.append("sin desviaciones relevantes frente al comportamiento esperado")

    return {
        "headline": headline,
        "level": level,
        "color": color,
        "score": score,
        "metrics": {
            "eventos_24h": len(last_24h),
            "eventos_7d": len(last_7d),
            "eventos_30d": len(last_30d),
            "baseline_7d": round(baseline_7d, 2),
            "deviation_7d": round(deviation_7d, 2),
            "acceleration_ratio": acceleration["ratio"],
            "mag_mean_30d": mag_mean_30d,
            "baseline_mag_mean": baseline_mag,
            "mag_shift": mag_shift,
            "depth_mean_30d_km": depth_mean_30d,
            "baseline_depth_mean_km": baseline_depth,
            "depth_shift_towards_surface_km": depth_shift,
            "migration_trend": migration["trend"]
        },
        "drivers": bullets,
        "note": "Detector experimental de cambio de régimen. No implica por sí mismo cambio eruptivo."
    }


def compute_risklab_index(events_recent, events_historical, island_name=None):
    merged = merge_recent_and_historical(events_recent, events_historical)

    if island_name and island_name != "Todas":
        merged = [e for e in merged if e["isla"] == island_name]
        events_recent = [e for e in events_recent if e["isla"] == island_name]
        events_historical = [e for e in events_historical if e["isla"] == island_name]

    e24 = len(events_in_hours(merged, 24))
    e7d = len(events_in_days(merged, 7))
    e30d = events_in_days(merged, 30)

    mmedia_30d = round(sum(e["magnitud"] for e in e30d) / len(e30d), 2) if e30d else 0
    pmedia_30d = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 2) if e30d else 0

    accel = compute_acceleration(events_recent, events_historical)["ratio"]
    baseline = compute_baseline(events_recent, events_historical, island_name)
    migration = detect_depth_migration(events_recent, events_historical, island_name)

    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_ratio_7d = round(e7d / baseline_7d, 2)

    depth_component = max(0, 20 - pmedia_30d)

    value = (
        (min(deviation_ratio_7d, 6) * 12.0) +
        (e24 * 1.8) +
        (mmedia_30d * 10.0 * 0.25) +
        (accel * 7.0) +
        (depth_component * 0.45) +
        (migration["score"] * 4.0)
    )

    value = round(min(100, max(0, value)), 1)

    if value < 25:
        signal = "Índice RiskLab bajo"
        color = "green"
    elif value < 50:
        signal = "Índice RiskLab moderado"
        color = "orange"
    else:
        signal = "Índice RiskLab elevado"
        color = "red"

    return {
        "value": value,
        "signal": signal,
        "color": color,
        "components": {
            "eventos_24h": e24,
            "eventos_7d": e7d,
            "eventos_30d": len(e30d),
            "magnitud_media_30d": mmedia_30d,
            "profundidad_media_30d_km": pmedia_30d,
            "aceleracion_ratio": round(accel, 2),
            "baseline_media_7d": baseline["media_7d"],
            "desviacion_vs_baseline_7d": deviation_ratio_7d,
            "migration_score": migration["score"],
            "migration_trend": migration["trend"]
        },
        "baseline": baseline,
        "note": "Índice experimental de observación relativo al comportamiento sísmico reciente esperado. No equivale al semáforo volcánico oficial."
    }


def compute_anomaly_signal(recent, historical, island=None):
    merged = merge_recent_and_historical(recent, historical)

    if island and island != "Todas":
        merged = [e for e in merged if e["isla"] == island]
        recent = [e for e in recent if e["isla"] == island]
        historical = [e for e in historical if e["isla"] == island]

    last_24h = events_in_hours(merged, 24)
    last_7d = events_in_days(merged, 7)

    baseline = compute_baseline(recent, historical, island)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0

    deviation_score = min((len(last_7d) / baseline_7d) * 20, 30)

    accel_data = compute_acceleration(recent, historical)
    accel_score = min(accel_data["ratio"] * 8, 20)

    magnitudes = [e["magnitud"] for e in last_7d if e.get("magnitud") is not None]
    mag_mean = (sum(magnitudes) / len(magnitudes)) if magnitudes else 0
    mag_score = min(mag_mean * 5, 10)

    swarm_score = 0
    if len(last_24h) >= 10:
        swarm_score = 15
    elif len(last_24h) >= 5:
        swarm_score = 8

    migration = detect_depth_migration(recent, historical, island)
    migration_score = min(migration.get("score", 0) * 6, 20)

    anomaly = deviation_score + accel_score + mag_score + swarm_score + migration_score
    anomaly = min(anomaly, 100)

    if anomaly < 30:
        level = "baja"
        color = "green"
    elif anomaly < 60:
        level = "moderada"
        color = "orange"
    else:
        level = "marcada"
        color = "red"

    drivers = []

    if deviation_score > 12:
        drivers.append("desviación relevante frente al baseline")
    if accel_score > 8:
        drivers.append("aceleración reciente")
    if mag_score > 4:
        drivers.append("magnitud media reciente destacable")
    if swarm_score > 0:
        drivers.append("concentración reciente de eventos")
    if migration_score > 0:
        drivers.append("señal de migración en profundidad")

    if not drivers:
        drivers.append("sin anomalías relevantes frente al patrón esperado")

    return {
        "score": round(anomaly, 1),
        "nivel": level,
        "color": color,
        "drivers": drivers
    }


def territorial_summary(island, anomaly, infrastructures):
    infra_isla = [i for i in infrastructures if i["isla"] == island]
    tipos = sorted(list(set(i["tipo"] for i in infra_isla)))

    lectura = "actividad dentro de parámetros habituales"
    if anomaly["nivel"] == "moderada":
        lectura = "actividad ligeramente superior al baseline reciente"
    if anomaly["nivel"] == "marcada":
        lectura = "actividad anómala que merece seguimiento"

    return {
        "isla": island,
        "infraestructuras": len(infra_isla),
        "tipos": tipos,
        "nivel_anomalia": anomaly["nivel"],
        "lectura": lectura
    }


def auto_interpretation(events_recent, events_historical, island_name="Canarias"):
    merged = merge_recent_and_historical(events_recent, events_historical)

    if island_name and island_name != "Canarias":
        merged = [e for e in merged if e["isla"] == island_name]
        events_recent = [e for e in events_recent if e["isla"] == island_name]
        events_historical = [e for e in events_historical if e["isla"] == island_name]

    e24 = events_in_hours(merged, 24)
    e72 = events_in_hours(merged, 72)
    e7d = events_in_days(merged, 7)
    e30d = events_in_days(merged, 30)

    n24 = len(e24)
    n72 = len(e72)
    n7d = len(e7d)

    mmax = max((e["magnitud"] for e in e30d), default=0)
    pmedia = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 1) if e30d else 0

    acceleration = compute_acceleration(events_recent, events_historical)
    baseline = compute_baseline(events_recent, events_historical, island_name if island_name != "Canarias" else None)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_ratio = round(n7d / baseline_7d, 2)
    regime = detect_regime_change(events_recent, events_historical, island_name if island_name != "Canarias" else None)
    migration = detect_depth_migration(events_recent, events_historical, island_name if island_name != "Canarias" else None)

    swarm = detect_swarm_candidates(events_recent)
    swarm_text = ""
    if swarm:
        top_swarm = swarm[0]
        swarm_text = f" Se detecta además un posible enjambre experimental con {top_swarm['count']} eventos."

    fragments = []

    if n24 == 0 and n7d == 0:
        fragments.append(f"No se observan señales destacadas en la ventana reciente para {island_name}.")
    else:
        fragments.append(
            f"En {island_name} se registran {n24} eventos en 24 horas, {n7d} en 7 días y una magnitud máxima reciente de {mmax:.1f}."
        )

    if deviation_ratio >= 2:
        fragments.append(f"La actividad de 7 días se sitúa claramente por encima del baseline esperado ({deviation_ratio} veces).")
    elif deviation_ratio >= 1.2:
        fragments.append(f"La actividad de 7 días se sitúa moderadamente por encima del baseline esperado ({deviation_ratio} veces).")
    else:
        fragments.append("La actividad reciente se sitúa en rangos próximos al comportamiento esperado.")

    if acceleration["label"] == "marcada":
        fragments.append("La actividad sísmica muestra una aceleración reciente marcada.")
    elif acceleration["label"] == "apreciable":
        fragments.append("La actividad sísmica muestra una aceleración reciente apreciable.")
    else:
        fragments.append("No se aprecia una aceleración sísmica clara en la comparación reciente.")

    if e30d:
        if pmedia < 10:
            fragments.append("El perfil medio de profundidad es relativamente superficial.")
        elif pmedia < 15:
            fragments.append("El perfil medio de profundidad es intermedio.")
        else:
            fragments.append("El perfil medio de profundidad es relativamente profundo.")

    if migration["trend"] == "migración superficial marcada":
        fragments.append("El detector experimental observa una migración sísmica superficial marcada.")
    elif migration["trend"] == "migración superficial moderada":
        fragments.append("El detector experimental observa una migración sísmica superficial moderada.")
    elif migration["trend"] == "migración a mayor profundidad marcada":
        fragments.append("El detector experimental observa una migración reciente a mayor profundidad.")
    else:
        fragments.append("No se observa una migración sísmica clara en profundidad.")

    if regime["level"] == "marcado":
        fragments.append("El detector experimental identifica un cambio marcado de régimen sísmico.")
    elif regime["level"] == "moderado":
        fragments.append("El detector experimental identifica un cambio moderado de régimen sísmico.")
    else:
        fragments.append("El detector experimental no identifica un cambio claro de régimen sísmico.")

    fragments.append(swarm_text.strip())

    text = " ".join([f for f in fragments if f]).strip()
    return {
        "text": text,
        "metrics": {
            "24h": n24,
            "72h": n72,
            "7d": n7d,
            "30d": len(e30d),
            "mmax": round(mmax, 1),
            "profundidad_media_km": pmedia,
            "aceleracion": acceleration["label"],
            "desviacion_vs_baseline_7d": deviation_ratio,
            "regime_level": regime["level"],
            "migration_trend": migration["trend"]
        }
    }


def grouped_summary_by_island(events_recent, events_historical):
    summary = {}
    for isla in [
        "Tenerife", "La Palma", "El Hierro", "Gran Canaria",
        "Lanzarote", "Fuerteventura", "La Gomera", "Atlántico-Canarias"
    ]:
        live = [e for e in events_recent if e["isla"] == isla]
        hist = [e for e in events_historical if e["isla"] == isla]
        merged = merge_recent_and_historical(live, hist)

        risk = compute_risklab_index(live, hist, isla) if merged else {
            "value": 0,
            "signal": "Índice RiskLab bajo",
            "baseline": {"media_7d": 0},
            "components": {"desviacion_vs_baseline_7d": 0, "migration_trend": "sin datos"}
        }

        summary[isla] = {
            "eventos_24h": len(events_in_hours(merged, 24)),
            "eventos_72h": len(events_in_hours(merged, 72)),
            "eventos_7d": len(events_in_days(merged, 7)),
            "eventos_10d": len(events_in_days(merged, 10)),
            "eventos_30d": len(events_in_days(merged, 30)),
            "magnitud_max": round(max((x["magnitud"] for x in merged), default=0), 1),
            "risklab_index": risk["value"],
            "risklab_signal": risk["signal"],
            "baseline_7d": risk["baseline"]["media_7d"],
            "desviacion_vs_baseline_7d": risk["components"]["desviacion_vs_baseline_7d"],
            "migration_trend": risk["components"]["migration_trend"]
        }
    return summary


# =========================
# Infraestructuras demo
# =========================
EMERGENCY_INFRASTRUCTURES = [
    {
        "nombre": "Polideportivo Municipal de Los Llanos",
        "tipo": "polideportivo",
        "lat": 28.6562,
        "lon": -17.9116,
        "municipio": "Los Llanos de Aridane",
        "isla": "La Palma"
    },
    {
        "nombre": "Pabellón Roberto Estrello",
        "tipo": "polideportivo",
        "lat": 28.4917,
        "lon": -16.3150,
        "municipio": "Santa Cruz de Tenerife",
        "isla": "Tenerife"
    },
    {
        "nombre": "Puerto de Santa Cruz de La Palma",
        "tipo": "puerto",
        "lat": 28.6819,
        "lon": -17.7648,
        "municipio": "Santa Cruz de La Palma",
        "isla": "La Palma"
    },
    {
        "nombre": "Campo de Fútbol de El Paso",
        "tipo": "campo_futbol",
        "lat": 28.6514,
        "lon": -17.8797,
        "municipio": "El Paso",
        "isla": "La Palma"
    }
]


# =========================
# Rutas
# =========================
@app.route("/")
def root():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(".", path)


@app.route("/api/ign-canarias")
def api_ign_canarias():
    try:
        eventos = parse_ign_canarias()
        return jsonify({
            "ok": True,
            "count": len(eventos),
            "eventos": eventos
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "count": 0,
            "eventos": []
        }), 500


@app.route("/api/usgs-canarias")
def api_usgs_canarias():
    try:
        eventos = fetch_usgs_canarias()
        return jsonify({
            "ok": True,
            "count": len(eventos),
            "eventos": eventos
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "count": 0,
            "eventos": []
        }), 500


@app.route("/api/catalog-historical-status")
def api_catalog_historical_status():
    events = historical = []
    return jsonify({
        "ok": True,
        "count": len(events),
        "loaded": HISTORICAL_CACHE["loaded"],
        "error": HISTORICAL_CACHE["error"]
    })


@app.route("/api/ign-enjambres")
def api_ign_enjambres():
    try:
        eventos = parse_ign_canarias()
        candidatos = detect_swarm_candidates(eventos)
        return jsonify({
            "ok": True,
            "count": len(candidatos),
            "candidatos": candidatos
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "count": 0,
            "candidatos": []
        }), 500


@app.route("/api/ign-serie")
def api_ign_serie():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        if island_name and island_name != "Todas":
            recent = [e for e in recent if e["isla"] == island_name]
            historical = [e for e in historical if e["isla"] == island_name]

        merged = merge_recent_and_historical(recent, historical)
        serie = serie_temporal(events_in_days(merged, 30))
        return jsonify({
            "ok": True,
            "serie": serie
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "serie": {"labels": [], "counts": [], "mmax": []}
        }), 500


@app.route("/api/risklab-summary")
def api_risklab_summary():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        return jsonify({
            "ok": True,
            "summary": grouped_summary_by_island(recent, historical)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "summary": {}
        }), 500


@app.route("/api/risklab-index")
def api_risklab_index():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        data = compute_risklab_index(recent, historical, island_name if island_name != "Todas" else None)
        return jsonify({
            "ok": True,
            "risklab_index": data
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "risklab_index": {}
        }), 500


@app.route("/api/risklab-regime")
def api_risklab_regime():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        data = detect_regime_change(recent, historical, island_name if island_name != "Todas" else None)

        return jsonify({
            "ok": True,
            "regime": data
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "regime": {}
        }), 500


@app.route("/api/risklab-migration")
def api_risklab_migration():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        data = detect_depth_migration(recent, historical, island_name if island_name != "Todas" else None)

        return jsonify({
            "ok": True,
            "migration": data
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "migration": {}
        }), 500


@app.route("/api/risklab-interpretation")
def api_risklab_interpretation():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        label = "Canarias"
        if island_name and island_name != "Todas":
            label = island_name

        interp = auto_interpretation(recent, historical, label)
        return jsonify({
            "ok": True,
            "interpretation": interp
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "interpretation": {}
        }), 500


@app.route("/api/risklab-depth")
def api_risklab_depth():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        merged = merge_recent_and_historical(recent, historical)
        if island_name and island_name != "Todas":
            merged = [e for e in merged if e["isla"] == island_name]

        return jsonify({
            "ok": True,
            "depth_profile": depth_profile(events_in_days(merged, 30))
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "depth_profile": {}
        }), 500


@app.route("/api/risklab-compare")
def api_risklab_compare():
    try:
        recent = parse_ign_canarias()
        historical = load_historical_catalog()
        island_name = request.args.get("island")

        if island_name and island_name != "Todas":
            recent = [e for e in recent if e["isla"] == island_name]
            historical = [e for e in historical if e["isla"] == island_name]

        return jsonify({
            "ok": True,
            "compare": compare_windows(recent, historical),
            "acceleration": compute_acceleration(recent, historical),
            "baseline": compute_baseline(recent, historical, island_name if island_name != "Todas" else None)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "compare": {},
            "acceleration": {},
            "baseline": {}
        }), 500


@app.route("/api/emergency-infrastructures")
def api_emergency_infrastructures():
    try:
        island_name = request.args.get("island")
        municipio = request.args.get("municipio")

        data = EMERGENCY_INFRASTRUCTURES[:]

        if island_name and island_name != "Todas":
            data = [x for x in data if x["isla"] == island_name]

        if municipio:
            data = [x for x in data if x["municipio"].lower() == municipio.lower()]

        return jsonify({
            "ok": True,
            "count": len(data),
            "infraestructuras": data,
            "note": "Inventario de demostración. Pendiente de carga completa desde planes municipales/insulares."
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "count": 0,
            "infraestructuras": []
        }), 500


@app.route("/api/risklab-bundle")
def api_risklab_bundle():
    try:
        island_name = request.args.get("island")
        if island_name == "Todas":
            island_name = None

        def build_bundle():
            recent = parse_ign_canarias()
            historical = []

            recent_filtered = recent
            historical_filtered = historical

            if island_name:
                recent_filtered = [e for e in recent if e["isla"] == island_name]
                historical_filtered = [e for e in historical if e["isla"] == island_name]

            summary = grouped_summary_by_island(recent, historical)
            if island_name:
                summary = {island_name: summary.get(island_name, {})}

            risklab_index = compute_risklab_index(recent_filtered, historical_filtered, island_name)
            interpretation = auto_interpretation(recent_filtered, historical_filtered, island_name or "Canarias")
            depth = depth_profile(events_in_days(merge_recent_and_historical(recent_filtered, historical_filtered), 30))
            compare = compare_windows(recent_filtered, historical_filtered)
            acceleration = compute_acceleration(recent_filtered, historical_filtered)
            baseline = compute_baseline(recent_filtered, historical_filtered, island_name)
            regime = detect_regime_change(recent_filtered, historical_filtered, island_name)
            migration = detect_depth_migration(recent_filtered, historical_filtered, island_name)
            anomaly = compute_anomaly_signal(recent_filtered, historical_filtered, island_name)

            serie = serie_temporal(
                events_in_days(merge_recent_and_historical(recent_filtered, historical_filtered), 30)
            )

            enjambres = detect_swarm_candidates(recent)
            if island_name:
                enjambres = [c for c in enjambres if c["isla"] == island_name]

            infra = EMERGENCY_INFRASTRUCTURES[:]
            if island_name:
                infra = [x for x in infra if x["isla"] == island_name]

            territorial = None
            if island_name:
                territorial = territorial_summary(island_name, anomaly, EMERGENCY_INFRASTRUCTURES)

            return {
                "ok": True,
                "ign_eventos": recent_filtered,
                "summary": summary,
                "risklab_index": risklab_index,
                "interpretation": interpretation,
                "depth_profile": depth,
                "compare": compare,
                "acceleration": acceleration,
                "baseline": baseline,
                "regime": regime,
                "migration": migration,
                "anomaly": anomaly,
                "territorial": territorial,
                "serie": serie,
                "candidatos_enjambre": enjambres,
                "infraestructuras": infra,
                "catalog_count": len(historical_filtered)
            }

        data = get_or_build_cached("bundle", island_name or "Todas", build_bundle)
        return jsonify(data)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/api/ign-debug")
def api_ign_debug():
    try:
        html_text = fetch_ign_html()
        soup = BeautifulSoup(html_text, "html.parser")
        text = soup.get_text("\n", strip=True)
        lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
        return jsonify({
            "ok": True,
            "sample_lines": lines[:40],
            "html_length": len(html_text),
            "historical_cache_loaded": HISTORICAL_CACHE["loaded"],
            "historical_cache_error": HISTORICAL_CACHE["error"]
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)