#!/usr/bin/env python3
"""
APRS-IS Storm Bulletin for Slovakia
===================================
Skript kontroluje oficiálne výstrahy SHMÚ cez MeteoAlarm CAP feed.
Ak nájde aktívnu výstrahu pred búrkami (Thunderstorm), pošle APRS bulletin.

Autor: OM8AKX
Licencia: MIT
"""

import os
import sys
import time
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("Chýba knižnica 'requests'. Nainštaluj: pip install requests")
    sys.exit(1)

try:
    import aprslib
except ImportError:
    print("Chýba knižnica 'aprslib'. Nainštaluj: pip install aprslib")
    sys.exit(1)


# ======================== KONFIGURÁCIA ========================
# Odporúčané: nastav cez environment variables alebo config súbor

CALLSIGN = os.getenv("APRS_CALLSIGN", "OM8AKX")          # Tvoj callsign (bez SSID alebo s -SSID)
PASSCODE = os.getenv("APRS_PASSCODE", "")                 # APRS-IS passcode (vygeneruj na https://apps.magicbug.co.uk/passcode/)
APRS_SERVER = os.getenv("APRS_SERVER", "euro.aprs2.net")  # alebo rotate.aprs2.net
APRS_PORT = int(os.getenv("APRS_PORT", "14580"))

# Bulletin nastavenia
BULLETIN_ID = "1"          # BLN1 ... BLN9
BULLETIN_GROUP = ""        # prázdne = všeobecný bulletin, alebo napr. "WX" pre group bulletin
MAX_BULLETIN_LEN = 67      # podľa APRS špecifikácie

# Zdroj dát
METEOALARM_URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-slovakia"

# Ako často posielať ten istý bulletin (minúty) – aby sa nezahltil APRS-IS
MIN_RESEND_MINUTES = 30

# Logovanie
LOG_LEVEL = logging.INFO
# ==============================================================


logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("aprs-storm")


def generate_passcode(callsign: str) -> int:
    """Vygeneruje APRS-IS passcode z callsignu (oficiálny algoritmus)."""
    call = callsign.split("-")[0].upper().strip()
    hash_val = 0x73E2
    for i in range(0, len(call), 2):
        hash_val ^= ord(call[i]) << 8
        if i + 1 < len(call):
            hash_val ^= ord(call[i + 1])
    return hash_val & 0x7FFF


