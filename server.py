from flask import Flask, jsonify, send_from_directory, request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math
import os

app = Flask(__name__, static_folder='.')

IGN_URL = "https://www.ign.es/web/vlc-ultimo-terremoto/-/terremotos-canarias/get10dias"


# =========================
# Catálogos base
# =========================
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
    "El Hierro": [
        "Frontera", "El Pinar", "Valverde"
    ],
    "Gran Canaria": [
        "Las Palmas de Gran Canaria", "Telde", "Ingenio", "Agüimes", "Gáldar",
        "Arucas", "Mogán", "San Bartolomé de Tirajana", "Santa Brígida", "Teror"
    ],
    "Lanzarote": [
        "Arrecife", "San Bartolomé", "Tías", "Tinajo", "Teguise", "Yaiza", "Haría"
    ],
    "Fuerteventura": [
        "Puerto del Rosario", "La Oliva", "Pájara", "Antigua", "Tuineje", "Betancuria"
    ],
    "La Gomera": [
        "San Sebastián de La Gomera", "Vallehermoso", "Alajeró", "Hermigua", "Agulo", "Valle Gran Rey"
    ],
    "Atlántico-Canarias": [
        "Atlántico-Canarias"
    ]
}


MUNICIPALITY_CENTROIDS = {
    # Tenerife
    ("Tenerife", "Adeje"): (28.1220, -16.7260),
    ("Tenerife", "Arafo"): (28.3400, -16.4150),
    ("Tenerife", "Arico"): (28.1770, -16.4790),
    ("Tenerife", "Arona"): (28.1000, -16.6800),
    ("Tenerife", "Buenavista del Norte"): (28.3700, -16.8500),
    ("Tenerife", "Candelaria"): (28.3540, -16.3710),
    ("Tenerife", "El Rosario"): (28.4300, -16.3600),
    ("Tenerife", "El Sauzal"): (28.4800, -16.4300),
    ("Tenerife", "El Tanque"): (28.3700, -16.7800),
    ("Tenerife", "Fasnia"): (28.2390, -16.4410),
    ("Tenerife", "Garachico"): (28.3720, -16.7650),
    ("Tenerife", "Granadilla de Abona"): (28.1180, -16.5760),
    ("Tenerife", "Guía de Isora"): (28.2100, -16.7800),
    ("Tenerife", "Güímar"): (28.3150, -16.4120),
    ("Tenerife", "Icod de los Vinos"): (28.3660, -16.7110),
    ("Tenerife", "La Guancha"): (28.3730, -16.6510),
    ("Tenerife", "La Matanza de Acentejo"): (28.4520, -16.4470),
    ("Tenerife", "La Orotava"): (28.3900, -16.5230),
    ("Tenerife", "La Victoria de Acentejo"): (28.4330, -16.4660),
    ("Tenerife", "Los Realejos"): (28.3850, -16.5820),
    ("Tenerife", "Los Silos"): (28.3670, -16.8170),
    ("Tenerife", "Puerto de la Cruz"): (28.4130, -16.5480),
    ("Tenerife", "San Cristóbal de La Laguna"): (28.4880, -16.3150),
    ("Tenerife", "San Juan de la Rambla"): (28.3910, -16.6500),
    ("Tenerife", "Santa Cruz de Tenerife"): (28.4630, -16.2510),
    ("Tenerife", "Santa Úrsula"): (28.4260, -16.4900),
    ("Tenerife", "Santiago del Teide"): (28.2950, -16.8150),
    ("Tenerife", "Tacoronte"): (28.4800, -16.4120),
    ("Tenerife", "Tegueste"): (28.5230, -16.3400),
    ("Tenerife", "Vilaflor de Chasna"): (28.1570, -16.6350),

    # La Palma
    ("La Palma", "Breña Alta"): (28.6500, -17.7900),
    ("La Palma", "Breña Baja"): (28.6300, -17.7600),
    ("La Palma", "El Paso"): (28.6500, -17.8800),
    ("La Palma", "Fuencaliente"): (28.4870, -17.8520),
    ("La Palma", "Garafía"): (28.8300, -17.9200),
    ("La Palma", "Los Llanos de Aridane"): (28.6580, -17.9180),
    ("La Palma", "Puntagorda"): (28.7700, -17.9800),
    ("La Palma", "Puntallana"): (28.7400, -17.7500),
    ("La Palma", "San Andrés y Sauces"): (28.8000, -17.7660),
    ("La Palma", "Santa Cruz de La Palma"): (28.6830, -17.7650),
    ("La Palma", "Tazacorte"): (28.6450, -17.9320),
    ("La Palma", "Tijarafe"): (28.7100, -17.9600),
    ("La Palma", "Villa de Mazo"): (28.6090, -17.7770),

    # El Hierro
    ("El Hierro", "Frontera"): (27.7530, -18.0050),
    ("El Hierro", "El Pinar"): (27.7110, -17.9810),
    ("El Hierro", "Valverde"): (27.8080, -17.9150),

    # Gran Canaria
    ("Gran Canaria", "Las Palmas de Gran Canaria"): (28.1230, -15.4360),
    ("Gran Canaria", "Telde"): (27.9960, -15.4180),
    ("Gran Canaria", "Ingenio"): (27.9190, -15.4350),
    ("Gran Canaria", "Agüimes"): (27.9050, -15.4460),
    ("Gran Canaria", "Gáldar"): (28.1400, -15.6500),
    ("Gran Canaria", "Arucas"): (28.1180, -15.5270),
    ("Gran Canaria", "Mogán"): (27.8830, -15.7230),
    ("Gran Canaria", "San Bartolomé de Tirajana"): (27.9240, -15.5730),
    ("Gran Canaria", "Santa Brígida"): (28.0320, -15.4910),
    ("Gran Canaria", "Teror"): (28.0590, -15.5490),

    # Lanzarote
    ("Lanzarote", "Arrecife"): (28.9630, -13.5480),
    ("Lanzarote", "San Bartolomé"): (28.9980, -13.6110),
    ("Lanzarote", "Tías"): (28.9530, -13.6500),
    ("Lanzarote", "Tinajo"): (29.0670, -13.6760),
    ("Lanzarote", "Teguise"): (29.0600, -13.5600),
    ("Lanzarote", "Yaiza"): (28.9530, -13.7650),
    ("Lanzarote", "Haría"): (29.1450, -13.4990),

    # Fuerteventura
    ("Fuerteventura", "Puerto del Rosario"): (28.5000, -13.8620),
    ("Fuerteventura", "La Oliva"): (28.6100, -13.9280),
    ("Fuerteventura", "Pájara"): (28.3500, -14.1070),
    ("Fuerteventura", "Antigua"): (28.4230, -14.0120),
    ("Fuerteventura", "Tuineje"): (28.3230, -14.0500),
    ("Fuerteventura", "Betancuria"): (28.4250, -14.0560),

    # La Gomera
    ("La Gomera", "San Sebastián de La Gomera"): (28.0910, -17.1100),
    ("La Gomera", "Vallehermoso"): (28.1800, -17.2650),
    ("La Gomera", "Alajeró"): (28.0640, -17.2400),
    ("La Gomera", "Hermigua"): (28.1660, -17.1940),
    ("La Gomera", "Agulo"): (28.1870, -17.1940),
    ("La Gomera", "Valle Gran Rey"): (28.1110, -17.3350),

    # Atlántico
    ("Atlántico-Canarias", "Atlántico-Canarias"): (28.3000, -16.5000),
}


