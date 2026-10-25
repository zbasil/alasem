"""Stable identifiers for teams and matches.

Team id: a 3-letter code that never changes (SportRadar's abbreviation for
every club it covers, our own code for the others). Every source spelling is
mapped to the canonical name in teams.py, then to the id here.

Match id: "<competition>-<season start year>-<home id>-<away id>", e.g.
"ESP1-2026-ATM-DEP". In a double round robin every ordered pair meets once
per season, so the id is unique and stays the same when the kick-off moves;
the season in the id keeps matches of different seasons apart. External ids
(SportRadar, StatsBomb ...) are kept beside it with their source.
"""

from __future__ import annotations

from .teams import DISPLAY, canonical

# canonical name -> (id, chart colour, kit colours (primary, secondary))
TEAMS = {
    "Alaves": ("ALA", "#2F6FD6", ("#1E5CB3", "#FFFFFF")),
    "Albacete": ("ALB", "#C8102E", ("#FFFFFF", "#C8102E")),
    "Compostela": ("CMP", "#2D63B3", ("#0055A4", "#FFFFFF")),
    "Extremadura": ("EXT", "#0E8A4A", ("#0E8A4A", "#FFFFFF")),
    "Lerida": ("LLE", "#2A5EAA", ("#0050A0", "#FFFFFF")),
    "Logrones": ("LOG", "#D9232E", ("#D9232E", "#FFFFFF")),
    "Merida": ("MER", "#C8102E", ("#C8102E", "#FFFFFF")),
    "Salamanca": ("SAL", "#6B6B6B", ("#FFFFFF", "#000000")),
    "Almeria": ("ALM", "#E3172D", ("#E3172D", "#FFFFFF")),
    "Ath Bilbao": ("ATH", "#E8202A", ("#E8202A", "#FFFFFF")),
    "Ath Madrid": ("ATM", "#D2232A", ("#D2232A", "#272E61")),
    "Barcelona": ("BAR", "#A50044", ("#A50044", "#004D98")),
    "Betis": ("RBB", "#0BB363", ("#0BB363", "#FFFFFF")),
    "Cadiz": ("CAD", "#E6C200", ("#FDE607", "#0045A5")),
    "Celta": ("RCC", "#62A8E5", ("#8AC3EE", "#FFFFFF")),
    "Cordoba": ("COR", "#0B7A3E", ("#0B7A3E", "#FFFFFF")),
    "Eibar": ("EIB", "#A6192E", ("#A6192E", "#1F3F8F")),
    "Elche": ("ELC", "#0F8A43", ("#FFFFFF", "#0F8A43")),
    "Espanol": ("ESP", "#1A86D0", ("#007FC8", "#FFFFFF")),
    "Getafe": ("GET", "#2D6FB7", ("#005999", "#FFFFFF")),
    "Gimnastic": ("GIM", "#D7001D", ("#D7001D", "#FFFFFF")),
    "Girona": ("GIR", "#DA291C", ("#DA291C", "#FFFFFF")),
    "Granada": ("GRA", "#C8102E", ("#C8102E", "#FFFFFF")),
    "Hercules": ("HER", "#2F65B5", ("#0055A4", "#FFFFFF")),
    "Huesca": ("HUE", "#3B55A3", ("#1F3F8F", "#A6192E")),
    "La Coruna": ("DEP", "#2B6CC4", ("#1B5BA7", "#FFFFFF")),
    "Las Palmas": ("LPA", "#E8C300", ("#FFE400", "#0055A5")),
    "Leganes": ("LEG", "#2C62B8", ("#0C4DA2", "#FFFFFF")),
    "Levante": ("LEV", "#B4053F", ("#B4053F", "#004B87")),
    "Malaga": ("MCF", "#4FA7DB", ("#4FA7DB", "#FFFFFF")),
    "Mallorca": ("MLL", "#E20613", ("#E20613", "#000000")),
    "Murcia": ("MUR", "#CF142B", ("#CF142B", "#FFFFFF")),
    "Numancia": ("NUM", "#E30613", ("#E30613", "#1F3F8F")),
    "Osasuna": ("OSA", "#D91A21", ("#D91A21", "#0A346F")),
    "Oviedo": ("OVI", "#1F5FB0", ("#0055A4", "#FFFFFF")),
    "Real Madrid": ("RMA", "#D9A400", ("#FFFFFF", "#FEBE10")),
    "Recreativo": ("REC", "#2E63B0", ("#0055A4", "#FFFFFF")),
    "Santander": ("RAC", "#00924A", ("#FFFFFF", "#00843D")),
    "Sevilla": ("SEV", "#E2001A", ("#FFFFFF", "#E2001A")),
    "Sociedad": ("RSO", "#1F78C8", ("#0067B1", "#FFFFFF")),
    "Sp Gijon": ("SPG", "#E30613", ("#E30613", "#FFFFFF")),
    "Tenerife": ("TEN", "#2350A8", ("#FFFFFF", "#003DA5")),
    "Valencia": ("VCF", "#F18A00", ("#FFFFFF", "#000000")),
    "Valladolid": ("VLL", "#7A3C9E", ("#6A2C91", "#FFFFFF")),
    "Vallecano": ("RVC", "#E53027", ("#FFFFFF", "#E53027")),
    "Villarreal": ("VIL", "#E8C800", ("#FFE667", "#005187")),
    "Xerez": ("XER", "#2D63B3", ("#005AAA", "#FFFFFF")),
    "Zaragoza": ("ZAR", "#2463B5", ("#FFFFFF", "#0057A8")),
}

