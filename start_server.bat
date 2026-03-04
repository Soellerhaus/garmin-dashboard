@echo off
REM Garmin Dashboard Server - Auto-Restart bei Absturz
REM Wird per Windows Task Scheduler bei Systemstart ausgefuehrt

cd /d C:\garmin-dashboard

:loop
echo [%date% %time%] Server wird gestartet... >> data\server_log.txt
"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" -u server.py 80 >> data\server_log.txt 2>&1
echo [%date% %time%] Server beendet - Neustart in 5 Sekunden... >> data\server_log.txt
timeout /t 5 /nobreak > nul
goto loop
