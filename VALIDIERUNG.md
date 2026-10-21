# Prüfstand 0.10.02

Stand: 21.10.2026. Inbetriebnahmeversion.

## Für 0.10.02 ausgeführt

- Python 3.12: 35 Tests, davon 22 erfolgreich und 13 wegen fehlender Web-/KNX-Abhängigkeiten übersprungen.
- LAN-Umstellung mit bestehender Konfiguration geprüft: andere Einstellungen, Dateirechte und einleitende Kommentare bleiben erhalten; wiederholte Anwendung funktioniert.
- Konfigurationslader: LAN-Vorgabe und ausdrücklich gesetztes Loopback geprüft.
- Ungültige Eingaben bleiben unverändert.
- Bash-Syntaxprüfung für Installer und Update erfolgreich.

## Auf dem Raspberry bestätigt

- Anwender hat Installation und Webstart von 0.10.01 bestätigt.
- systemd-Dienst aktiv, Health-Endpunkt liefert HTTP 200 und Version 0.10.01.
- Zabbix, PostgreSQL und PHP wurden im Zuge des Umbaus entfernt; SSH, nginx, ntfy und Statusdisplay laufen.
- Update auf 0.10.02 und LAN-Zugriff sind anschließend auf dem Raspberry zu prüfen.

## Noch offen

- Vollständige Web-/xknx-Tests mit installierten Abhängigkeiten; GitHub-CI-Ergebnis separat prüfen.
- Echter KNX/IP-Empfang am MDT-Router und Abnahme der Alarmmatrix.
- Update-Rückwechsel auf Raspberry Pi OS testen.
- Weboberfläche im Browser und auf mobilen Geräten abnehmen.
- Bestehendes NAS-Backup an SQLite, neue Verzeichnisse und weiterhin genutzte Dienste anpassen. Alter Backup-Timer bleibt bis dahin deaktiviert.

Das Changelog steht in [CHANGELOG.md](CHANGELOG.md).
