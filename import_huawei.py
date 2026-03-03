#!/usr/bin/env python3
"""
Importiert Huawei-Daten aus CSV-Dateien und merged sie in garmin_data.json.

Die Huawei-Daten (vor Garmin) werden als zusaetzliche Eintraege hinzugefuegt.
Bei Ueberlappung werden nur leere Garmin-Felder mit Huawei-Daten aufgefuellt.
"""

import csv
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALTE_DATEN = os.path.join(SCRIPT_DIR, "Alte Daten")
GARMIN_FILE = os.path.join(SCRIPT_DIR, "data", "garmin_data.json")

# Huawei Dateien
HEALTH_CSV = os.path.join(ALTE_DATEN, "huawei_daily_health.csv")
ACTIVITY_CSV = os.path.join(ALTE_DATEN, "huawei_daily_activity.csv")
SPORT_CSV = os.path.join(ALTE_DATEN, "huawei_sport_by_type.csv")


def safe_float(val):
    """Konvertiert String zu Float, gibt None zurueck bei leerem Wert."""
    if val is None or val == "" or val.strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val):
    """Konvertiert String zu Int, gibt None zurueck bei leerem Wert."""
    f = safe_float(val)
    if f is None:
        return None
    return int(f)


def read_csv(path):
    """Liest CSV-Datei und gibt Liste von Dicts zurueck."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def empty_daily(date_str):
    """Erstellt einen leeren Daily-Eintrag im Garmin-Format."""
    return {
        "date": date_str,
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


def main():
    # --- Garmin-Daten laden ---
    print("Lade garmin_data.json ...")
    with open(GARMIN_FILE, "r", encoding="utf-8") as f:
        garmin = json.load(f)

    daily_by_date = {}
    for entry in garmin["daily"]:
        daily_by_date[entry["date"]] = entry

    garmin_dates = set(daily_by_date.keys())
    garmin_first = min(garmin_dates)
    print(f"  Garmin: {len(garmin['daily'])} Tage, {garmin_first} bis {max(garmin_dates)}")
    print(f"  Garmin: {len(garmin.get('activities', []))} Aktivitaeten")

    # --- Huawei Health-Daten lesen ---
    print("\nLese Huawei Health-Daten ...")
    health_rows = read_csv(HEALTH_CSV)
    health_by_date = {}
    for row in health_rows:
        d = row["date"]
        # Nur Zeilen mit tatsaechlichen Daten (mindestens ein HR-Wert)
        rhr = safe_int(row.get("resting_hr"))
        hr_max = safe_int(row.get("max_hr"))
        hr_min = safe_int(row.get("min_hr"))
        stress_avg = safe_int(row.get("stress_avg"))
        stress_max = safe_int(row.get("stress_max"))
        spo2_avg = safe_float(row.get("spo2_avg"))

        if any(v is not None for v in [rhr, hr_max, hr_min, stress_avg, spo2_avg]):
            health_by_date[d] = {
                "resting_hr": rhr,
                "hr_min": hr_min,
                "hr_max": hr_max,
                "stress_avg": stress_avg,
                "stress_max": stress_max,
                "spo2_avg": spo2_avg,
            }
    print(f"  {len(health_by_date)} Tage mit Health-Daten")

    # --- Huawei Activity-Daten lesen ---
    print("\nLese Huawei Activity-Daten ...")
    activity_rows = read_csv(ACTIVITY_CSV)
    activity_by_date = {}
    for row in activity_rows:
        d = row["date"]
        steps = safe_int(row.get("steps"))
        cals = safe_float(row.get("calories_kcal"))

        if steps is not None and steps > 0:
            activity_by_date[d] = {
                "steps": steps,
                "calories_total": round(cals) if cals else None,
            }
    print(f"  {len(activity_by_date)} Tage mit Activity-Daten")

    # --- Huawei Sport-Daten lesen (fuer Aktivitaeten) ---
    print("\nLese Huawei Sport-Daten ...")
    sport_rows = read_csv(SPORT_CSV)

    # Sport-Typ Mapping: Huawei → Garmin-kompatibel
    type_map = {
        "hiking": ("hiking", "Wandern"),
        "cycling": ("road_cycling", "Radfahren"),
        "running": ("running", "Laufen"),
    }

    huawei_activities = []
    for row in sport_rows:
        sport_type = row.get("sport_type", "").lower()
        if sport_type not in type_map:
            continue  # Walking ueberspringen

        duration = safe_float(row.get("duration_min"))
        if duration is None or duration < 10:
            continue  # Zu kurze Auto-Erkennung ueberspringen

        distance_m = safe_float(row.get("distance_m"))
        distance_km = round(distance_m / 1000, 2) if distance_m else 0
        calories = safe_float(row.get("calories_kcal"))
        garmin_type, name = type_map[sport_type]

        huawei_activities.append({
            "date": row["date"],
            "type": garmin_type,
            "name": f"{name} (Huawei)",
            "duration_minutes": round(duration, 1),
            "distance_km": distance_km,
            "avg_hr": None,
            "calories": round(calories) if calories else None,
        })

    print(f"  {len(huawei_activities)} Aktivitaeten (Wandern/Radfahren/Laufen, >10 Min)")

    # --- Merge: Daily-Daten ---
    print("\n--- Merge Daily-Daten ---")
    all_huawei_dates = set(health_by_date.keys()) | set(activity_by_date.keys())
    new_dates = 0
    filled_dates = 0

    for d in sorted(all_huawei_dates):
        health = health_by_date.get(d, {})
        activity = activity_by_date.get(d, {})

        if d not in daily_by_date:
            # Neuer Eintrag (vor Garmin-Zeitraum)
            entry = empty_daily(d)
            entry["resting_hr"] = health.get("resting_hr")
            entry["hr_min"] = health.get("hr_min")
            entry["hr_max"] = health.get("hr_max")
            entry["stress_avg"] = health.get("stress_avg")
            entry["stress_max"] = health.get("stress_max")
            entry["spo2_avg"] = health.get("spo2_avg")
            entry["steps"] = activity.get("steps")
            entry["calories_total"] = activity.get("calories_total")
            daily_by_date[d] = entry
            new_dates += 1
        else:
            # Bestehendes Garmin-Datum: nur Nulls auffuellen
            existing = daily_by_date[d]
            updated = False
            field_map = {
                "resting_hr": health.get("resting_hr"),
                "hr_min": health.get("hr_min"),
                "hr_max": health.get("hr_max"),
                "stress_avg": health.get("stress_avg"),
                "stress_max": health.get("stress_max"),
                "spo2_avg": health.get("spo2_avg"),
                "steps": activity.get("steps"),
                "calories_total": activity.get("calories_total"),
            }
            for field, val in field_map.items():
                if existing.get(field) is None and val is not None:
                    existing[field] = val
                    updated = True
            if updated:
                filled_dates += 1

    print(f"  {new_dates} neue Tage hinzugefuegt (vor Garmin)")
    print(f"  {filled_dates} bestehende Tage mit Huawei-Daten aufgefuellt")

    # --- Merge: Aktivitaeten ---
    print("\n--- Merge Aktivitaeten ---")
    existing_activities = garmin.get("activities", [])

    # Nur Huawei-Aktivitaeten fuer Daten vor dem Garmin-Zeitraum hinzufuegen
    garmin_activity_dates = set(a["date"] for a in existing_activities)
    added_acts = 0
    for act in huawei_activities:
        if act["date"] < garmin_first:
            existing_activities.append(act)
            added_acts += 1

    print(f"  {added_acts} Huawei-Aktivitaeten hinzugefuegt")

    # --- Sortieren und speichern ---
    all_daily = sorted(daily_by_date.values(), key=lambda x: x["date"])
    existing_activities.sort(key=lambda x: x["date"], reverse=True)

    garmin["daily"] = all_daily
    garmin["activities"] = existing_activities
    garmin["last_updated"] = datetime.now().isoformat(timespec="seconds")

    print(f"\n--- Ergebnis ---")
    print(f"  Daily:       {len(all_daily)} Tage ({all_daily[0]['date']} bis {all_daily[-1]['date']})")
    print(f"  Aktivitaeten: {len(existing_activities)}")

    # Backup erstellen
    backup = GARMIN_FILE + ".backup"
    if not os.path.exists(backup):
        import shutil
        shutil.copy2(GARMIN_FILE, backup)
        print(f"\n  Backup: {backup}")

    # Speichern
    with open(GARMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(garmin, f, ensure_ascii=False, indent=2)
    print(f"  Gespeichert: {GARMIN_FILE}")


if __name__ == "__main__":
    main()
