"""Team names.

Canonical names follow football-data.co.uk (the main data source), so files
from that site can be used without any renaming. Every other source is mapped
onto these names through ALIASES.
"""

from __future__ import annotations

# canonical name -> (English display name, Arabic display name)
DISPLAY = {
    "Alaves": ("Alavés", "ألافيس"),
    "Almeria": ("Almería", "ألميريا"),
    "Ath Bilbao": ("Athletic Club", "أتلتيك بلباو"),
    "Ath Madrid": ("Atlético Madrid", "أتلتيكو مدريد"),
    "Barcelona": ("Barcelona", "برشلونة"),
    "Betis": ("Real Betis", "ريال بيتيس"),
    "Cadiz": ("Cádiz", "قادش"),
    "Celta": ("Celta Vigo", "سيلتا فيغو"),
    "Cordoba": ("Córdoba", "قرطبة"),
    "Eibar": ("Eibar", "إيبار"),
    "Elche": ("Elche", "إلتشي"),
    "Espanol": ("Espanyol", "إسبانيول"),
    "Getafe": ("Getafe", "خيتافي"),
    "Girona": ("Girona", "جيرونا"),
    "Granada": ("Granada", "غرناطة"),
    "Huesca": ("Huesca", "هويسكا"),
    "La Coruna": ("Deportivo La Coruña", "ديبورتيفو لاكورونيا"),
    "Las Palmas": ("Las Palmas", "لاس بالماس"),
    "Leganes": ("Leganés", "ليغانيس"),
    "Levante": ("Levante", "ليفانتي"),
    "Malaga": ("Málaga", "ملقة"),
    "Mallorca": ("Mallorca", "مايوركا"),
    "Osasuna": ("Osasuna", "أوساسونا"),
    "Oviedo": ("Real Oviedo", "ريال أوفييدو"),
    "Real Madrid": ("Real Madrid", "ريال مدريد"),
    "Santander": ("Racing Santander", "راسينغ سانتاندير"),
    "Sevilla": ("Sevilla", "إشبيلية"),
    "Sociedad": ("Real Sociedad", "ريال سوسيداد"),
    "Sp Gijon": ("Sporting Gijón", "سبورتينغ خيخون"),
    "Valencia": ("Valencia", "فالنسيا"),
    "Valladolid": ("Valladolid", "بلد الوليد"),
    "Vallecano": ("Rayo Vallecano", "رايو فاييكانو"),
    "Villarreal": ("Villarreal", "فياريال"),
    "Zaragoza": ("Zaragoza", "سرقسطة"),
}

# other spellings -> canonical name
ALIASES = {
    # football-data.co.uk historical spelling
    "Villareal": "Villarreal",
    # openfootball
    "Athletic Club": "Ath Bilbao",
    "CA Osasuna": "Osasuna",
    "Club Atlético de Madrid": "Ath Madrid",
    "Deportivo Alavés": "Alaves",
    "Elche CF": "Elche",
    "FC Barcelona": "Barcelona",
    "Getafe CF": "Getafe",
    "Levante UD": "Levante",
    "Málaga CF": "Malaga",
    "RC Celta de Vigo": "Celta",
    "RC Deportivo La Coruña": "La Coruna",
    "RCD Espanyol de Barcelona": "Espanol",
    "Rayo Vallecano de Madrid": "Vallecano",
    "Real Betis Balompié": "Betis",
    "Real Madrid CF": "Real Madrid",
    "Real Racing Club de Santander": "Santander",
    "Real Sociedad de Fútbol": "Sociedad",
    "Sevilla FC": "Sevilla",
    "Valencia CF": "Valencia",
    "Villarreal CF": "Villarreal",
    "Girona FC": "Girona",
    "RCD Mallorca": "Mallorca",
    "Real Oviedo": "Oviedo",
    # footballwebpages.co.uk / common English names
    "Athletic Bilbao": "Ath Bilbao",
    "Atlético Madrid": "Ath Madrid",
    "Atletico Madrid": "Ath Madrid",
    "Alavés": "Alaves",
    "Real Betis": "Betis",
    "Real Sociedad": "Sociedad",
    "Celta Vigo": "Celta",
    "Deportivo de A Coruña": "La Coruna",
    "Deportivo La Coruña": "La Coruna",
    "Deportivo La Coruna": "La Coruna",
    "Espanyol": "Espanol",
    "Rayo Vallecano": "Vallecano",
    "Racing de Santander": "Santander",
    "Racing Santander": "Santander",
    "Málaga": "Malaga",
    # SportRadar
    "Real Betis Seville": "Betis",
    "Malaga CF": "Malaga",
    "Real Sociedad San Sebastian": "Sociedad",
    "Espanyol Barcelona": "Espanol",
    "RC Deportivo de A Coruna": "La Coruna",
    "Atletico Madrid": "Ath Madrid",
    "Deportivo Alaves": "Alaves",
    "CA Osasuna": "Osasuna",
    # StatsBomb
    "Barcelona": "Barcelona",
    "Real Madrid": "Real Madrid",
    "Atlético Madrid": "Ath Madrid",
    "RC Deportivo La Coruña": "La Coruna",
    "Real Valladolid": "Valladolid",
    "Sporting Gijón": "Sp Gijon",
    "Granada": "Granada",
    "Eibar": "Eibar",
    "Las Palmas": "Las Palmas",
}


def canonical(name: str) -> str:
    """Return the canonical (football-data.co.uk) name for any spelling."""
    name = str(name).strip()
    if name in DISPLAY:
        return name
    return ALIASES.get(name, name)


def english(name: str) -> str:
    return DISPLAY.get(canonical(name), (name, name))[0]


def arabic(name: str) -> str:
    return DISPLAY.get(canonical(name), (name, name))[1]
