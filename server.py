from flask import Flask, jsonify, send_from_directory, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os
import math

app = Flask(__name__, static_folder='.')

IGN_URL = "https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias"


# =========================================================
# CONFIG
# =========================================================
OFFICIAL_VOLCANIC_STATUS = [
    {
        "isla": "Tenerife",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    },
    {
        "isla": "La Palma",
        "nivel": "Amarillo",
        "color": "yellow",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en amarillo por situación post-eruptiva."
    },
    {
        "isla": "El Hierro",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    },
    {
        "isla": "Gran Canaria",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    },
    {
        "isla": "Lanzarote",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    },
    {
        "isla": "Fuerteventura",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    },
    {
        "isla": "La Gomera",
        "nivel": "Verde",
        "color": "green",
        "scope": "isla",
        "oficial": True,
        "fuente": "Gobierno de Canarias / PEVOLCA",
        "last_verified": "2026-04-03",
        "nota": "Estado oficial insular mostrado en verde."
    }
]

ISLAND_CENTERS = {
    "Tenerife": {"lat": 28.2916, "lon": -16.6291},
    "La Palma": {"lat": 28.6837, "lon": -17.7649},
    "El Hierro": {"lat": 27.7255, "lon": -18.0243},
    "Gran Canaria": {"lat": 28.1235, "lon": -15.4363},
    "Lanzarote": {"lat": 29.0469, "lon": -13.5899},
    "Fuerteventura": {"lat": 28.3587, "lon": -14.0537},
    "La Gomera": {"lat": 28.1165, "lon": -17.2461},
}

MUNICIPALITIES_BY_ISLAND = {
    "Tenerife": [
        "Adeje", "Arafo", "Arico", "Arona", "Buenavista del Norte", "Candelaria",
        "El Rosario", "El Sauzal", "El Tanque", "Fasnia", "Garachico",
        "Granadilla de Abona", "Guía de Isora", "Güímar", "Icod de los Vinos",
        "La Guancha", "La Matanza de Acentejo", "La Orotava", "La Victoria de Acentejo",
        "Los Realejos", "Los Silos", "Puerto de la Cruz", "San Cristóbal de La Laguna",
        "San Juan de la Rambla", "Santa Cruz de Tenerife", "Santa Úrsula",
        "Santiago del Teide", "Tacoronte", "Tegueste", "Vilaflor de Chasna"
    ],
    "La Palma": [
        "Breña Alta", "Breña Baja", "El Paso", "Fuencaliente", "Garafía",
        "Los Llanos de Aridane", "Puntagorda", "Puntallana", "San Andrés y Sauces",
        "Santa Cruz de La Palma", "Tazacorte", "Tijarafe", "Villa de Mazo"
    ],
    "El Hierro": ["Frontera", "El Pinar", "Valverde"],
    "Gran Canaria": [
        "Agaete", "Agüimes", "Artenara", "Arucas", "Firgas", "Gáldar", "Ingenio",
        "La Aldea de San Nicolás", "Las Palmas de Gran Canaria", "Mogán", "Moya",
        "San Bartolomé de Tirajana", "Santa Brígida", "Santa Lucía de Tirajana",
        "Telde", "Teror", "Valsequillo de Gran Canaria", "Vega de San Mateo"
    ],
    "Lanzarote": ["Arrecife", "Haría", "San Bartolomé", "Teguise", "Tías", "Tinajo", "Yaiza"],
    "Fuerteventura": ["Antigua", "Betancuria", "La Oliva", "Pájara", "Puerto del Rosario", "Tuineje"],
    "La Gomera": ["Agulo", "Alajeró", "Hermigua", "San Sebastián de La Gomera", "Valle Gran Rey", "Vallehermoso"],
    "Atlántico-Canarias": ["Atlántico-Canarias"]
}

MUNICIPALITY_ALIASES = {
    "San Cristóbal de La Laguna": ["san cristobal de la laguna", "la laguna"],
    "Fuencaliente": ["fuencaliente", "fuencaliente de la palma"],
    "El Pinar": ["el pinar", "el pinar de el hierro"],
    "Guía de Isora": ["guia de isora", "guía de isora"],
    "Güímar": ["guimar", "güímar"],
    "Agüimes": ["aguimes", "agüimes"],
    "Gáldar": ["galdar", "gáldar"],
    "Mogán": ["mogan", "mogán"],
    "San Bartolomé": ["san bartolome", "san bartolomé"],
    "Tías": ["tias", "tías"],
    "Pájara": ["pajara", "pájara"],
    "Haría": ["haria", "haría"],
    "Alajeró": ["alajero", "alajeró"],
    "Breña Alta": ["brena alta", "breña alta"],
    "Breña Baja": ["brena baja", "breña baja"],
    "Garafía": ["garafia", "garafía"],
    "San Andrés y Sauces": ["san andres y sauces", "san andrés y sauces"],
    "Santa Úrsula": ["santa ursula", "santa úrsula"],
}