def fetch_storm_warnings() -> List[Dict]:
    """Stiahne výstrahy z MeteoAlarm a vráti len búrkové."""
    try:
        r = requests.get(METEOALARM_URL, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error(f"Chyba pri sťahovaní MeteoAlarm: {e}")
        return []

    storms = []
    for item in data.get("warnings", []):
        alert = item.get("alert", item)
        infos = alert.get("info", [])
        if not isinstance(infos, list):
            infos = [infos]

        for info in infos:
            params = {p.get("valueName"): p.get("value") for p in info.get("parameter", [])}
            atype = params.get("awareness_type", "")
            event = (info.get("event") or "").lower()
            headline = info.get("headline") or ""
            description = info.get("description") or ""

            # Thunderstorm = awareness_type "3; Thunderstorm"
            is_storm = (
                "Thunderstorm" in atype
                or atype.startswith("3;")
                or "búrk" in event
                or "thunderstorm" in event
                or "búrka" in headline.lower()
            )

            if is_storm:
                areas = []
                for area in info.get("area", []):
                    desc = area.get("areaDesc")
                    if desc:
                        areas.append(desc)

                storms.append({
                    "identifier": alert.get("identifier", ""),
                    "event": info.get("event", "Búrka"),
                    "headline": headline,
                    "description": description[:200],
                    "severity": info.get("severity", "Unknown"),
                    "certainty": info.get("certainty", ""),
                    "awareness_level": params.get("awareness_level", ""),
                    "areas": areas,
                    "onset": info.get("onset"),
                    "expires": info.get("expires"),
                    "language": info.get("language", ""),
                })
                break  # stačí jedna info blok

    return storms


def build_bulletin_text(storms: List[Dict]) -> str:
    """Vytvorí krátky text bulletinu (max 67 znakov)."""
    if not storms:
        return ""

    # Zoberieme najvyššiu závažnosť
    severity_order = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
    storms_sorted = sorted(storms, key=lambda s: severity_order.get(s["severity"], 0), reverse=True)
    top = storms_sorted[0]

    level = top.get("awareness_level", "")
    # "2; yellow; Moderate" -> "žltá" / "oranžová" / "červená"
    color = ""
    if "yellow" in level.lower() or "2;" in level:
        color = "žltá"
    elif "orange" in level.lower() or "3;" in level:
        color = "oranžová"
    elif "red" in level.lower() or "4;" in level:
        color = "červená"

    areas = top.get("areas", [])
    area_str = ", ".join(areas[:3])
    if len(areas) > 3:
        area_str += f" +{len(areas)-3}"

    # Krátky text
    if color:
        text = f"SHMU {color} výstraha pred búrkami: {area_str}"
    else:
        text = f"SHMU výstraha pred búrkami: {area_str}"

    # Orezanie na max dĺžku
    if len(text) > MAX_BULLETIN_LEN:
        text = text[: MAX_BULLETIN_LEN - 3] + "..."

    return text


def send_aprs_bulletin(text: str, callsign: str, passcode: str) -> bool:
    """Pošle bulletin do APRS-IS."""
    if not text:
        return False

    # Formát bulletinu podľa APRS špecifikácie
    # Všeobecný: :BLNn     :text
    # Group:     :BLNnGROUP:text  (GROUP max 5 znakov)
    if BULLETIN_GROUP:
        addr = f"BLN{BULLETIN_ID}{BULLETIN_GROUP[:5]:<5}"
    else:
        addr = f"BLN{BULLETIN_ID}     "

    # Packet: CALLSIGN>APRS,TCPIP*::ADDR:text
    packet = f"{callsign}>APRS,TCPIP*::{addr}:{text}"

    log.info(f"Posielam packet: {packet}")

    try:
        ais = aprslib.IS(callsign, passwd=str(passcode), host=APRS_SERVER, port=APRS_PORT)
        ais.connect()
        ais.sendall(packet)
        ais.close()
        log.info("Bulletin úspešne odoslaný do APRS-IS")
        return True
    except Exception as e:
        log.error(f"Chyba pri odosielaní do APRS-IS: {e}")
        return False


def get_state_file() -> str:
    """Cesta k súboru so stavom (aby sme neposielali stále to isté)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_bulletin_state")


def should_send(storms: List[Dict], text: str) -> bool:
    """Rozhodne, či poslať bulletin (nová situácia alebo uplynul čas)."""
    state_file = get_state_file()
    now = time.time()

    current_hash = hashlib.md5(text.encode()).hexdigest()

    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                last_hash, last_ts = f.read().strip().split("|")
                last_ts = float(last_ts)
                if last_hash == current_hash and (now - last_ts) < MIN_RESEND_MINUTES * 60:
                    log.info(f"Ten istý bulletin už bol poslaný pred {int((now-last_ts)/60)} min – preskakujem")
                    return False
        except Exception:
            pass

    return True


def save_state(text: str):
    state_file = get_state_file()
    h = hashlib.md5(text.encode()).hexdigest()
    with open(state_file, "w") as f:
        f.write(f"{h}|{time.time()}")


def main():
    log.info("=== APRS SK Storm Bulletin ===")

    # Passcode
    passcode = PASSCODE
    if not passcode:
        passcode = str(generate_passcode(CALLSIGN))
        log.info(f"Passcode vygenerovaný pre {CALLSIGN}: {passcode}")

    # Stiahni výstrahy
    storms = fetch_storm_warnings()
    log.info(f"Nájdených búrkových výstrah: {len(storms)}")

    if not storms:
        log.info("Žiadne aktívne výstrahy pred búrkami – končím")
        return 0

    for s in storms:
        log.info(f"  - {s['severity']}: {s['event']} | {', '.join(s['areas'][:5])}")

    text = build_bulletin_text(storms)
    log.info(f"Text bulletinu ({len(text)} znakov): {text}")

    if not should_send(storms, text):
        return 0

    ok = send_aprs_bulletin(text, CALLSIGN, passcode)
    if ok:
        save_state(text)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
