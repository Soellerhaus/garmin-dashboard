#!/usr/bin/env python3
"""
Gewichtsdaten Import – aus CSV oder Huawei Health Export.

Variante 1 (einfach): CSV-Datei mit Gewichtsdaten
  python huawei_import.py data/gewicht.csv

Variante 2 (Huawei Export): Entpackter Export-Ordner
  python huawei_import.py "C:\\Users\\Max\\Downloads\\HuaweiHealthExport"

Ohne Argumente: Liest automatisch data/gewicht.csv

Speichert alles in data/weight_data.json.
"""

import sys
import os
import json
import glob
from datetime import datetime


# ── CSV-Import ────────────────────────────────────────────────────

def parse_csv(datei_pfad):
    """Liest Gewichtsdaten aus einer einfachen CSV-Datei.

    Erwartetes Format (Semikolon oder Komma als Trennzeichen):
      datum;gewicht;koerperfett
      2024-01-05;85.2;22.1
      2024-02-03;84.1;

    Koerperfett ist optional. Erste Zeile wird als Header ignoriert.
    """
    gewichte = []

    with open(datei_pfad, "r", encoding="utf-8") as f:
        zeilen = f.readlines()

    if len(zeilen) < 2:
        return gewichte

    # Trennzeichen erkennen
    trennzeichen = ";" if ";" in zeilen[0] else ","

    for zeile in zeilen[1:]:
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue

        teile = zeile.split(trennzeichen)
        if len(teile) < 2:
            continue

        try:
            datum = teile[0].strip()
            # Verschiedene Datumsformate unterstuetzen
            if "." in datum and len(datum.split(".")) == 3:
                # TT.MM.JJJJ
                p = datum.split(".")
                datum = f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"

            gewicht = float(teile[1].strip().replace(",", "."))
            eintrag = {"date": datum, "weight_kg": round(gewicht, 1)}

            if len(teile) >= 3 and teile[2].strip():
                fett = float(teile[2].strip().replace(",", "."))
                eintrag["body_fat_pct"] = round(fett, 1)

            gewichte.append(eintrag)
        except (ValueError, IndexError):
            continue

    return gewichte


# ── Huawei Health JSON-Import ─────────────────────────────────────

def parse_weight_records(data):
    """Extrahiert Gewichtsdaten aus Huawei Health JSON-Struktur.

    Huawei Health speichert Gewichtsdaten mit type=10006.
    Die Messwerte stecken in samplePoints[].value als
    doppelt kodierter JSON-String.
    """
    gewichte = []
    records = data if isinstance(data, list) else [data]

    for record in records:
        if record.get("type") != 10006:
            continue
        for point in record.get("samplePoints", []):
            if point.get("key") != "WEIGHT_BODYFAT_BROAD":
                continue
            try:
                ts_ms = point.get("startTime", 0)
                datum = datetime.fromtimestamp(ts_ms / 1000)
                value_str = point.get("value", "{}")
                values = json.loads(value_str) if isinstance(value_str, str) else value_str
                weight = values.get("bodyWeight")
                fat = values.get("bodyFatRate")
                if weight is not None:
                    eintrag = {
                        "date": datum.strftime("%Y-%m-%d"),
                        "weight_kg": round(float(weight), 1),
                    }
                    if fat is not None:
                        eintrag["body_fat_pct"] = round(float(fat), 1)
                    gewichte.append(eintrag)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

    return gewichte


def find_health_json_files(pfad):
    """Sucht nach JSON-Dateien im Huawei Health Export-Ordner."""
    json_dateien = []
    if os.path.isfile(pfad) and pfad.lower().endswith(".json"):
        return [pfad]
    if os.path.isdir(pfad):
        health_dir = os.path.join(pfad, "Health detail data & description")
        if os.path.isdir(health_dir):
            pfad = health_dir
        for datei in glob.glob(os.path.join(pfad, "**", "*.json"), recursive=True):
            json_dateien.append(datei)
    return json_dateien


# ── Speichern ─────────────────────────────────────────────────────