CRITICALITY_WEIGHT = {
    "hospital": 5,
    "aeropuerto": 5,
    "puerto": 4,
    "emergencias": 4,
    "telecom": 4,
    "subestacion": 4,
    "agua": 4,
    "albergue": 3,
    "polideportivo": 3,
    "carretera": 3
}


EMERGENCY_INFRASTRUCTURES = [
    # TENERIFE
    {
        "nombre": "Hospital Universitario de Canarias",
        "tipo": "hospital",
        "lat": 28.4526,
        "lon": -16.2922,
        "municipio": "San Cristóbal de La Laguna",
        "isla": "Tenerife",
        "criticidad": "muy alta",
        "note": "Hospital de referencia"
    },
    {
        "nombre": "Hospital Universitario Nuestra Señora de Candelaria",
        "tipo": "hospital",
        "lat": 28.4417,
        "lon": -16.2806,
        "municipio": "Santa Cruz de Tenerife",
        "isla": "Tenerife",
        "criticidad": "muy alta",
        "note": "Hospital de referencia"
    },
    {
        "nombre": "Aeropuerto Tenerife Norte",
        "tipo": "aeropuerto",
        "lat": 28.4827,
        "lon": -16.3415,
        "municipio": "San Cristóbal de La Laguna",
        "isla": "Tenerife",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Aeropuerto Tenerife Sur",
        "tipo": "aeropuerto",
        "lat": 28.0445,
        "lon": -16.5725,
        "municipio": "Granadilla de Abona",
        "isla": "Tenerife",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Puerto de Santa Cruz de Tenerife",
        "tipo": "puerto",
        "lat": 28.4705,
        "lon": -16.2365,
        "municipio": "Santa Cruz de Tenerife",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Pabellón Roberto Estrello",
        "tipo": "polideportivo",
        "lat": 28.4917,
        "lon": -16.3150,
        "municipio": "Santa Cruz de Tenerife",
        "isla": "Tenerife",
        "criticidad": "media"
    },
    {
        "nombre": "Centro Coordinador Insular Tenerife",
        "tipo": "emergencias",
        "lat": 28.4630,
        "lon": -16.2510,
        "municipio": "Santa Cruz de Tenerife",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Subestación Granadilla",
        "tipo": "subestacion",
        "lat": 28.0840,
        "lon": -16.5760,
        "municipio": "Granadilla de Abona",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Nodo telecom Izaña",
        "tipo": "telecom",
        "lat": 28.3000,
        "lon": -16.5110,
        "municipio": "La Orotava",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Depósito estratégico de agua norte Tenerife",
        "tipo": "agua",
        "lat": 28.4040,
        "lon": -16.5600,
        "municipio": "La Orotava",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Polideportivo de Icod",
        "tipo": "albergue",
        "lat": 28.3675,
        "lon": -16.7140,
        "municipio": "Icod de los Vinos",
        "isla": "Tenerife",
        "criticidad": "media"
    },
    {
        "nombre": "Enlace TF-1 Candelaria",
        "tipo": "carretera",
        "lat": 28.3540,
        "lon": -16.3690,
        "municipio": "Candelaria",
        "isla": "Tenerife",
        "criticidad": "alta"
    },
    {
        "nombre": "Enlace TF-5 La Orotava",
        "tipo": "carretera",
        "lat": 28.3910,
        "lon": -16.5400,
        "municipio": "La Orotava",
        "isla": "Tenerife",
        "criticidad": "alta"
    },

    # LA PALMA
    {
        "nombre": "Hospital General de La Palma",
        "tipo": "hospital",
        "lat": 28.6510,
        "lon": -17.7830,
        "municipio": "Breña Alta",
        "isla": "La Palma",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Aeropuerto de La Palma",
        "tipo": "aeropuerto",
        "lat": 28.6265,
        "lon": -17.7556,
        "municipio": "Villa de Mazo",
        "isla": "La Palma",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Puerto de Santa Cruz de La Palma",
        "tipo": "puerto",
        "lat": 28.6819,
        "lon": -17.7648,
        "municipio": "Santa Cruz de La Palma",
        "isla": "La Palma",
        "criticidad": "alta"
    },
    {
        "nombre": "Polideportivo Municipal de Los Llanos",
        "tipo": "polideportivo",
        "lat": 28.6562,
        "lon": -17.9116,
        "municipio": "Los Llanos de Aridane",
        "isla": "La Palma",
        "criticidad": "media"
    },
    {
        "nombre": "Campo de Fútbol de El Paso",
        "tipo": "albergue",
        "lat": 28.6514,
        "lon": -17.8797,
        "municipio": "El Paso",
        "isla": "La Palma",
        "criticidad": "media"
    },
    {
        "nombre": "Subestación Los Guinchos",
        "tipo": "subestacion",
        "lat": 28.6470,
        "lon": -17.7600,
        "municipio": "Breña Alta",
        "isla": "La Palma",
        "criticidad": "alta"
    },

    # EL HIERRO
    {
        "nombre": "Hospital Insular Nuestra Señora de los Reyes",
        "tipo": "hospital",
        "lat": 27.8060,
        "lon": -17.9150,
        "municipio": "Valverde",
        "isla": "El Hierro",
        "criticidad": "alta"
    },
    {
        "nombre": "Puerto de La Estaca",
        "tipo": "puerto",
        "lat": 27.7720,
        "lon": -17.9030,
        "municipio": "Valverde",
        "isla": "El Hierro",
        "criticidad": "alta"
    },
    {
        "nombre": "Aeropuerto de El Hierro",
        "tipo": "aeropuerto",
        "lat": 27.8148,
        "lon": -17.8871,
        "municipio": "Valverde",
        "isla": "El Hierro",
        "criticidad": "alta"
    },

    # GRAN CANARIA
    {
        "nombre": "Hospital Universitario de Gran Canaria Dr. Negrín",
        "tipo": "hospital",
        "lat": 28.1270,
        "lon": -15.4450,
        "municipio": "Las Palmas de Gran Canaria",
        "isla": "Gran Canaria",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Aeropuerto de Gran Canaria",
        "tipo": "aeropuerto",
        "lat": 27.9319,
        "lon": -15.3866,
        "municipio": "Ingenio",
        "isla": "Gran Canaria",
        "criticidad": "muy alta"
    },
    {
        "nombre": "Puerto de La Luz",
        "tipo": "puerto",
        "lat": 28.1410,
        "lon": -15.4170,
        "municipio": "Las Palmas de Gran Canaria",
        "isla": "Gran Canaria",
        "criticidad": "muy alta"
    },

    # LANZAROTE
    {
        "nombre": "Hospital Universitario Doctor José Molina Orosa",
        "tipo": "hospital",
        "lat": 28.9670,
        "lon": -13.5660,
        "municipio": "Arrecife",
        "isla": "Lanzarote",
        "criticidad": "alta"
    },
    {
        "nombre": "Aeropuerto César Manrique-Lanzarote",
        "tipo": "aeropuerto",
        "lat": 28.9455,
        "lon": -13.6052,
        "municipio": "San Bartolomé",
        "isla": "Lanzarote",
        "criticidad": "alta"
    },
    {
        "nombre": "Puerto de Arrecife",
        "tipo": "puerto",
        "lat": 28.9600,
        "lon": -13.5500,
        "municipio": "Arrecife",
        "isla": "Lanzarote",
        "criticidad": "alta"
    },

    # FUERTEVENTURA
    {
        "nombre": "Hospital General de Fuerteventura",
        "tipo": "hospital",
        "lat": 28.4980,
        "lon": -13.8670,
        "municipio": "Puerto del Rosario",
        "isla": "Fuerteventura",
        "criticidad": "alta"
    },
    {
        "nombre": "Aeropuerto de Fuerteventura",
        "tipo": "aeropuerto",
        "lat": 28.4527,
        "lon": -13.8638,
        "municipio": "Puerto del Rosario",
        "isla": "Fuerteventura",
        "criticidad": "alta"
    },

    # LA GOMERA
    {
        "nombre": "Hospital Nuestra Señora de Guadalupe",
        "tipo": "hospital",
        "lat": 28.0910,
        "lon": -17.1120,
        "municipio": "San Sebastián de La Gomera",
        "isla": "La Gomera",
        "criticidad": "alta"
    },
    {
        "nombre": "Puerto de San Sebastián de La Gomera",
        "tipo": "puerto",
        "lat": 28.0915,
        "lon": -17.1110,
        "municipio": "San Sebastián de La Gomera",
        "isla": "La Gomera",
        "criticidad": "alta"
    }
]


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


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


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


