# APRS SK Storm Bulletin

Python skript, ktorý pri výskyte **búrok na území Slovenska** automaticky pošle bulletin do **APRS-IS**.

**Zdroje dát:**
1. Oficiálne výstrahy SHMÚ cez MeteoAlarm CAP feed
2. Aktuálne blesky z **Blitzortung** (verejný WebSocket)

## Čo robí

1. Stiahne aktuálne výstrahy zo Slovenska (MeteoAlarm / SHMÚ)
2. Počúva Blitzortung WebSocket ~45 s a počíta údery bleskov nad územím SR
3. Ak nájde aktívnu výstrahu **alebo** dostatok bleskov (≥5), vytvorí krátky bulletin
4. Pošle ho do APRS-IS ako `BLN1` bulletin

Príklady bulletinov:
```
SHMU žltá búrky: Žilina, Poprad
SHMU oranžová búrky: Prešov | Blitzortung 12 úderov/SK
Blitzortung 8 úderov/SK
```

## Požiadavky

- Python 3.8+
- Platný amatérsky callsign a APRS-IS passcode
- Internetové pripojenie

```bash
pip install -r requirements.txt
```

## Inštalácia a konfigurácia

```bash
git clone https://github.com/OM8AKX/aprs-sk-storm-bulletin.git
cd aprs-sk-storm-bulletin
pip install -r requirements.txt

export APRS_CALLSIGN="OM8AKX"
export APRS_PASSCODE="12345"           # alebo nechaj prázdne – vygeneruje sa
export APRS_SERVER="euro.aprs2.net"
```

### Blitzortung nastavenia (voliteľné)

| Premenná                 | Predvolené | Popis                                      |
|--------------------------|------------|--------------------------------------------|
| `USE_BLITZORTUNG`        | 1          | Zapnúť/vypnúť Blitzortung (0/1)            |
| `BLITZ_LISTEN_SECONDS`   | 45         | Koľko sekúnd počúvať WebSocket             |
| `BLITZ_MIN_STRIKES`      | 5          | Min. počet úderov nad SK na trigger        |
| `BLITZ_MAX_AGE_SEC`      | 600        | Max. vek úderu v sekundách (10 min)        |
| `USE_METEOALARM`         | 1          | Zapnúť/vypnúť MeteoAlarm                   |

## Spustenie

```bash
python3 aprs_sk_storm_bulletin.py
```

Odporúčané cez **cron** každých 10–15 minút (Blitzortung počúvanie trvá ~45 s):

```cron
*/15 * * * * cd /cesta/k/skriptu && /usr/bin/python3 aprs_sk_storm_bulletin.py >> /var/log/aprs-storm.log 2>&1
```

## Poznámky k Blitzortung

- Používa verejné WebSocket servery (`ws1`, `ws7`, `ws8` …) – rovnaké ako oficiálna mapa.
- Filtruje údery podľa bounding boxu Slovenska.
- Pri každom behu sa pripojí na ~45 sekúnd a počíta aktuálne údery.
- Ak nie je dostupný žiadny server, skript pokračuje len s MeteoAlarm dátami.

## Licencia

MIT

---
73!  
OM8AKX
