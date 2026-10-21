# Prüfstand

Stand: 21.10.2026. Projektversion 0.10.03, weiterhin Inbetriebnahmeversion.

## Für die KNX-Verbindungsverwaltung geprüft

- Python 3.12 mit FastAPI 0.143.0, Uvicorn 0.53.0, xknx 4.0.0 und HTTPX 0.28.1: 41 Tests erfolgreich, keine übersprungen.
- Echte xknx-Decoder und Konstruktoren, Alarmregeln, SQLite-Zustände und HTTP-Endpunkte geprüft.
- Verbindungen hinzufügen, bearbeiten und löschen, Speicherung über erneuten App-Start sowie Aufnahme ins SQLite-Backup geprüft.
- Authentifizierung, Aktionsheader, Cross-Site-Abweisung, Größenlimit, Eingabevalidierung und Konflikte bei veralteten Revisionen geprüft.
- Neuaufbau der Monitor-Verbindungen und Überspringen deaktivierter Verbindungen ohne reale Router-Sockets getestet.
- Simulierter Datenbankschreibfehler: bisherige Einstellungen und Monitor werden beibehalten beziehungsweise wieder aktiviert.
- Dashboard mit DOM-Simulation geprüft: Navigation, Hinzufügen, Bearbeiten, Wechsel zu Routing, Löschen und übertragene Formulardaten.
- JavaScript- und Shellsyntax geprüft.

## Auf dem Raspberry bestätigt

- Installation und lokaler Webstart von 0.10.01 sowie direkter Zugriff nach dem LAN-Umbau bestätigt.
- Zabbix, PostgreSQL und PHP entfernt; SSH, nginx, ntfy und Statusdisplay laufen.

## Noch offen

- Visuelle Abnahme der neuen Einstellungen im echten Browser, einschließlich mobiler Ansicht.
- Update auf die neue Version und persistente Verbindungsverwaltung auf Raspberry Pi OS prüfen.
- Echter KNX/IP-Empfang am MDT-Router, Wiederverbindung und Abnahme der Alarmmatrix.
- Update-Rückwechsel auf Raspberry Pi OS testen.
- NAS-Backup an SQLite, neue Verzeichnisse und weiterhin genutzte Dienste anpassen. Alter Backup-Timer bleibt bis dahin deaktiviert.

Das Changelog steht in [CHANGELOG.md](CHANGELOG.md).