def classify_municipality(lat, lon, island):
    candidates = MUNICIPALITIES_BY_ISLAND.get(island, [])
    if not candidates:
        return None

    best_name = None
    best_dist = None

    for muni in candidates:
        centroid = MUNICIPALITY_CENTROIDS.get((island, muni))
        if not centroid:
            continue
        d = haversine_km(lat, lon, centroid[0], centroid[1])
        if best_dist is None or d < best_dist:
            best_dist = d
            best_name = muni

    return best_name


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

            island = classify_island(lat, lon)
            municipio = classify_municipality(lat, lon, island)

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
                "isla": island,
                "municipio": municipio,
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

    eventos = []
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

            island = classify_island(lat, lon)
            municipio = classify_municipality(lat, lon, island)

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
                "isla": island,
                "municipio": municipio,
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
        island = classify_island(lat, lon)

        eventos.append({
            "id": feature.get("id"),
            "lat": lat,
            "lon": lon,
            "profundidad_km": depth,
            "magnitud": props.get("mag", 0) or 0,
            "localizacion": props.get("place", "Canarias"),
            "datetime_iso": datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(),
            "source": "USGS",
            "isla": island
        })

    return eventos


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


def compute_baseline(events_recent, island_name=None, municipio=None):
    eventos = list(events_recent)

    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

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
        "window_note": "Baseline experimental calculado sobre la ventana reciente disponible."
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


