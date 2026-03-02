#!/usr/bin/env python3
"""
Garmin Login – Einmaliger Login und Token-Speicherung.

Nutzt die garth-Bibliothek, um sich bei Garmin Connect anzumelden
und den Token unter ~/.garth/ zu speichern.
"""

import sys
import os
import getpass
from pathlib import Path

# Token-Verzeichnis (Standard: ~/.garth/)
TOKEN_DIR = str(Path.home() / ".garth")

def main():
    """Hauptfunktion: Login bei Garmin Connect durchführen."""

    # garth importieren – falls nicht installiert, Hinweis geben
    try:
        import garth
    except ImportError:
        print("FEHLER: Die Bibliothek 'garth' ist nicht installiert.")
        print("Bitte installieren mit: pip install garth")
        sys.exit(1)

    print("=" * 50)
    print("  Garmin Connect – Login")
    print("=" * 50)
    print()

    # Zugangsdaten abfragen (niemals hardcoded!)
    email = input("Garmin E-Mail: ").strip()
    if not email:
        print("FEHLER: E-Mail darf nicht leer sein.")
        sys.exit(1)

    passwort = getpass.getpass("Garmin Passwort: ")
    if not passwort:
        print("FEHLER: Passwort darf nicht leer sein.")
        sys.exit(1)

    print()
    print("Anmeldung läuft...")

    try:
        # Login durchführen
        garth.login(email, passwort)

        # Token-Verzeichnis erstellen falls nötig
        os.makedirs(TOKEN_DIR, exist_ok=True)

        # Token speichern
        garth.save(TOKEN_DIR)

        print()
        print("LOGIN ERFOLGREICH!")
        print(f"Token wurde gespeichert unter: {TOKEN_DIR}")
        print()
        print("Du kannst jetzt garmin_fetch.py ausführen,")
        print("um deine Daten abzurufen.")

    except Exception as e:
        print()
        print(f"LOGIN FEHLGESCHLAGEN: {e}")
        print()
        print("Mögliche Ursachen:")
        print("  - E-Mail oder Passwort falsch")
        print("  - Zwei-Faktor-Authentifizierung aktiv")
        print("  - Garmin-Server nicht erreichbar")
        print("  - Zu viele Login-Versuche (bitte warten)")
        sys.exit(1)


if __name__ == "__main__":
    main()