def speichern(gewicht_liste):
    """Speichert Gewichtsdaten als JSON, fuehrt mit bestehenden zusammen."""
    skript_pfad = os.path.dirname(os.path.abspath(__file__))
    data_pfad = os.path.join(skript_pfad, "data")
    os.makedirs(data_pfad, exist_ok=True)
    datei_pfad = os.path.join(data_pfad, "weight_data.json")

    # Bestehende Daten laden
    bestehende = []
    if os.path.exists(datei_pfad):
        try:
            with open(datei_pfad, "r", encoding="utf-8") as f:
                alt = json.load(f)
                bestehende = alt.get("weights", [])
                print(f"  {len(bestehende)} bestehende Eintraege gefunden")
        except (json.JSONDecodeError, KeyError):
            pass

    # Zusammenfuehren: neue Daten ueberschreiben alte am gleichen Datum
    zusammen = {e["date"]: e for e in bestehende}
    for eintrag in gewicht_liste:
        zusammen[eintrag["date"]] = eintrag
    endgueltig = sorted(zusammen.values(), key=lambda x: x["date"])

    ergebnis = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "source": "Gewichtsdaten Import",
        "weights": endgueltig,
    }

    with open(datei_pfad, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)

    print(f"  Gespeichert: {datei_pfad}")
    print()
    print("=" * 50)
    min_w = min(e["weight_kg"] for e in endgueltig)
    max_w = max(e["weight_kg"] for e in endgueltig)
    print(f"  {len(endgueltig)} Tage mit Gewichtsdaten")
    print(f"  Zeitraum: {endgueltig[0]['date']} bis {endgueltig[-1]['date']}")
    print(f"  Gewicht: {min_w} – {max_w} kg")
    has_fat = any("body_fat_pct" in e for e in endgueltig)
    if has_fat:
        fats = [e["body_fat_pct"] for e in endgueltig if "body_fat_pct" in e]
        print(f"  Koerperfett: {min(fats)} – {max(fats)} %")
    print("=" * 50)


# ── Hauptprogramm ─────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Gewichtsdaten Import")
    print("=" * 50)
    print()

    # Standard: data/gewicht.csv im Skript-Ordner
    skript_pfad = os.path.dirname(os.path.abspath(__file__))
    standard_csv = os.path.join(skript_pfad, "data", "gewicht.csv")

    quell_pfad = sys.argv[1] if len(sys.argv) >= 2 else standard_csv

    if not os.path.exists(quell_pfad):
        if len(sys.argv) < 2:
            print(f"Keine CSV-Datei gefunden: {standard_csv}")
            print()
            print("Erstelle die Datei data/gewicht.csv mit folgendem Format:")
            print()
            print("  datum;gewicht;koerperfett")
            print("  2024-01-05;85.2;22.1")
            print("  2024-02-03;84.1;")
            print("  2024-03-15;83.0;20.5")
            print()
            print("Koerperfett ist optional. Dann erneut ausfuehren.")
        else:
            print(f"FEHLER: Pfad nicht gefunden: {quell_pfad}")
        sys.exit(1)

    alle_gewichte = []

    # ── CSV-Datei? ────────────────────────────────────────
    if quell_pfad.lower().endswith(".csv"):
        print(f"Lese CSV: {quell_pfad}")
        alle_gewichte = parse_csv(quell_pfad)
        if alle_gewichte:
            print(f"  {len(alle_gewichte)} Eintraege gelesen")
        else:
            print("  Keine Gewichtsdaten in der CSV gefunden.")
            sys.exit(1)

    # ── Huawei Health Export-Ordner? ──────────────────────
    else:
        print(f"Suche Huawei Health Daten in: {quell_pfad}")
        json_dateien = find_health_json_files(quell_pfad)

        if not json_dateien:
            print("Keine JSON-Dateien gefunden.")
            sys.exit(1)

        print(f"  {len(json_dateien)} JSON-Datei(en) gefunden")
        print()
        print("Lese Gewichtsdaten...")

        for datei in json_dateien:
            try:
                with open(datei, "r", encoding="utf-8") as f:
                    data = json.load(f)
                gewichte = parse_weight_records(data)
                if gewichte:
                    print(f"  {os.path.basename(datei)}: {len(gewichte)} Messungen")
                    alle_gewichte.extend(gewichte)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        if not alle_gewichte:
            print("Keine Gewichtsdaten gefunden.")
            sys.exit(1)

    # Tagesdurchschnitte berechnen
    tages_daten = {}
    for eintrag in alle_gewichte:
        datum = eintrag["date"]
        if datum not in tages_daten:
            tages_daten[datum] = {"weights": [], "fats": []}
        tages_daten[datum]["weights"].append(eintrag["weight_kg"])
        if "body_fat_pct" in eintrag:
            tages_daten[datum]["fats"].append(eintrag["body_fat_pct"])

    gewicht_liste = []
    for datum in sorted(tages_daten.keys()):
        werte = tages_daten[datum]
        avg_weight = round(sum(werte["weights"]) / len(werte["weights"]), 1)
        eintrag = {"date": datum, "weight_kg": avg_weight}
        if werte["fats"]:
            avg_fat = round(sum(werte["fats"]) / len(werte["fats"]), 1)
            eintrag["body_fat_pct"] = avg_fat
        gewicht_liste.append(eintrag)

    print()
    print("Speichere Daten...")
    speichern(gewicht_liste)


if __name__ == "__main__":
    main()