def detect_depth_migration(events_recent, island_name=None, municipio=None):
    eventos = list(events_recent)

    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

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
            score = 0
            drivers.append("no se observa un desplazamiento vertical claro de la sismicidad")

    shallow_recent = len([e for e in last_72h if e["profundidad_km"] < 10])
    total_recent = len(last_72h)
    shallow_ratio = round(shallow_recent / total_recent, 2) if total_recent > 0 else 0

    return {
        "headline": trend.capitalize(),
        "trend": trend,
        "color": color,
        "score": score,
        "metrics": {
            "prof_media_72h_km": mean_72h,
            "prof_media_7d_km": mean_7d,
            "shift_towards_surface_km": shift_km,
            "shallow_ratio_72h": shallow_ratio,
            "eventos_72h": total_recent
        },
        "drivers": drivers,
        "note": "Detector experimental de migración sísmica en profundidad."
    }


def detect_regime_change(events_recent, island_name=None, municipio=None):
    eventos = list(events_recent)

    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

    last_24h = events_in_hours(eventos, 24)
    last_7d = events_in_days(eventos, 7)
    last_30d = events_in_days(eventos, 30)

    baseline = compute_baseline(events_recent, island_name, municipio)
    acceleration = compute_acceleration(eventos)
    migration = detect_depth_migration(eventos, island_name, municipio)

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

    if mag_mean_30d >= 1.8:
        bullets.append("magnitud media reciente destacable")

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
            "migration_trend": migration["trend"]
        },
        "drivers": bullets,
        "note": "Detector experimental de cambio de régimen."
    }


