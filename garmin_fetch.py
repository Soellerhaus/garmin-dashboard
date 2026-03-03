#!/usr/bin/env python3
"""
Garmin Fetch – Datenabruf von Garmin Connect.

Nutzt den gespeicherten Token aus ~/.garth/,
holt die Daten ab 01.01.2022 und speichert
alles in data/garmin_data.json.

Verwendet garth-Datenklassen fuer Schlaf, Body Battery etc.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta, date
from pathlib import Path

# Token-Verzeichnis (gleich wie in garmin_login.py)
TOKEN_DIR = str(Path.home() / ".garth")


def safe_api(garth, url, params=None):
    """API-Aufruf mit Fehlerbehandlung. Gibt None bei Fehler zurueck."""
    try:
        if params:
            return garth.connectapi(url, params=params)
        return garth.connectapi(url)
    except Exception:
        return None


def safe_get(func, *args, **kwargs):
    """Sicherer Aufruf einer garth-Datenklasse."""
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


def main():
    """Hauptfunktion: Daten von Garmin Connect abrufen."""

    # garth importieren
    try:
        import garth
    except ImportError:
        print("FEHLER: Die Bibliothek 'garth' ist nicht installiert.")
        print("Bitte installieren mit: pip install garth")
        sys.exit(1)

    print("=" * 50)
    print("  Garmin Connect - Datenabruf")
    print("=" * 50)
    print()

    # Gespeicherten Token laden
    try:
        garth.resume(TOKEN_DIR)
        garth.client.username
        print("Token geladen - Verbindung steht.")
    except Exception:
        print("FEHLER: Kein gueltiger Token gefunden.")
        print("Bitte zuerst garmin_login.py ausfuehren.")
        sys.exit(1)

    # Zeitraum festlegen: ab 01.01.2022 bis heute
    heute = date.today()
    start_datum = date(2022, 1, 1)
    anzahl_tage = (heute - start_datum).days + 1

    print(f"Zeitraum: {start_datum} bis {heute} ({anzahl_tage} Tage)")
    print()

    # Datenstruktur vorbereiten
    tage_erfolgreich = 0
    daily_data = []
    activities_data = []

    # ---- Taegliche Daten abrufen ----
    print("Hole taegliche Daten...")

    for i in range(anzahl_tage):
        datum = start_datum + timedelta(days=i)
        datum_str = datum.isoformat()

        tages_daten = {
            "date": datum_str,
            "resting_hr": None,
            "hr_min": None,
            "hr_max": None,
            "hr_avg": None,
            "hrv": None,
            "sleep_duration_hours": None,
            "sleep_score": None,
            "deep_sleep_pct": None,
            "light_sleep_pct": None,
            "rem_sleep_pct": None,
            "body_battery_min": None,
            "body_battery_max": None,
            "stress_avg": None,
            "stress_max": None,
            "steps": None,
            "spo2_avg": None,
            "calories_total": None,
            "calories_active": None,
        }

        # ---- Herzfrequenz (REST API) ----
        hr = safe_api(garth,
            f"/usersummary-service/stats/heartRate/daily/{datum_str}/{datum_str}")
        if hr and isinstance(hr, list) and len(hr) > 0:
            vals = hr[0].get("values", {})
            tages_daten["resting_hr"] = vals.get("restingHR")
            tages_daten["hr_min"] = vals.get("wellnessMinAvgHR")
            tages_daten["hr_max"] = vals.get("wellnessMaxAvgHR")

        # ---- HRV (REST API) ----
        hrv = safe_api(garth, f"/hrv-service/hrv/{datum_str}")
        if hrv and isinstance(hrv, dict):
            summary = hrv.get("hrvSummary")
            if summary:
                tages_daten["hrv"] = summary.get("lastNightAvg") or summary.get("weeklyAvg")

        # ---- Schritte (REST API) ----
        steps = safe_api(garth,
            f"/usersummary-service/stats/steps/daily/{datum_str}/{datum_str}")
        if steps and isinstance(steps, list) and len(steps) > 0:
            tages_daten["steps"] = steps[0].get("totalSteps")

        # ---- Schlaf (garth DailySleepData) ----
        sleep = safe_get(garth.DailySleepData.get, datum)
        if sleep and hasattr(sleep, 'daily_sleep_dto'):
            dto = sleep.daily_sleep_dto
            if dto:
                # Schlafdauer
                if dto.sleep_time_seconds:
                    tages_daten["sleep_duration_hours"] = round(dto.sleep_time_seconds / 3600, 1)

                # Schlaf-Score
                if dto.sleep_scores and dto.sleep_scores.overall:
                    tages_daten["sleep_score"] = dto.sleep_scores.overall.value

                # Schlafphasen (Prozent)
                if dto.sleep_scores:
                    if dto.sleep_scores.deep_percentage:
                        tages_daten["deep_sleep_pct"] = dto.sleep_scores.deep_percentage.value
                    if dto.sleep_scores.light_percentage:
                        tages_daten["light_sleep_pct"] = dto.sleep_scores.light_percentage.value
                    if dto.sleep_scores.rem_percentage:
                        tages_daten["rem_sleep_pct"] = dto.sleep_scores.rem_percentage.value

        # ---- Body Battery + Stress (garth DailyBodyBatteryStress) ----
        bb = safe_get(garth.DailyBodyBatteryStress.list, datum, 1)
        if bb and len(bb) > 0:
            b = bb[0]
            tages_daten["body_battery_min"] = b.min_body_battery
            tages_daten["body_battery_max"] = b.max_body_battery
            tages_daten["stress_avg"] = b.avg_stress_level
            tages_daten["stress_max"] = b.max_stress_level

        # ---- Stress Fallback (REST API, falls garth-Klasse nichts liefert) ----
        if tages_daten["stress_avg"] is None:
            stress_stats = safe_api(garth,
                f"/usersummary-service/stats/stress/daily/{datum_str}/{datum_str}")
            if stress_stats and isinstance(stress_stats, list) and len(stress_stats) > 0:
                vals = stress_stats[0].get("values", {})
                tages_daten["stress_avg"] = vals.get("overallStressLevel")

        # ---- Kalorien (REST API) ----
        cals = safe_api(garth,
            f"/usersummary-service/stats/calories/daily/{datum_str}/{datum_str}")
        if cals and isinstance(cals, list) and len(cals) > 0:
            vals = cals[0].get("values", {})
            tages_daten["calories_total"] = vals.get("totalKilocalories")
            tages_daten["calories_active"] = vals.get("activeKilocalories")

        daily_data.append(tages_daten)

        # Zaehlen ob mindestens ein Wert vorhanden ist
        werte = [v for k, v in tages_daten.items() if k != "date" and v is not None]
        if werte:
            tage_erfolgreich += 1

        # Fortschritt anzeigen (jede 10. Zeile oder letzte)
        if i % 10 == 0 or i == anzahl_tage - 1:
            print(f"  [{i+1}/{anzahl_tage}] {datum_str} - {len(werte)} Werte")

        # Kurze Pause alle 30 Requests um Rate-Limiting zu vermeiden
        if i > 0 and i % 30 == 0:
            time.sleep(1)

    # ---- Aktivitaeten abrufen ----
    print()
    print("Hole Aktivitaeten...")

    try:
        aktivitaeten = garth.connectapi(
            f"/activitylist-service/activities/search/activities",
            params={"startDate": start_datum.isoformat(), "limit": 5000}
        )

        if aktivitaeten and isinstance(aktivitaeten, list):
            for akt in aktivitaeten:
                try:
                    akt_datum = akt.get("startTimeLocal", "")[:10]
                    dauer_sek = akt.get("duration")
                    dauer_min = round(dauer_sek / 60, 1) if dauer_sek else None
                    distanz_m = akt.get("distance")
                    distanz_km = round(distanz_m / 1000, 2) if distanz_m else None

                    aufstieg = akt.get("elevationGain")
                    if aufstieg is not None:
                        aufstieg = round(aufstieg)

                    activities_data.append({
                        "date": akt_datum,
                        "type": akt.get("activityType", {}).get("typeKey", "unknown"),
                        "name": akt.get("activityName", "Unbekannt"),
                        "duration_minutes": dauer_min,
                        "distance_km": distanz_km,
                        "avg_hr": akt.get("averageHR"),
                        "calories": akt.get("calories"),
                        "elevation_gain": aufstieg,
                    })
                except Exception:
                    continue

            print(f"  {len(activities_data)} Aktivitaeten geladen")
        else:
            print("  Keine Aktivitaeten gefunden")

    except Exception as e:
        print(f"  Aktivitaeten konnten nicht geladen werden: {e}")

    # ---- JSON speichern ----
    print()
    print("Speichere Daten...")

    ergebnis = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "daily": daily_data,
        "activities": activities_data,
    }

    skript_pfad = os.path.dirname(os.path.abspath(__file__))
    data_pfad = os.path.join(skript_pfad, "data")
    os.makedirs(data_pfad, exist_ok=True)
    datei_pfad = os.path.join(data_pfad, "garmin_data.json")

    try:
        with open(datei_pfad, "w", encoding="utf-8") as f:
            json.dump(ergebnis, f, ensure_ascii=False, indent=2)
        print(f"Gespeichert: {datei_pfad}")
    except Exception as e:
        print(f"FEHLER beim Speichern: {e}")
        sys.exit(1)

    # ---- Zusammenfassung ----
    print()
    print("=" * 50)
    print(f"  {tage_erfolgreich} von {anzahl_tage} Tagen erfolgreich geladen")
    print(f"  {len(activities_data)} Aktivitaeten geladen")
    print(f"  Letzte Aktualisierung: {ergebnis['last_updated']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
