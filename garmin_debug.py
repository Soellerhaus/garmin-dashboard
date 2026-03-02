#!/usr/bin/env python3
"""
Debug-Skript: Testet verschiedene Garmin API-Endpoints
und zeigt die Rückgabewerte an.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

TOKEN_DIR = str(Path.home() / ".garth")

try:
    import garth
except ImportError:
    print("garth nicht installiert")
    sys.exit(1)

try:
    garth.resume(TOKEN_DIR)
    print("Token geladen.\n")
except Exception:
    print("Token nicht gefunden. garmin_login.py ausfuehren.")
    sys.exit(1)

# Gestrige Daten (heute ist evtl. noch unvollständig)
datum = (datetime.now().date() - timedelta(days=1)).isoformat()
print(f"Test-Datum: {datum}\n")

# Liste der Endpoints zum Testen
endpoints = [
    ("Daily Summary", f"/usersummary-service/usersummary/daily/{datum}"),
    ("Heart Rate Stats", f"/usersummary-service/stats/heartRate/daily/{datum}/{datum}"),
    ("Daily Heart Rate", f"/wellness-service/wellness/dailyHeartRate/{datum}"),
    ("HRV", f"/hrv-service/hrv/{datum}"),
    ("Sleep", f"/wellness-service/wellness/dailySleepData/{datum}"),
    ("Sleep v2", f"/sleep-service/sleep/dailySleepData/{datum}"),
    ("Body Battery", f"/wellness-service/wellness/bodyBattery/days/{datum}/{datum}"),
    ("Body Battery v2", f"/wellness-service/wellness/bodyBattery?date={datum}"),
    ("Stress Daily", f"/usersummary-service/stats/stress/daily/{datum}/{datum}"),
    ("Stress Wellness", f"/wellness-service/wellness/dailyStress/{datum}"),
    ("SpO2 Summary", f"/wellness-service/wellness/pulse-ox/dailySummary/{datum}/{datum}"),
    ("SpO2 Daily", f"/wellness-service/wellness/pulse-ox/daily/{datum}"),
    ("Steps", f"/usersummary-service/stats/steps/daily/{datum}/{datum}"),
    ("Activities", f"/activitylist-service/activities/search/activities?startDate={datum}&limit=5"),
]

for name, url in endpoints:
    print(f"=== {name} ===")
    print(f"  URL: {url}")
    try:
        result = garth.connectapi(url)
        # Auf 500 Zeichen begrenzen für Lesbarkeit
        text = json.dumps(result, indent=2, ensure_ascii=False)
        if len(text) > 500:
            text = text[:500] + "\n  ... (gekuerzt)"
        print(f"  Response: {text}")
    except Exception as e:
        print(f"  FEHLER: {e}")
    print()