def compute_risklab_index(events_recent, island_name=None, municipio=None):
    eventos = list(events_recent)

    if island_name and island_name != "Todas":
        eventos = [e for e in eventos if e["isla"] == island_name]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

    e24 = len(events_in_hours(eventos, 24))
    e7d = len(events_in_days(eventos, 7))
    e30d = events_in_days(eventos, 30)

    mmedia_30d = round(sum(e["magnitud"] for e in e30d) / len(e30d), 2) if e30d else 0
    pmedia_30d = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 2) if e30d else 0

    accel = compute_acceleration(eventos)["ratio"]
    baseline = compute_baseline(events_recent, island_name, municipio)
    migration = detect_depth_migration(eventos, island_name, municipio)

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


def compute_anomaly_signal(recent, island=None, municipio=None):
    eventos = list(recent)

    if island and island != "Todas":
        eventos = [e for e in eventos if e["isla"] == island]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

    last_24h = events_in_hours(eventos, 24)
    last_7d = events_in_days(eventos, 7)

    baseline = compute_baseline(recent, island, municipio)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0

    deviation_score = min((len(last_7d) / baseline_7d) * 20, 30)

    accel_data = compute_acceleration(eventos)
    accel_score = min(accel_data["ratio"] * 8, 20)

    magnitudes = [e["magnitud"] for e in last_7d if e.get("magnitud") is not None]
    mag_mean = (sum(magnitudes) / len(magnitudes)) if magnitudes else 0
    mag_score = min(mag_mean * 5, 10)

    swarm_score = 0
    if len(last_24h) >= 10:
        swarm_score = 15
    elif len(last_24h) >= 5:
        swarm_score = 8

    migration = detect_depth_migration(eventos, island, municipio)
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


