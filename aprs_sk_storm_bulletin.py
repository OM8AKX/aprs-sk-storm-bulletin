#!/usr/bin/env python3
"""
APRS-IS Storm Bulletin for Slovakia
===================================
Skript kontroluje:
  1. Oficiálne výstrahy SHMÚ cez MeteoAlarm CAP feed
  2. Aktuálne blesky z Blitzortung (verejný WebSocket)

Ak nájde aktívnu výstrahu pred búrkami ALEBO dostatok bleskov nad SK,
pošle APRS bulletin.

Autor: OM8AKX
Licencia: MIT
"""

import os
import sys
import time
import json
import logging
import hashlib
import asyncio
from typing import List, Dict, Tuple

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

try:
    import websockets
except ImportError:
    print("Chýba knižnica 'websockets'. Nainštaluj: pip install websockets")
    sys.exit(1)


# ======================== KONFIGURÁCIA ========================
CALLSIGN = os.getenv("APRS_CALLSIGN", "OM8AKX")
PASSCODE = os.getenv("APRS_PASSCODE", "")
APRS_SERVER = os.getenv("APRS_SERVER", "euro.aprs2.net")
APRS_PORT = int(os.getenv("APRS_PORT", "14580"))

# Bulletin
BULLETIN_ID = "1"
BULLETIN_GROUP = ""          # napr. "WX" pre group bulletin
MAX_BULLETIN_LEN = 67

# MeteoAlarm
METEOALARM_URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-slovakia"
USE_METEOALARM = os.getenv("USE_METEOALARM", "1") == "1"

# Blitzortung
USE_BLITZORTUNG = os.getenv("USE_BLITZORTUNG", "1") == "1"
BLITZ_LISTEN_SECONDS = int(os.getenv("BLITZ_LISTEN_SECONDS", "45"))  # koľko sekúnd počúvať
BLITZ_MIN_STRIKES = int(os.getenv("BLITZ_MIN_STRIKES", "5"))         # min. počet úderov na trigger
BLITZ_MAX_AGE_SEC = int(os.getenv("BLITZ_MAX_AGE_SEC", "600"))       # max. vek úderu (10 min)

# Bounding box Slovenska (približne)
SK_LAT_MIN, SK_LAT_MAX = 47.73, 49.62
SK_LON_MIN, SK_LON_MAX = 16.84, 22.56

# Blitzortung WebSocket servery (rotujú)
WS_SERVERS = [
    "wss://ws1.blitzortung.org/",
    "wss://ws7.blitzortung.org/",
    "wss://ws8.blitzortung.org/",
    "wss://ws6.blitzortung.org/",
]

# Interval medzi rovnakými bulletinmi
MIN_RESEND_MINUTES = 30

LOG_LEVEL = logging.INFO
# ==============================================================


logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("aprs-storm")


def generate_passcode(callsign: str) -> int:
    """Vygeneruje APRS-IS passcode z callsignu."""
    call = callsign.split("-")[0].upper().strip()
    hash_val = 0x73E2
    for i in range(0, len(call), 2):
        hash_val ^= ord(call[i]) << 8
        if i + 1 < len(call):
            hash_val ^= ord(call[i + 1])
    return hash_val & 0x7FFF


def in_slovakia(lat: float, lon: float) -> bool:
    return SK_LAT_MIN <= lat <= SK_LAT_MAX and SK_LON_MIN <= lon <= SK_LON_MAX


# -------------------- MeteoAlarm --------------------

def fetch_storm_warnings() -> List[Dict]:
    """Stiahne výstrahy z MeteoAlarm a vráti len búrkové."""
    if not USE_METEOALARM:
        return []

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

            is_storm = (
                "Thunderstorm" in atype
                or atype.startswith("3;")
                or "búrk" in event
                or "thunderstorm" in event
                or "búrka" in headline.lower()
            )

            if is_storm:
                areas = [a.get("areaDesc") for a in info.get("area", []) if a.get("areaDesc")]
                storms.append({
                    "source": "meteoalarm",
                    "identifier": alert.get("identifier", ""),
                    "event": info.get("event", "Búrka"),
                    "headline": headline,
                    "severity": info.get("severity", "Unknown"),
                    "awareness_level": params.get("awareness_level", ""),
                    "areas": areas,
                })
                break

    return storms


# -------------------- Blitzortung --------------------

