# Quellcode nach GitHub übertragen

Der Schreibaufruf zu GitHub wurde in der Erstellungsumgebung mit „MCP tool call requires approval, but approval policy is never“ blockiert. Es wurde keine Datei im Repository angelegt.

Das ZIP enthält die Repository-Dateien einschließlich `.github/workflows`, `.gitignore` und `.gitattributes`. Nach dem Entpacken den gesamten Inhalt nach `jotebu/KNX-Alarmserver` übertragen, nicht einen zusätzlichen übergeordneten Projektordner. Keine privaten Konfigurationen hinzufügen.

Bei Verwendung von Git im entpackten Projektordner:

```bash
git init -b main
git add .
git commit -m "Add KNX alarmserver with typed DPT rules, dashboard and Raspberry installer"
git remote add origin https://github.com/jotebu/KNX-Alarmserver.git
git push -u origin main
```

Falls das Repository inzwischen bereits Commits enthält, stattdessen das aktuelle Repository klonen und die gelieferten Projektdateien dort kontrolliert übernehmen. Keinen erzwungenen Push verwenden.

Danach den Workflow **Tests** prüfen und mögliche Integrationsprobleme beheben. Erst nach erfolgreichen vollständigen Tests und dem Raspberry-/KNX-Abnahmetest einen Versionstag veröffentlichen. Die v0.1.0 ist eine Inbetriebnahmeversion. Der vorbereitete Release-Workflow erzeugt ausdrücklich ein Vorab-Release.
