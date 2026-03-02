# Garmin Dashboard

Einfaches, lokales Dashboard für deine Garmin Connect Daten.
Kein Backend, keine Datenbank – nur Python-Skripte und eine HTML-Datei.

## Voraussetzungen

- Python 3.8 oder neuer
- pip (Python-Paketmanager)
- Ein Garmin Connect Account

## Installation

```bash
pip install garth
```

## Benutzung

### 1. Erster Login

Einmalig ausführen, um den Garmin-Token zu speichern:

```bash
python garmin_login.py
```

Du wirst nach E-Mail und Passwort gefragt. Der Token wird unter `~/.garth/` gespeichert.

### 2. Daten abrufen

Holt die Daten der letzten 30 Tage von Garmin Connect:

```bash
python garmin_fetch.py
```

Die Daten werden in `data/garmin_data.json` gespeichert.

### 3. Dashboard ansehen

**Lokal (einfachste Methode):**

```bash
# Python-Webserver starten (im Projektordner)
python -m http.server 8080
```

Dann im Browser `http://localhost:8080` öffnen.

**Oder:** `index.html` direkt im Browser öffnen (bei manchen Browsern funktioniert `fetch()` nicht mit `file://`-URLs).

**Auf einem Webserver:** Einfach den gesamten Ordner auf deinen Webserver kopieren.

## Huawei Health – Gewichtsdaten importieren

Das Dashboard kann zusätzlich Gewichtsdaten aus der Huawei Health App anzeigen.

### Daten exportieren (einmalig in der App)

1. Huawei Health App öffnen
2. **Ich** > Kontoname > **Datenschutzzentrum**
3. **Daten anfordern** > **Health** auswählen
4. Passwort festlegen und absenden
5. ZIP per E-Mail erhalten und entpacken

### Gewichtsdaten importieren

```bash
python huawei_import.py "C:\Users\DeinName\Downloads\HuaweiHealthExport"
```

Das Skript sucht automatisch im Ordner `Health detail data & description` nach Gewichtsdaten und speichert sie in `data/weight_data.json`. Bei erneutem Import werden bestehende Daten zusammengeführt.

Das Dashboard zeigt dann automatisch die Gewichts- und Körperfett-Charts an.

## Automatisierung

### Windows – Task Scheduler

1. Aufgabenplanung öffnen (Win+R → `taskschd.msc`)
2. Neue Aufgabe erstellen
3. Trigger: Täglich um z.B. 08:00
4. Aktion: Programm starten
   - Programm: `python`
   - Argumente: `C:\garmin-dashboard\garmin_fetch.py`
   - Starten in: `C:\garmin-dashboard`

### Linux – Cron

Crontab bearbeiten:

```bash
crontab -e
```

Zeile hinzufügen (jeden Tag um 8:00 Uhr):

```
0 8 * * * cd /pfad/zu/garmin-dashboard && python3 garmin_fetch.py >> /var/log/garmin_fetch.log 2>&1
```

## Passwortschutz (Apache-Webserver)

Falls das Dashboard auf einem Webserver läuft:

1. `.htpasswd`-Datei erstellen (außerhalb des Web-Verzeichnisses):

```bash
htpasswd -c /home/DEINUSER/.htpasswd benutzername
```

2. In `.htaccess` den Pfad bei `AuthUserFile` anpassen.

## Projektstruktur

```
garmin-dashboard/
├── garmin_login.py     # Einmaliger Login, Token speichern
├── garmin_fetch.py     # Täglicher Datenabruf
├── huawei_import.py    # Huawei Health Gewichtsdaten importieren
├── garmin_debug.py     # Debug: API-Endpoints testen
├── data/               # JSON-Dateien (automatisch erstellt)
│   ├── garmin_data.json
│   └── weight_data.json
├── index.html          # Dashboard (Single File)
├── .htaccess           # Passwortschutz (Apache)
└── README.md           # Diese Datei
```

## Token abgelaufen?

Falls `garmin_fetch.py` meldet, dass der Token abgelaufen ist:

```bash
python garmin_login.py
```

Danach erneut `garmin_fetch.py` ausführen.

## Hinweise

- Keine Zugangsdaten werden im Code gespeichert
- Alle Daten bleiben lokal auf deinem Rechner
- Das Dashboard funktioniert offline (nach dem Datenabruf)
- Bei fehlenden Werten wird `null` gesetzt – das Dashboard zeigt Lücken an