VOLCANO_REFERENCE = {
    "Tenerife": {"lat": 28.2724, "lon": -16.6425, "name": "Teide"},
    "La Palma": {"lat": 28.6128, "lon": -17.8660, "name": "Tajogaite / Cumbre Vieja"},
    "El Hierro": {"lat": 27.7290, "lon": -18.0200, "name": "Tagoro"},
    "Gran Canaria": {"lat": 28.0085, "lon": -15.4564, "name": "Bandama"},
    "Lanzarote": {"lat": 29.0167, "lon": -13.7500, "name": "Timanfaya"},
    "Fuerteventura": {"lat": 28.3587, "lon": -14.0537, "name": "Fuerteventura"},
    "La Gomera": {"lat": 28.1165, "lon": -17.2461, "name": "La Gomera"},
}

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
    },
    {
        "nombre": "Hospital Universitario de Canarias",
        "tipo": "hospital",
        "lat": 28.4511,
        "lon": -16.2985,
        "municipio": "San Cristóbal de La Laguna",
        "isla": "Tenerife"
    },
    {
        "nombre": "Hospital General de La Palma",
        "tipo": "hospital",
        "lat": 28.6671,
        "lon": -17.7915,
        "municipio": "Breña Alta",
        "isla": "La Palma"
    }
]


# =========================================================
# UTILIDADES
# =========================================================
def clean_text(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_float(value):
    value = str(value).replace(",", ".").strip()
    return float(value)


def now_utc():
    return datetime.now(timezone.utc)


def normalize_text(value):
    value = str(value or "").strip().lower()
    repl = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for a, b in repl.items():
        value = value.replace(a, b)
    return re.sub(r"\s+", " ", value)


def canonical_municipality_name(name):
    n = normalize_text(name)
    if not n:
        return ""

    for island, items in MUNICIPALITIES_BY_ISLAND.items():
        for item in items:
            if normalize_text(item) == n:
                return item

    for canonical, aliases in MUNICIPALITY_ALIASES.items():
        if n == normalize_text(canonical):
            return canonical
        for alias in aliases:
            if n == normalize_text(alias):
                return canonical

    return name


def municipality_to_island(municipio):
    m = normalize_text(municipio)
    for island, items in MUNICIPALITIES_BY_ISLAND.items():
        for item in items:
            if normalize_text(item) == m:
                return island
    return "Atlántico-Canarias"


def infer_municipality(localizacion, island):
    loc = normalize_text(localizacion)

    for canonical, aliases in MUNICIPALITY_ALIASES.items():
        names = [canonical] + aliases
        for candidate in names:
            if normalize_text(candidate) in loc:
                return canonical

    for candidate in MUNICIPALITIES_BY_ISLAND.get(island, []):
        if normalize_text(candidate) in loc:
            return candidate

    return ""


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


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a = math.sin(d1 / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d2 / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


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


# =========================================================
# INGESTA IGN
# =========================================================
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

            dt = None
            try:
                dt = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

            evento_id = ""
            for c in cells:
                if re.fullmatch(r"es\d+[a-z0-9]+", c.lower()):
                    evento_id = c
                    break

            isla = classify_island(lat, lon)
            municipio = canonical_municipality_name(infer_municipality(localizacion, isla))

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
                "isla": isla,
                "municipio": municipio,
                "source": "IGN_live"
            })
        except Exception:
            pass

    return eventos


# =========================================================
# USGS
# =========================================================
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


# =========================================================
# ANALÍTICA GENERAL
# =========================================================
def depth_profile(eventos):
    bins = {"< 5 km": 0, "5–10 km": 0, "10–15 km": 0, "15–20 km": 0, "> 20 km": 0}
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

    ordenadas = sorted(dias.items(), key=lambda item: datetime.strptime(item[0], "%d/%m"))
    return {
        "labels": [k for k, _ in ordenadas],
        "counts": [v["count"] for _, v in ordenadas],
        "mmax": [v["mmax"] for _, v in ordenadas]
    }


