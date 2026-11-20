# APRS SK Storm Bulletin

Python skript, ktorý pri výskyte **búrok na území Slovenska** automaticky pošle bulletin do **APRS-IS**.

**Zdroje dát:**
1. **MeteoAlarm / SHMÚ** – oficiálne výstrahy
2. **Blitzortung** – reálne blesky (WebSocket)
3. **Open-Meteo** – predpoveď búrok (weather codes 95–99, bez API kľúča)

## Čo robí

1. Stiahne výstrahy zo Slovenska (MeteoAlarm)
2. Počúva Blitzortung ~40 s a počíta údery nad SK
3. Overí predpoveď Open-Meteo na 7 bodoch (BA, ZA, KE, BB, PO, NR, PP)
4. Ak nájde výstrahu **alebo** blesky **alebo** predpoveď búrok → pošle `BLN1` bulletin

Príklady:
```
SHMU žltá búrky: Žilina, Poprad
Blitz 12 úderov | OpenMeteo búrky: Košice,Prešov
OpenMeteo búrky: Bratislava,Nitra
```

## Spustenie na GitHub Actions

1. **Settings → Secrets and variables → Actions**
   - `APRS_CALLSIGN` = tvoj callsign
   - `APRS_PASSCODE` = passcode (https://apps.magicbug.co.uk/passcode/)

2. **Actions → SK Storm Bulletin → Run workflow** (test)

Beží automaticky každých 15 minút.

## Lokálne

```bash
pip install -r requirements.txt
export APRS_CALLSIGN=OM8AKX
export APRS_PASSCODE=12345
python3 aprs_sk_storm_bulletin.py
```

### Premenné

| Premenná | Predvolené | Popis |
|----------|------------|-------|
| `USE_METEOALARM` | 1 | Oficiálne výstrahy |
| `USE_BLITZORTUNG` | 1 | Blesky |
| `USE_OPENMETEO` | 1 | Predpoveď Open-Meteo |
| `BLITZ_MIN_STRIKES` | 5 | Prah úderov |
| `OPENMETEO_HOURS` | 3 | Hodiny predpovede dopredu |
| `MIN_RESEND_MINUTES` | 30 | Interval medzi rovnakými bulletinmi |

## Licencia

MIT · 73! OM8AKX
