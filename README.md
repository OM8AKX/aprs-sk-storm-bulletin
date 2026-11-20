# APRS SK Storm Bulletin

Python skript, ktorý pri výskyte **búrok na území Slovenska** automaticky pošle bulletin do **APRS-IS**.

Zdroj dát: oficiálny MeteoAlarm CAP feed (SHMÚ).

## Čo robí

1. Stiahne aktuálne výstrahy zo Slovenska (MeteoAlarm / SHMÚ)
2. Filtruje výstrahy typu **Thunderstorm** (búrky)
3. Ak nájde aktívnu výstrahu, vytvorí krátky bulletin (max 67 znakov)
4. Pošle ho do APRS-IS ako `BLN1` bulletin

Príklad bulletinu:
```
SHMU žltá výstraha pred búrkami: Žilina, Poprad, Prešov
```

## Požiadavky

- Python 3.8+
- Platný amatérsky callsign a APRS-IS passcode
- Internetové pripojenie

```bash
pip install -r requirements.txt
```

## Inštalácia a konfigurácia

1. Klonuj repozitár:
```bash
git clone https://github.com/OM8AKX/aprs-sk-storm-bulletin.git
cd aprs-sk-storm-bulletin
```

2. Nastav premenné prostredia (odporúčané):

```bash
export APRS_CALLSIGN="OM8AKX"          # tvoj callsign
export APRS_PASSCODE="12345"           # passcode (vygeneruj nižšie)
export APRS_SERVER="euro.aprs2.net"    # európsky server
```

Alebo uprav konštanty priamo v skripte.

### Ako získať APRS-IS passcode

- Online: https://apps.magicbug.co.uk/passcode/
- Alebo skript si ho vygeneruje automaticky z callsignu (ak `APRS_PASSCODE` nie je nastavený)

## Spustenie

Jednorazovo:
```bash
python3 aprs_sk_storm_bulletin.py
```

Odporúčané cez **cron** každých 10–15 minút:

```cron
*/15 * * * * cd /cesta/k/skriptu && /usr/bin/python3 aprs_sk_storm_bulletin.py >> /var/log/aprs-storm.log 2>&1
```

Skript si pamätá posledný odoslaný bulletin a neposiela ten istý častejšie ako raz za 30 minút (nastaviteľné cez `MIN_RESEND_MINUTES`).

## Konfiguračné možnosti

| Premenná / konštanta     | Predvolená hodnota     | Popis                                      |
|--------------------------|------------------------|--------------------------------------------|
| `APRS_CALLSIGN`          | OM8AKX                 | Callsign                                   |
| `APRS_PASSCODE`          | (auto)                 | APRS-IS passcode                           |
| `APRS_SERVER`            | euro.aprs2.net         | APRS-IS server                             |
| `APRS_PORT`              | 14580                  | Port                                       |
| `BULLETIN_ID`            | 1                      | Číslo bulletinu (BLN1–BLN9)                |
| `BULLETIN_GROUP`         | ""                     | Group bulletin (napr. "WX")                |
| `MIN_RESEND_MINUTES`     | 30                     | Minimálny interval medzi rovnakými bulletinmi |

## Poznámky

- Skript posiela **všeobecný bulletin** (`BLN1`). Ak chceš group bulletin (napr. pre skupinu WX), nastav `BULLETIN_GROUP = "WX"`.
- Text bulletinu je v slovenčine a stručný kvôli limitu 67 znakov.
- Neposiela sa pri každom behu – len keď sa zmení situácia alebo uplynie `MIN_RESEND_MINUTES`.
- Pre produkciu odporúčam spúšťať pod cronom alebo systemd timerom.

## Licencia

MIT

---
73!  
OM8AKX