def compute_baseline(events_recent, island_name=None):
    eventos = list(events_recent)
    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    ventana = events_in_days(eventos, 10)
    total_days = 10
    eventos_totales = len(ventana)
    media_diaria = round(eventos_totales / total_days, 2) if total_days else 0
    media_7d = round(media_diaria * 7, 2)

    magnitud_media = round(sum(e["magnitud"] for e in ventana) / len(ventana), 2) if ventana else 0
    profundidad_media = round(sum(e["profundidad_km"] for e in ventana) / len(ventana), 2) if ventana else 0

    return {
        "sample_size": len(ventana),
        "media_diaria": media_diaria,
        "media_7d": media_7d,
        "magnitud_media": magnitud_media,
        "profundidad_media_km": profundidad_media,
    }


def compare_windows(events_recent):
    return {
        "24h": len(events_in_hours(events_recent, 24)),
        "7d": len(events_in_days(events_recent, 7)),
        "10d": len(events_in_days(events_recent, 10)),
        "30d": len(events_in_days(events_recent, 30))
    }


def compute_acceleration(events_recent):
    e24 = len(events_in_hours(events_recent, 24))
    e72 = len(events_in_hours(events_recent, 72))
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


def detect_depth_migration(events_recent, island_name=None):
    eventos = list(events_recent)
    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    last_7d = events_in_days(eventos, 7)
    last_72h = events_in_hours(eventos, 72)

    mean_72h = round(sum(e["profundidad_km"] for e in last_72h) / len(last_72h), 2) if last_72h else None
    mean_7d = round(sum(e["profundidad_km"] for e in last_7d) / len(last_7d), 2) if last_7d else None

    trend = "sin datos suficientes"
    color = "green"
    shift_km = None
    score = 0
    drivers = []

    if mean_72h is not None and mean_7d is not None:
        shift_km = round(mean_7d - mean_72h, 2)
        if shift_km >= 3:
            trend = "migración superficial moderada"
            color = "orange"
            score = 2
            drivers.append(f"la profundidad media reciente es {shift_km} km más superficial que la media 7d")
        elif shift_km <= -3:
            trend = "migración a mayor profundidad marcada"
            color = "orange"
            score = 2
            drivers.append(f"la profundidad media reciente es {abs(shift_km)} km más profunda que la media 7d")
        else:
            trend = "sin migración clara"
            color = "green"
            drivers.append("no se observa un desplazamiento vertical claro de la sismicidad")

    return {
        "headline": trend.capitalize(),
        "trend": trend,
        "color": color,
        "score": score,
        "metrics": {
            "prof_media_72h_km": mean_72h,
            "prof_media_7d_km": mean_7d,
            "shift_towards_surface_km": shift_km,
            "eventos_72h": len(last_72h)
        },
        "drivers": drivers
    }


def detect_regime_change(events_recent, island_name=None):
    eventos = list(events_recent)
    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    last_24h = events_in_hours(eventos, 24)
    last_7d = events_in_days(eventos, 7)
    last_30d = events_in_days(eventos, 30)

    baseline = compute_baseline(events_recent, island_name)
    acceleration = compute_acceleration(eventos)
    migration = detect_depth_migration(eventos, island_name)

    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_7d = len(last_7d) / baseline_7d
    mag_mean_30d = round(sum(e["magnitud"] for e in last_30d) / len(last_30d), 2) if last_30d else 0

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

    if mag_mean_30d >= 1.8:
        score += 1

    score += migration["score"]

    if score <= 2:
        level, color, headline = "estable", "green", "Sin cambio claro de régimen"
    elif score <= 6:
        level, color, headline = "moderado", "orange", "Cambio moderado de régimen"
    else:
        level, color, headline = "marcado", "red", "Cambio marcado de régimen"

    bullets = []
    if deviation_7d >= 1.3:
        bullets.append(f"actividad 7d por encima del baseline ({deviation_7d:.2f}x)")
    if acceleration["label"] == "marcada":
        bullets.append("aceleración reciente marcada")
    elif acceleration["label"] == "apreciable":
        bullets.append("aceleración reciente apreciable")
    if mag_mean_30d >= 1.8:
        bullets.append("magnitud media reciente destacable")
    bullets.extend(migration["drivers"])
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
            "migration_trend": migration["trend"]
        },
        "drivers": bullets
    }


