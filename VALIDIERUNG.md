# Prüfstand

Stand: 21.10.2026. Projektversion 0.10.04, Inbetriebnahmeversion.

## Web-Aufrufe und Fehlererholung

- Python 3.12 mit den festgelegten FastAPI-/Uvicorn-/xknx-Versionen und HTTPX: 43 Tests erfolgreich, keine übersprungen.
- Vier JavaScript-Regressionstests mit Node: keine überlappenden Aktualisierungen, Timeout auch beim Antwortinhalt, Freigabe nach Fehlern, erfolgreiche Wiederaufnahme, begrenzter Backoff und Pause in verdeckten Tabs.
- Ein gemeinsamer authentifizierter Dashboard-Abruf statt mehrfacher Passwortprüfungen je Aktualisierung; Antwortdaten und Zugriffsschutz getestet.
- Belegter Regressionstest: Liveness bleibt bei einem ausgelasteten synchronen Passwort-Worker erreichbar.
- Echter TCP-Test mit Uvicorn, sechs parallelen Clients und jeweils 15 Aufrufen: keine HTTP-Fehler oder Verbindungsabbrüche. Der gemeldete vollständige Verbindungsverlust konnte lokal nicht reproduziert werden.
- JavaScript- und Shellsyntax erfolgreich geprüft.

## Weiterhin gültige Prüfungen

- KNX-Verbindungsverwaltung einschließlich Persistenz, Backup, Konfliktbehandlung und simulierter Speicherfehler geprüft.
- Echte xknx-Decoder, Alarmregeln und HTTP-API getestet.

## Noch offen

- Update und erneute Prüfung auf dem betroffenen Raspberry und Windows-Browser, insbesondere Öffnen des Dashboards, Abwarten und Wiederaufnahme nach Fehlern.
- Ursache der zeitweisen TCP-Verbindungsabbrüche im konkreten Netzwerk, falls sie nach dem Update weiterhin auftreten.
- Visuelle Abnahme im echten Browser und auf mobilen Geräten.
- Echter KNX-Empfang, MDT-Wiederverbindung und Alarmmatrix-Abnahme.
- NAS-Backup anpassen; alter Timer bleibt bis dahin deaktiviert.

Änderungen stehen in [CHANGELOG.md](CHANGELOG.md).
