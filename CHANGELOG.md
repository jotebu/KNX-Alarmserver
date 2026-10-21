# Changelog

Alle folgenden Projektänderungen werden hier pro Version dokumentiert, neueste Version zuerst.

## 0.10.04 – 21.10.2026

- Dashboard-Anfragen erhalten feste Zeitlimits einschließlich des Lesens der Antwort. Eine hängende Anfrage blockiert die automatische Aktualisierung nicht mehr bis zum Browser-Timeout.
- Aktualisierung auf eine gemeinsame API-Anfrage umgestellt; nur eine PBKDF2-Passwortprüfung pro Aktualisierung statt bisher zwei bis drei.
- Nächste Abfrage wird erst nach Abschluss der vorherigen geplant; bei Fehlern begrenzter Backoff, Pause in verdeckten Tabs und Wiederaufnahme beim Zurückkehren.
- Keine automatischen Wiederholungen von Schreibaktionen; Hinweis auf erneutes Laden bei ausbleibender Speicherbestätigung.
- Liveness-Endpunkt unabhängig von synchronen Passwort-Worker-Aufgaben ausgeführt.
- Regressionstests für hängende Anfragen, blockierte Antwortinhalte, Erholung, Backoff und Threadpool-Auslastung ergänzt; JavaScript-Tests in GitHub Actions aufgenommen.
- Die gemeldeten vollständigen zeitweisen Verbindungsabbrüche sind lokal noch nicht reproduziert. Diese Version behebt belegte Schwächen der Aktualisierung und ist anschließend im betroffenen Netzwerk zu prüfen.

## 0.10.03 – 21.10.2026

- Dashboard um KNX-Verbindungsverwaltung ergänzt: hinzufügen, bearbeiten, löschen, einzeln aktivieren sowie KNX-Empfang global einschalten.
- Formulare für UDP-Tunneling und Multicast-Routing mit Validierung von IPv4-Adressen, Port, physikalischer Adresse und eindeutigen Namen.
- Einstellungen dauerhaft in SQLite gespeichert und bei Neustarts wieder verwendet; vorhandene TOML-Verbindungen dienen bis zum ersten Dashboard-Speichern als Ausgangspunkt.
- KNX-Verbindungen werden beim Speichern ohne Webserver-Neustart neu aufgebaut.
- Schreibzugriff authentifiziert und mit Aktionsheader geschützt; konkurrierende veraltete Änderungen werden abgewiesen. Bei Speicherfehler wird die bisherige Konfiguration wieder aktiviert.
- Neue Installationen enthalten keine vorgegebenen Routeradressen.
- Vollständige Python-Tests erstmals einschließlich Web-/xknx-Abhängigkeiten ausgeführt.

## 0.10.02 – 21.10.2026

- Direkter Zugriff über `http://RASPBERRY-IP:8080`: Vorgabe für `server.host` in Beispielkonfiguration und Konfigurationslader auf `0.0.0.0` geändert.
- Installer-Option `--lan` stellt bestehende Installationen gezielt auf direkten LAN-Zugriff um, ohne Benutzer, Datenbank oder andere Einstellungen zu ersetzen.
- Update-Skript reicht die optionale Angabe `--lan` an den Installer weiter.
- Installationshinweise und Abschlussmeldung für LAN-Zugriff angepasst; veraltete GitHub-Sperrmeldung entfernt.
- Unkritische Meldung zu `reset-failed` bei Erstinstallation vermieden.
- Dieses Changelog eingeführt.

## 0.10.01 – 21.10.2026

- Projektversion auf das gewünschte Schema `0.10.01` umgestellt.
- Installation und lokaler Webstart auf dem Raspberry durch den Anwender bestätigt; Health-Endpunkt meldet Version 0.10.01.
- Grundlage: KNX/IP-Tunneling und Routing, allgemeine DPT-Auswertung, Alarmregeln, Weboberfläche, Quittierungen, SQLite und systemd-Installation.

## 0.1.0 – 21.10.2026

- Erster veröffentlichter Quellstand der Inbetriebnahmeversion.

