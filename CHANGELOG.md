# Changelog

Alle folgenden Projektänderungen werden hier pro Version dokumentiert, neueste Version zuerst.

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