def compute_risklab_index(events_recent, island_name=None):
    eventos = list(events_recent)
    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    e24 = len(events_in_hours(eventos, 24))
    e7d = len(events_in_days(eventos, 7))
    e30d = events_in_days(eventos, 30)

    mmedia_30d = round(sum(e["magnitud"] for e in e30d) / len(e30d), 2) if e30d else 0
    pmedia_30d = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 2) if e30d else 0

    accel = compute_acceleration(eventos)["ratio"]
    baseline = compute_baseline(events_recent, island_name)
    migration = detect_depth_migration(eventos, island_name)

    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_ratio_7d = round(e7d / baseline_7d, 2)
    depth_component = max(0, 20 - pmedia_30d)

    value = (
        (min(deviation_ratio_7d, 6) * 12.0) +
        (e24 * 1.8) +
        (mmedia_30d * 2.5) +
        (accel * 7.0) +
        (depth_component * 0.45) +
        (migration["score"] * 4.0)
    )
    value = round(min(100, max(0, value)), 1)

    if value < 25:
        signal, color = "Índice RiskLab bajo", "green"
    elif value < 50:
        signal, color = "Índice RiskLab moderado", "orange"
    else:
        signal, color = "Índice RiskLab elevado", "red"

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
        "note": "Índice experimental de observación. No equivale al semáforo volcánico oficial."
    }


def compute_anomaly_signal(recent, island=None):
    eventos = list(recent)
    if island and island != "Todas":
        eventos = [e for e in eventos if e["isla"] == island]

    last_24h = events_in_hours(eventos, 24)
    last_7d = events_in_days(eventos, 7)

    baseline = compute_baseline(recent, island)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0

    deviation_score = min((len(last_7d) / baseline_7d) * 20, 30)
    accel_data = compute_acceleration(eventos)
    accel_score = min(accel_data["ratio"] * 8, 20)

    magnitudes = [e["magnitud"] for e in last_7d if e.get("magnitud") is not None]
    mag_mean = (sum(magnitudes) / len(magnitudes)) if magnitudes else 0
    mag_score = min(mag_mean * 5, 10)

    swarm_score = 15 if len(last_24h) >= 10 else 8 if len(last_24h) >= 5 else 0
    migration = detect_depth_migration(eventos, island)
    migration_score = min(migration.get("score", 0) * 6, 20)

    anomaly = min(deviation_score + accel_score + mag_score + swarm_score + migration_score, 100)

    if anomaly < 30:
        level, color = "baja", "green"
    elif anomaly < 60:
        level, color = "moderada", "orange"
    else:
        level, color = "marcada", "red"

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

    return {"score": round(anomaly, 1), "nivel": level, "color": color, "drivers": drivers}


def auto_interpretation(events_recent, label="Canarias"):
    n24 = len(events_in_hours(events_recent, 24))
    n72 = len(events_in_hours(events_recent, 72))
    n7d = len(events_in_days(events_recent, 7))
    e30d = events_in_days(events_recent, 30)

    mmax = max((e["magnitud"] for e in e30d), default=0)
    pmedia = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 1) if e30d else 0

    acceleration = compute_acceleration(events_recent)
    baseline = compute_baseline(events_recent)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_ratio = round(n7d / baseline_7d, 2)

    fragments = []
    if n24 == 0 and n7d == 0:
        fragments.append(f"No se observan señales destacadas en la ventana reciente para {label}.")
    else:
        fragments.append(f"En {label} se registran {n24} eventos en 24 horas, {n7d} en 7 días y una magnitud máxima reciente de {mmax:.1f}.")

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

    return {
        "text": " ".join(fragments).strip(),
        "metrics": {
            "24h": n24,
            "72h": n72,
            "7d": n7d,
            "30d": len(e30d),
            "mmax": round(mmax, 1),
            "profundidad_media_km": pmedia,
            "aceleracion": acceleration["label"],
            "desviacion_vs_baseline_7d": deviation_ratio
        }
    }


def grouped_summary_by_island(events_recent):
    summary = {}
    for isla in [
        "Tenerife", "La Palma", "El Hierro", "Gran Canaria",
        "Lanzarote", "Fuerteventura", "La Gomera", "Atlántico-Canarias"
    ]:
        live = [e for e in events_recent if e["isla"] == isla]
        risk = compute_risklab_index(live, isla) if live else {
            "value": 0,
            "baseline": {"media_7d": 0},
            "components": {"desviacion_vs_baseline_7d": 0}
        }

        summary[isla] = {
            "eventos_24h": len(events_in_hours(live, 24)),
            "eventos_7d": len(events_in_days(live, 7)),
            "eventos_30d": len(events_in_days(live, 30)),
            "magnitud_max": round(max((x["magnitud"] for x in live), default=0), 1),
            "risklab_index": risk["value"],
            "baseline_7d": risk["baseline"]["media_7d"],
            "desviacion_vs_baseline_7d": risk["components"]["desviacion_vs_baseline_7d"]
        }
    return summary