def auto_interpretation(events_recent, island_name="Canarias", municipio=None):
    eventos = list(events_recent)

    if island_name and island_name != "Canarias":
        eventos = [e for e in eventos if e["isla"] == island_name]

    if municipio and municipio != "Todos":
        eventos = [e for e in eventos if e.get("municipio") == municipio]

    e24 = events_in_hours(eventos, 24)
    e72 = events_in_hours(eventos, 72)
    e7d = events_in_days(eventos, 7)
    e30d = events_in_days(eventos, 30)

    n24 = len(e24)
    n72 = len(e72)
    n7d = len(e7d)

    mmax = max((e["magnitud"] for e in e30d), default=0)
    pmedia = round(sum(e["profundidad_km"] for e in e30d) / len(e30d), 1) if e30d else 0

    acceleration = compute_acceleration(eventos)
    baseline = compute_baseline(eventos, island_name if island_name != "Canarias" else None, municipio)
    baseline_7d = baseline["media_7d"] if baseline["media_7d"] > 0 else 1.0
    deviation_ratio = round(n7d / baseline_7d, 2)
    regime = detect_regime_change(eventos, island_name if island_name != "Canarias" else None, municipio)
    migration = detect_depth_migration(eventos, island_name if island_name != "Canarias" else None, municipio)

    swarm = detect_swarm_candidates(eventos)
    swarm_text = ""
    if swarm:
        top_swarm = swarm[0]
        swarm_text = f" Se detecta además un posible enjambre experimental con {top_swarm['count']} eventos."

    scope_label = municipio if municipio and municipio != "Todos" else island_name

    fragments = []

    if n24 == 0 and n7d == 0:
        fragments.append(f"No se observan señales destacadas en la ventana reciente para {scope_label}.")
    else:
        fragments.append(
            f"En {scope_label} se registran {n24} eventos en 24 horas, {n7d} en 7 días y una magnitud máxima reciente de {mmax:.1f}."
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

    if migration["trend"] == "migración superficial moderada":
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


def grouped_summary_by_island(events_recent):
    summary = {}
    for isla in [
        "Tenerife", "La Palma", "El Hierro", "Gran Canaria",
        "Lanzarote", "Fuerteventura", "La Gomera", "Atlántico-Canarias"
    ]:
        live = [e for e in events_recent if e["isla"] == isla]

        risk = compute_risklab_index(live, isla) if live else {
            "value": 0,
            "signal": "Índice RiskLab bajo",
            "baseline": {"media_7d": 0},
            "components": {"desviacion_vs_baseline_7d": 0, "migration_trend": "sin datos"}
        }

        summary[isla] = {
            "eventos_24h": len(events_in_hours(live, 24)),
            "eventos_72h": len(events_in_hours(live, 72)),
            "eventos_7d": len(events_in_days(live, 7)),
            "eventos_10d": len(events_in_days(live, 10)),
            "eventos_30d": len(events_in_days(live, 30)),
            "magnitud_max": round(max((x["magnitud"] for x in live), default=0), 1),
            "risklab_index": risk["value"],
            "risklab_signal": risk["signal"],
            "baseline_7d": risk["baseline"]["media_7d"],
            "desviacion_vs_baseline_7d": risk["components"]["desviacion_vs_baseline_7d"],
            "migration_trend": risk["components"]["migration_trend"]
        }
    return summary


def filter_infrastructures(island_name=None, municipio=None):
    data = EMERGENCY_INFRASTRUCTURES[:]

    if island_name and island_name != "Todas":
        data = [x for x in data if x["isla"] == island_name]

    if municipio and municipio != "Todos":
        data = [x for x in data if x["municipio"] == municipio]

    return data


def recent_event_centroid(events_recent):
    recent = events_in_days(events_recent, 7)
    if not recent:
        return None

    lat = sum(e["lat"] for e in recent) / len(recent)
    lon = sum(e["lon"] for e in recent) / len(recent)

    return {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "count": len(recent)
    }


def nearest_infrastructure_to_centroid(events_recent, infrastructures):
    centroid = recent_event_centroid(events_recent)
    if not centroid or not infrastructures:
        return None

    best = None
    best_dist = None

    for infra in infrastructures:
        d = haversine_km(centroid["lat"], centroid["lon"], infra["lat"], infra["lon"])
        if best_dist is None or d < best_dist:
            best_dist = d
            best = dict(infra)
            best["distancia_km"] = round(d, 2)

    return best


def exposed_infrastructures(events_recent, infrastructures, radius_km=15):
    centroid = recent_event_centroid(events_recent)
    if not centroid:
        return []

    exposed = []
    for infra in infrastructures:
        d = haversine_km(centroid["lat"], centroid["lon"], infra["lat"], infra["lon"])
        if d <= radius_km:
            item = dict(infra)
            item["distancia_km"] = round(d, 2)
            exposed.append(item)

    exposed.sort(key=lambda x: (x["distancia_km"], -CRITICALITY_WEIGHT.get(x["tipo"], 1)))
    return exposed


def territorial_summary(island, anomaly, infrastructures, events_recent):
    infra_isla = [i for i in infrastructures if i["isla"] == island]
    tipos = sorted(list(set(i["tipo"] for i in infra_isla)))
    expuestas = exposed_infrastructures(events_recent, infra_isla, radius_km=18)
    nearest = nearest_infrastructure_to_centroid(events_recent, infra_isla)

    lectura = "actividad dentro de parámetros habituales"
    if anomaly["nivel"] == "moderada":
        lectura = "actividad ligeramente superior al baseline reciente con revisión territorial recomendada"
    if anomaly["nivel"] == "marcada":
        lectura = "actividad anómala que merece seguimiento reforzado sobre infraestructuras y soporte logístico"

    return {
        "isla": island,
        "infraestructuras": len(infra_isla),
        "tipos": tipos,
        "nivel_anomalia": anomaly["nivel"],
        "lectura": lectura,
        "expuestas_7d": len(expuestas),
        "infra_mas_cercana": nearest
    }


def municipality_operational_summary(events_recent, infrastructures, island_name, municipio):
    eventos = [e for e in events_recent if e["isla"] == island_name and e.get("municipio") == municipio]
    infra = [x for x in infrastructures if x["isla"] == island_name and x["municipio"] == municipio]

    return {
        "municipio": municipio,
        "isla": island_name,
        "eventos_7d": len(events_in_days(eventos, 7)),
        "eventos_30d": len(events_in_days(eventos, 30)),
        "magnitud_max_30d": round(max((e["magnitud"] for e in eventos), default=0), 1),
        "infraestructuras_criticas": len(infra),
        "tipos": sorted(list(set(x["tipo"] for x in infra)))
    }


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


@app.route("/api/risklab-summary")
def api_risklab_summary():
    try:
        recent = parse_ign_canarias()
        return jsonify({
            "ok": True,
            "summary": grouped_summary_by_island(recent)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "summary": {}
        }), 500


@app.route("/api/emergency-infrastructures")
def api_emergency_infrastructures():
    try:
        island_name = request.args.get("island")
        municipio = request.args.get("municipio")

        data = filter_infrastructures(island_name, municipio)

        return jsonify({
            "ok": True,
            "count": len(data),
            "infraestructuras": data,
            "note": "Inventario prototipo RiskLab inspirado en lógica operativa territorial."
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
        municipio = request.args.get("municipio", "Todos")

        if island_name == "Todas":
            island_name = None

        recent = parse_ign_canarias()

        recent_filtered = recent[:]
        if island_name:
            recent_filtered = [e for e in recent_filtered if e["isla"] == island_name]

        municipios_disponibles = []
        if island_name:
            municipios_disponibles = MUNICIPALITIES_BY_ISLAND.get(island_name, [])
        else:
            municipios_disponibles = []

        if municipio and municipio != "Todos":
            recent_filtered = [e for e in recent_filtered if e.get("municipio") == municipio]

        summary = grouped_summary_by_island(recent)
        if island_name:
            summary = {island_name: summary.get(island_name, {})}

        risklab_index = compute_risklab_index(recent_filtered, island_name, municipio)
        interpretation = auto_interpretation(recent_filtered, island_name or "Canarias", municipio)
        depth = depth_profile(events_in_days(recent_filtered, 30))
        compare = compare_windows(recent_filtered)
        acceleration = compute_acceleration(recent_filtered)
        baseline = compute_baseline(recent_filtered, island_name, municipio)
        regime = detect_regime_change(recent_filtered, island_name, municipio)
        migration = detect_depth_migration(recent_filtered, island_name, municipio)
        anomaly = compute_anomaly_signal(recent_filtered, island_name, municipio)

        serie = serie_temporal(events_in_days(recent_filtered, 30))

        enjambres = detect_swarm_candidates(recent)
        if island_name:
            enjambres = [c for c in enjambres if c["isla"] == island_name]

        infra = filter_infrastructures(island_name, municipio)
        infra_expuestas = exposed_infrastructures(recent_filtered, infra, radius_km=18)

        territorial = None
        if island_name:
            territorial = territorial_summary(island_name, anomaly, EMERGENCY_INFRASTRUCTURES, recent_filtered)

        municipio_resumen = None
        if island_name and municipio and municipio != "Todos":
            municipio_resumen = municipality_operational_summary(recent, EMERGENCY_INFRASTRUCTURES, island_name, municipio)

        return jsonify({
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
            "infra_expuestas": infra_expuestas,
            "municipio_resumen": municipio_resumen,
            "municipios_disponibles": municipios_disponibles
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
            "candidatos_enjambre": [],
            "infraestructuras": [],
            "infra_expuestas": [],
            "municipio_resumen": None,
            "municipios_disponibles": []
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
            "html_length": len(html_text)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)