async def _listen_blitzortung(duration: int) -> List[Dict]:
    """Počúva Blitzortung WebSocket a zbiera údery nad SK."""
    strikes = []
    now_ns = time.time_ns()
    min_time_ns = now_ns - (BLITZ_MAX_AGE_SEC * 1_000_000_000)

    for server in WS_SERVERS:
        try:
            log.info(f"Blitzortung: pripájam sa na {server} ...")
            async with websockets.connect(
                server,
                ping_interval=20,
                ping_timeout=15,
                close_timeout=5,
                open_timeout=10,
            ) as ws:
                try:
                    await ws.send(json.dumps({"time": 0}))
                except Exception:
                    pass

                log.info(f"Blitzortung: počúvam {duration}s ...")
                end_time = time.time() + duration

                while time.time() < end_time:
                    try:
                        remaining = end_time - time.time()
                        if remaining <= 0:
                            break
                        raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5.0))
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        log.debug(f"recv error: {e}")
                        break

                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue

                    lat = data.get("lat")
                    lon = data.get("lon")
                    ts = data.get("time")

                    if lat is None or lon is None:
                        continue

                    try:
                        lat = float(lat)
                        lon = float(lon)
                    except (TypeError, ValueError):
                        continue

                    if not in_slovakia(lat, lon):
                        continue

                    if ts is not None:
                        try:
                            if int(ts) < min_time_ns:
                                continue
                        except (TypeError, ValueError):
                            pass

                    strikes.append({"lat": lat, "lon": lon, "time": ts})

                log.info(f"Blitzortung: zachytených {len(strikes)} úderov nad SK")
                return strikes

        except Exception as e:
            log.warning(f"Blitzortung server {server} zlyhal: {e}")
            continue

    log.warning("Blitzortung: žiadny server nedostupný")
    return strikes


def fetch_blitzortung_strikes() -> Tuple[int, List[Dict]]:
    """Synchronný wrapper – vráti (počet, zoznam) úderov nad SK."""
    if not USE_BLITZORTUNG:
        return 0, []

    try:
        strikes = asyncio.run(_listen_blitzortung(BLITZ_LISTEN_SECONDS))
        return len(strikes), strikes
    except Exception as e:
        log.error(f"Blitzortung chyba: {e}")
        return 0, []


# -------------------- Bulletin text --------------------

def build_bulletin_text(storms: List[Dict], blitz_count: int) -> str:
    """Vytvorí krátky text bulletinu (max 67 znakov)."""
    parts = []

    if storms:
        severity_order = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
        top = sorted(storms, key=lambda s: severity_order.get(s["severity"], 0), reverse=True)[0]

        level = top.get("awareness_level", "")
        color = ""
        if "yellow" in level.lower() or "2;" in level:
            color = "žltá"
        elif "orange" in level.lower() or "3;" in level:
            color = "oranžová"
        elif "red" in level.lower() or "4;" in level:
            color = "červená"

        areas = top.get("areas", [])
        area_str = ", ".join(areas[:2])
        if len(areas) > 2:
            area_str += f" +{len(areas)-2}"

        if color:
            parts.append(f"SHMU {color} búrky: {area_str}")
        else:
            parts.append(f"SHMU búrky: {area_str}")

    if blitz_count >= BLITZ_MIN_STRIKES:
        parts.append(f"Blitzortung {blitz_count} úderov/SK")

    if not parts:
        return ""

    text = " | ".join(parts)

    if len(text) > MAX_BULLETIN_LEN:
        text = text[: MAX_BULLETIN_LEN - 3] + "..."

    return text


# -------------------- APRS --------------------

def send_aprs_bulletin(text: str, callsign: str, passcode: str) -> bool:
    if not text:
        return False

    if BULLETIN_GROUP:
        addr = f"BLN{BULLETIN_ID}{BULLETIN_GROUP[:5]:<5}"
    else:
        addr = f"BLN{BULLETIN_ID}     "

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
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_bulletin_state")


def should_send(text: str) -> bool:
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


# -------------------- main --------------------

def main():
    log.info("=== APRS SK Storm Bulletin (MeteoAlarm + Blitzortung) ===")

    passcode = PASSCODE or str(generate_passcode(CALLSIGN))
    if not PASSCODE:
        log.info(f"Passcode vygenerovaný pre {CALLSIGN}: {passcode}")

    # 1) MeteoAlarm
    storms = fetch_storm_warnings()
    log.info(f"MeteoAlarm: {len(storms)} búrkových výstrah")
    for s in storms:
        log.info(f"  - {s['severity']}: {s['event']} | {', '.join(s['areas'][:4])}")

    # 2) Blitzortung
    blitz_count, strikes = fetch_blitzortung_strikes()
    log.info(f"Blitzortung: {blitz_count} úderov nad SK (min. threshold={BLITZ_MIN_STRIKES})")

    # Rozhodnutie
    has_meteo = len(storms) > 0
    has_blitz = blitz_count >= BLITZ_MIN_STRIKES

    if not has_meteo and not has_blitz:
        log.info("Žiadna aktívna búrková situácia – končím")
        return 0

    text = build_bulletin_text(storms, blitz_count)
    log.info(f"Text bulletinu ({len(text)} znakov): {text}")

    if not should_send(text):
        return 0

    ok = send_aprs_bulletin(text, CALLSIGN, passcode)
    if ok:
        save_state(text)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
