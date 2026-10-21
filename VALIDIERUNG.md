# Prüfstand 0.10.01

Stand: 21.10.2026. Erste Implementierung, noch keine produktive Freigabe.

## Hier ausgeführt

- Python 3.12 (erneut am 21.10.2026): reine Konfigurations-, Datenbank- und Regeltests mit `unittest`.
- Ergebnis: 19 Tests erfolgreich, 13 Bibliotheks-/Webtests mangels Abhängigkeiten übersprungen.
- Zustandswechsel, persistierende Quittierung, wiederkehrende Alarme, Neustartkennzeichnung, idempotente Telegramme, Passwortprüfung und konsistente SQLite-Sicherung.
- Regeln für Zahlen, Texte, Aufzählungswerte und Felder strukturierter Daten; numerische Hysterese und sichtbare Dekodierungsfehler.
- Bash-Syntaxprüfung für Installation und Update.

## Noch auszuführen

- Tests mit installierten FastAPI-, HTTPX- und xknx-Paketen: Diese Pakete sind lokal nicht vorhanden und konnten wegen der Netzwerkbeschränkung nicht installiert werden. Die zugehörigen Tests werden hier ausdrücklich übersprungen.
- Der vorbereitete GitHub-Workflow installiert die Pakete und führt sämtliche Tests unter Python 3.11 und 3.13 aus. Der Quellstand wird am 21.10.2026 erstmals über den GitHub-Zugriff veröffentlicht; das CI-Ergebnis ist separat in GitHub Actions zu prüfen.
- Installer und Update-Rückwechsel auf Raspberry Pi OS mit systemd testen. Hier wurde nur die Shellsyntax geprüft.
- Echtes KNX/IP-Tunneling bzw. Routing am MDT-Router, Sichtbarkeit aller gewünschten Linien und Fehlerszenarien testen.
- Weboberfläche im Browser und auf mobilen Geräten abnehmen. Ein gerenderter visueller Browsertest steht aus.

Der Quellcode enthält keine privaten Gebäude-IP-Adressen oder echten Alarmgruppenadressen.