# Arabic and English names for teams that are not in teams.DISPLAY
EXTRA_NAMES = {
    "Albacete": ("Albacete", "ألباسيتي"),
    "Compostela": ("Compostela", "كومبوستيلا"),
    "Extremadura": ("Extremadura", "إكستريمادورا"),
    "Lerida": ("Lleida", "ليريدا"),
    "Logrones": ("Logroñés", "لوغرونييس"),
    "Merida": ("Mérida", "ميريدا"),
    "Salamanca": ("Salamanca", "سالامانكا"),
    "Gimnastic": ("Gimnàstic", "خيمناستيك"),
    "Hercules": ("Hércules", "هيركوليس"),
    "Murcia": ("Real Murcia", "مورسيا"),
    "Numancia": ("Numancia", "نومانسيا"),
    "Recreativo": ("Recreativo Huelva", "ريكرياتيفو"),
    "Tenerife": ("Tenerife", "تينيريفي"),
    "Xerez": ("Xerez", "خيريز"),
}

ID_TO_NAME = {v[0]: k for k, v in TEAMS.items()}


def team_id(name: str) -> str:
    c = canonical(name)
    if c not in TEAMS:
        raise KeyError(f"unknown team '{name}' (canonical '{c}'): add it to zsc/registry.py")
    return TEAMS[c][0]


def team_name(tid: str) -> str:
    return ID_TO_NAME[tid]


def names(name: str) -> tuple[str, str]:
    c = canonical(name)
    if c in DISPLAY:
        return DISPLAY[c]
    return EXTRA_NAMES.get(c, (c, c))


def team_record(name: str) -> dict:
    c = canonical(name)
    tid, color, kit = TEAMS[c]
    en, ar = names(c)
    return {"id": tid, "canonical": c, "en": en, "ar": ar, "color": color, "kit": list(kit)}


def match_id(competition: str, season: int, home: str, away: str) -> str:
    return f"{competition}-{int(season)}-{team_id(home)}-{team_id(away)}"


def parse_match_id(mid: str) -> dict:
    comp, season, h, a = mid.split("-")
    return {"competition": comp, "season": int(season), "home_id": h, "away_id": a,
            "home": ID_TO_NAME[h], "away": ID_TO_NAME[a]}
