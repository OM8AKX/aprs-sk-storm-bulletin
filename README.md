# APRS SK Storm Bulletin

Python skript, ktorý pri výskyte **búrok a krúp na území Slovenska** automaticky pošle bulletin do **APRS-IS**.

**Zdroje dát:**
1. **MeteoAlarm / SHMÚ** – oficiálne výstrahy (búrky + zmienky o krúpach)
2. **Blitzortung** – reálne blesky (WebSocket)
3. **Open-Meteo** – predpoveď búrok/krúp (kódy 95–99, bez API kľúča)

## Detekcia krúp

| Zdroj | Ako deteguje krúpy |
|-------|--------------------|
| MeteoAlarm | Kľúčové slová v texte (krúp, hail, hagel…) |
| Open-Meteo | Weather code **96** (slight hail) a **99** (heavy hail) |

Príklady bulletinov:
```
SHMU žltá búrky+krúpy: Žilina, Poprad
OpenMeteo krúpy: Košice,Prešov
SHMU oranžová búrky: BA | Blitz 12 úderov | OpenMeteo krúpy: NR
```

## GitHub Actions

1. Secrets: `APRS_CALLSIGN`, `APRS_PASSCODE`
2. Actions → SK Storm Bulletin → Run workflow

Beží každých 15 minút.

## Lokálne

```bash
pip install -r requirements.txt
export APRS_CALLSIGN=OM8AKX
export APRS_PASSCODE=12345
python3 aprs_sk_storm_bulletin.py
```

| Premenná | Predvolené | Popis |
|----------|------------|-------|
| `USE_METEOALARM` | 1 | Oficiálne výstrahy |
| `USE_BLITZORTUNG` | 1 | Blesky |
| `USE_OPENMETEO` | 1 | Predpoveď + krúpy |
| `BLITZ_MIN_STRIKES` | 5 | Prah úderov |
| `OPENMETEO_HOURS` | 3 | Hodiny predpovede |

## Licencia

MIT · 73! OM8AKX