# =========================================================
# ANALÍTICA MUNICIPAL
# =========================================================
def municipality_score(events):
    e24 = len(events_in_hours(events, 24))
    e7d = len(events_in_days(events, 7))
    e30d = len(events_in_days(events, 30))
    mmax = max((e["magnitud"] for e in events), default=0)
    pmedia = round(sum(e["profundidad_km"] for e in events) / len(events), 2) if events else 0
    accel = compute_acceleration(events)["ratio"] if events else 0

    depth_component = max(0, 20 - pmedia)
    score = (e24 * 10) + (e7d * 4) + (mmax * 12) + (accel * 8) + (depth_component * 0.4)
    score = round(min(100, max(0, score)), 1)

    if e7d == 0:
        nivel, color = "sin actividad", "gray"
    elif score < 20:
        nivel, color = "baja", "blue1"
    elif score < 45:
        nivel, color = "ligera", "blue2"
    elif score < 80:
        nivel, color = "moderada", "violet"
    else:
        nivel, color = "alta", "magenta"

    return {
        "score": score,
        "nivel": nivel,
        "color": color,
        "eventos_24h": e24,
        "eventos_7d": e7d,
        "eventos_30d": e30d,
        "magnitud_max_30d": round(mmax, 1),
        "profundidad_media_km": round(pmedia, 1) if events else 0,
        "aceleracion_ratio": round(accel, 2)
    }


def build_municipality_stats(events_recent, island_name=None):
    municipios = MUNICIPALITIES_BY_ISLAND.get(island_name, []) if island_name else [m for v in MUNICIPALITIES_BY_ISLAND.values() for m in v]
    out = {}
    for muni in municipios:
        evs = [e for e in events_recent if canonical_municipality_name(e.get("municipio", "")) == muni]
        out[muni] = {"municipio": muni, "isla": municipality_to_island(muni), **municipality_score(evs)}
    return out


def municipality_ranking(events_recent, island_name=None, limit=8):
    stats = build_municipality_stats(events_recent, island_name)
    items = list(stats.values())
    items.sort(key=lambda x: (x["score"], x["magnitud_max_30d"], x["eventos_7d"]), reverse=True)
    return [x for x in items if x["eventos_7d"] > 0][:limit]


def municipality_summary(events_recent, municipio):
    muni = canonical_municipality_name(municipio)
    evs = [e for e in events_recent if canonical_municipality_name(e.get("municipio", "")) == muni]
    return {"municipio": muni, "isla": municipality_to_island(muni), **municipality_score(evs)}


def detect_municipal_clusters(events_recent, island_name=None):
    stats = build_municipality_stats(events_recent, island_name)
    clusters = []

    for muni, data in stats.items():
        count = data["eventos_7d"]
        if count == 0:
            continue

        if count >= 12 or data["score"] >= 70:
            nivel = "concentrado"
            color = "magenta"
        elif count >= 6 or data["score"] >= 35:
            nivel = "activo"
            color = "violet"
        else:
            nivel = "leve"
            color = "blue2"

        ref = VOLCANO_REFERENCE.get(data["isla"])
        clusters.append({
            "municipio": muni,
            "isla": data["isla"],
            "nivel": nivel,
            "color": color,
            "score": data["score"],
            "eventos_7d": data["eventos_7d"],
            "magnitud_max_30d": data["magnitud_max_30d"],
            "ref_lat": ref["lat"] if ref else None,
            "ref_lon": ref["lon"] if ref else None,
            "ref_name": ref["name"] if ref else data["isla"]
        })

    clusters.sort(key=lambda x: (x["score"], x["eventos_7d"]), reverse=True)
    return clusters


def exposed_infrastructures(events_recent, island_name=None, municipio=None):
    stats = build_municipality_stats(events_recent, island_name)
    active_municipios = set()

    if municipio and municipio not in ("Todos", ""):
        active_municipios.add(canonical_municipality_name(municipio))
    else:
        for m, data in stats.items():
            if data["eventos_7d"] > 0:
                active_municipios.add(m)

    out = []
    for infra in EMERGENCY_INFRASTRUCTURES:
        if island_name and island_name != "Todas" and infra["isla"] != island_name:
            continue

        muni = canonical_municipality_name(infra["municipio"])
        if muni in active_municipios:
            ref = VOLCANO_REFERENCE.get(infra["isla"])
            distancia = None
            if ref:
                distancia = round(haversine_km(infra["lat"], infra["lon"], ref["lat"], ref["lon"]), 1)

            out.append({
                **infra,
                "distancia_km": distancia,
                "motivo": "infraestructura dentro de municipio con actividad reciente"
            })

    out.sort(key=lambda x: (x["distancia_km"] is None, x["distancia_km"] if x["distancia_km"] is not None else 9999))
    return out


