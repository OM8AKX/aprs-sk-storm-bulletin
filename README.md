# APRS SK Storm Bulletin

Python skript, ktorý pri výskyte **búrok na území Slovenska** automaticky pošle bulletin do **APRS-IS**.

**Zdroje dát:**
1. Oficiálne výstrahy SHMÚ cez MeteoAlarm CAP feed
2. Aktuálne blesky z **Blitzortung** (verejný WebSocket)

## Čo robí

1. Stiahne aktuálne výstrahy zo Slovenska (MeteoAlarm / SHMÚ)
2. Počúva Blitzortung WebSocket ~40–45 s a počíta údery bleskov nad územím SR
3. Ak nájde aktívnu výstrahu **alebo** dostatok bleskov (≥5), vytvorí krátky bulletin
4. Pošle ho do APRS-IS ako `BLN1` bulletin

Príklady bulletinov:
```
SHMU žltá búrky: Žilina, Poprad
SHMU oranžová búrky: Prešov | Blitzortung 12 úderov/SK
Blitzortung 8 úderov/SK
```

## Spustenie na GitHub Actions (odporúčané)

Projekt obsahuje workflow, ktorý beží **každých 15 minút** priamo na GitHube.

### 1. Nastav Secrets

Choď do repozitára → **Settings → Secrets and variables → Actions → New repository secret**

Pridaj tieto dva secrets:

| Názov             | Hodnota                          |
|-------------------|----------------------------------|
| `APRS_CALLSIGN`   | tvoj callsign (napr. `OM8AKX`)   |
| `APRS_PASSCODE`   | APRS-IS passcode                 |

Passcode vygeneruješ tu: https://apps.magicbug.co.uk/passcode/

### 2. Zapni Actions

Ak Actions ešte nie sú povolené:
- **Settings → Actions → General → Allow all actions**

### 3. Manuálne spustenie (test)

- Záložka **Actions** → **SK Storm Bulletin** → **Run workflow**

Potom sa workflow spúšťa automaticky každých 15 minút.

---

## Lokálne spustenie

```bash
git clone https://github.com/OM8AKX/aprs-sk-storm-bulletin.git
cd aprs-sk-storm-bulletin
pip install -r requirements.txt

export APRS_CALLSIGN="OM8AKX"
export APRS_PASSCODE="12345"
python3 aprs_sk_storm_bulletin.py
```

### Blitzortung / MeteoAlarm nastavenia

| Premenná                 | Predvolené | Popis                                      |
|--------------------------|------------|--------------------------------------------|
| `USE_BLITZORTUNG`        | 1          | Zapnúť/vypnúť Blitzortung (0/1)            |
| `BLITZ_LISTEN_SECONDS`   | 45         | Koľko sekúnd počúvať WebSocket             |
| `BLITZ_MIN_STRIKES`      | 5          | Min. počet úderov nad SK na trigger        |
| `BLITZ_MAX_AGE_SEC`      | 600        | Max. vek úderu v sekundách (10 min)        |
| `USE_METEOALARM`         | 1          | Zapnúť/vypnúť MeteoAlarm                   |

## Poznámky

- GitHub Actions free tier stačí na beh každých 15 minút.
- Blitzortung používa verejné WebSocket servery (rovnaké ako oficiálna mapa).
- Pri každom behu sa pripojí na ~40 s a počíta aktuálne údery nad SK.
- Ten istý bulletin sa neposiela častejšie ako raz za ~25–30 minút.

## Licencia

MIT

---
73!  
OM8AKX
