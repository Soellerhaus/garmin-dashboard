@echo off
REM Garmin Dashboard - Taeglicher Datenabruf
REM Wird per Windows Task Scheduler ausgefuehrt

cd /d C:\garmin-dashboard
"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" -u garmin_fetch.py >> data\fetch_log.txt 2>&1

REM Automatisch auf GitHub pushen
git add data\garmin_data.json >> data\fetch_log.txt 2>&1
git commit -m "Auto-Update: Garmin Daten %date%" >> data\fetch_log.txt 2>&1
git push origin master >> data\fetch_log.txt 2>&1

echo [%date% %time%] Fetch abgeschlossen >> data\fetch_log.txt