# =========================================================
# RUTAS
# =========================================================
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
        return jsonify({"ok": True, "count": len(eventos), "eventos": eventos})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "count": 0, "eventos": []}), 500


@app.route("/api/usgs-canarias")
def api_usgs_canarias():
    try:
        eventos = fetch_usgs_canarias()
        return jsonify({"ok": True, "count": len(eventos), "eventos": eventos})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "count": 0, "eventos": []}), 500


@app.route("/api/official-volcanic-status")
def api_official_volcanic_status():
    return jsonify({"ok": True, "official_status": OFFICIAL_VOLCANIC_STATUS})


@app.route("/api/risklab-bundle")
def api_risklab_bundle():
    try:
        island_name = request.args.get("island")
        municipio = request.args.get("municipio")

        island_filter = None if island_name in (None, "Todas") else island_name
        municipio_filter = None if municipio in (None, "Todos", "") else canonical_municipality_name(municipio)

        recent = parse_ign_canarias()

        recent_island = recent
        if island_filter:
            recent_island = [e for e in recent if e["isla"] == island_filter]

        recent_selected = recent_island
        if municipio_filter:
            recent_selected = [e for e in recent_island if canonical_municipality_name(e.get("municipio", "")) == municipio_filter]

        analytics_base = recent_selected if municipio_filter else recent_island

        summary = grouped_summary_by_island(recent)
        risklab_index = compute_risklab_index(analytics_base, island_filter)
        interpretation = auto_interpretation(analytics_base, municipio_filter or island_filter or "Canarias")
        depth = depth_profile(events_in_days(analytics_base, 30))
        compare = compare_windows(analytics_base)
        acceleration = compute_acceleration(analytics_base)
        baseline = compute_baseline(analytics_base, island_filter)
        regime = detect_regime_change(analytics_base, island_filter)
        migration = detect_depth_migration(analytics_base, island_filter)
        anomaly = compute_anomaly_signal(analytics_base, island_filter)
        serie = serie_temporal(events_in_days(analytics_base, 30))

        official_status = OFFICIAL_VOLCANIC_STATUS

        municipal_stats = build_municipality_stats(recent_island, island_filter)
        municipal_ranking = municipality_ranking(recent_island, island_filter)
        selected_municipality = municipality_summary(recent_island, municipio_filter) if municipio_filter else None
        municipal_clusters = detect_municipal_clusters(recent_island, island_filter)
        infra_expuestas = exposed_infrastructures(recent_island, island_filter, municipio_filter)

        territorial = None
        if island_filter:
            territorial = {
                "isla": island_filter,
                "nivel_anomalia": anomaly["nivel"],
                "lectura": "actividad dentro de parámetros habituales" if anomaly["nivel"] == "baja" else
                           "actividad ligeramente superior al baseline reciente" if anomaly["nivel"] == "moderada" else
                           "actividad anómala que merece seguimiento",
                "infraestructuras": len([x for x in EMERGENCY_INFRASTRUCTURES if x["isla"] == island_filter]),
                "infra_expuestas": infra_expuestas
            }

        return jsonify({
            "ok": True,
            "ign_eventos": analytics_base,
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
            "official_status": official_status,
            "municipal_stats": municipal_stats,
            "municipal_ranking": municipal_ranking,
            "selected_municipality": selected_municipality,
            "municipal_clusters": municipal_clusters,
            "infra_expuestas": infra_expuestas
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "ign_eventos": [],
            "summary": {},
            "risklab_index": None,
            "interpretation": None,
            "depth_profile": {},
            "compare": {},
            "acceleration": {},
            "baseline": {},
            "regime": None,
            "migration": None,
            "anomaly": None,
            "territorial": None,
            "serie": {"labels": [], "counts": [], "mmax": []},
            "official_status": [],
            "municipal_stats": {},
            "municipal_ranking": [],
            "selected_municipality": None,
            "municipal_clusters": [],
            "infra_expuestas": []
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)