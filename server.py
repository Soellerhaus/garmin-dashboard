#!/usr/bin/env python3
"""
Garmin Dashboard Server – Statische Dateien + Gewichts-API.

Startet einen einfachen Webserver der:
  - Statische Dateien aus dem Projektordner ausliefert
  - POST /api/weight  → Gewicht speichern
  - GET  /api/weight  → Alle Gewichtsdaten lesen

Starten:
  python server.py
  python server.py 8080
"""

import sys
import os
import json
import base64
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Passwort aus config.json laden
def load_password():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("password", "")
    return os.environ.get("DASHBOARD_PASSWORD", "")

PASSWORD = load_password()
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
WEIGHT_FILE = os.path.join(DATA_DIR, "weight_data.json")


def load_weight_data():
    """Laedt bestehende Gewichtsdaten."""
    if os.path.exists(WEIGHT_FILE):
        with open(WEIGHT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "source": "Dashboard", "weights": []}


def save_weight_data(data):
    """Speichert Gewichtsdaten."""
    os.makedirs(DATA_DIR, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat(timespec="seconds")
    with open(WEIGHT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP-Handler mit Gewichts-API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def check_auth(self):
        """Prueft HTTP Basic Auth. Gibt True zurueck wenn ok."""
        auth = self.headers.get("Authorization")
        if auth and auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                # Format: benutzer:passwort - nur Passwort pruefen
                if ":" in decoded:
                    pw = decoded.split(":", 1)[1]
                    if pw == PASSWORD:
                        return True
            except Exception:
                pass
        # Nicht autorisiert = Login-Dialog anzeigen
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Garmin Dashboard"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Zugang verweigert</h1><p>Bitte Passwort eingeben.</p>")
        return False

    def do_GET(self):
        if not self.check_auth():
            return
        if self.path == "/api/weight":
            self.send_json(load_weight_data())
        else:
            super().do_GET()

    def do_POST(self):
        if not self.check_auth():
            return
        if self.path == "/api/weight":
            self.handle_weight_post()
        else:
            self.send_error(404)

    def do_DELETE(self):
        if not self.check_auth():
            return
        if self.path.startswith("/api/weight/"):
            self.handle_weight_delete()
        else:
            self.send_error(404)

    def handle_weight_post(self):
        """Neues Gewicht speichern."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            gewicht = body.get("weight_kg")
            datum = body.get("date", datetime.now().strftime("%Y-%m-%d"))

            if gewicht is None:
                self.send_json({"error": "weight_kg fehlt"}, 400)
                return

            gewicht = round(float(gewicht), 1)
            if gewicht < 20 or gewicht > 300:
                self.send_json({"error": "Ungueltiges Gewicht"}, 400)
                return

            eintrag = {"date": datum, "weight_kg": gewicht}

            # Optional: Koerperfett
            fett = body.get("body_fat_pct")
            if fett is not None:
                eintrag["body_fat_pct"] = round(float(fett), 1)

            # Laden, einfuegen/aktualisieren, speichern
            data = load_weight_data()
            data["source"] = "Dashboard"

            # Bestehenden Eintrag am gleichen Datum ersetzen
            data["weights"] = [w for w in data["weights"] if w["date"] != datum]
            data["weights"].append(eintrag)
            data["weights"].sort(key=lambda w: w["date"])

            save_weight_data(data)

            self.send_json({
                "ok": True,
                "saved": eintrag,
                "total": len(data["weights"]),
            })
            print(f"  Gewicht gespeichert: {datum} = {gewicht} kg")

        except (json.JSONDecodeError, ValueError) as e:
            self.send_json({"error": str(e)}, 400)

    def handle_weight_delete(self):
        """Gewichtseintrag loeschen."""
        try:
            datum = self.path.split("/api/weight/")[1]
            data = load_weight_data()
            vorher = len(data["weights"])
            data["weights"] = [w for w in data["weights"] if w["date"] != datum]
            nachher = len(data["weights"])

            if vorher == nachher:
                self.send_json({"error": "Datum nicht gefunden"}, 404)
                return

            save_weight_data(data)
            self.send_json({"ok": True, "deleted": datum})
            print(f"  Gewicht geloescht: {datum}")


        except Exception as e:
            self.send_json({"error": str(e)}, 400)

    def send_json(self, obj, code=200):
        """JSON-Response senden."""
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Nur API-Aufrufe loggen, nicht jede Datei."""
        if args and "/api/" in str(args[0]):
            super().log_message(format, *args)


if __name__ == "__main__":
    print(f"Dashboard Server laeuft auf http://localhost:{PORT}")
    print(f"  Verzeichnis: {SCRIPT_DIR}")
    print(f"  Gewichtsdaten: {WEIGHT_FILE}")
    print()
    httpd = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer beendet.")
