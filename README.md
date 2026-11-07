# KNX Alarmserver

Dieses Repository veroeffentlicht signierte ARM64-Nuitka-Versionen des KNX-Alarmservers. Der Python-Quellcode wird nicht oeffentlich bereitgestellt.

## Schnellinstallation auf Raspberry Pi OS (64 Bit)

Voraussetzungen: Raspberry Pi mit ARM64/aarch64, Debian 12 oder 13 bzw. Raspberry Pi OS 64 Bit, Internetzugang, freier TCP-Port 80 und sudo-Rechte.

**Ein Befehl direkt im Terminal:**

```bash
curl -fsSL https://raw.githubusercontent.com/jotebu/KNX-Alarmserver/main/install.sh -o /tmp/knx-alarmserver-install.sh && sudo bash /tmp/knx-alarmserver-install.sh
```

Der Befehl laedt den Installer automatisch herunter und startet ihn. Die Installation fragt interaktiv nach Admin-E-Mail, Vorname, Nachname und Passwort (mindestens 10 Zeichen). Danach ist die Weboberflaeche im LAN unter `http://RASPBERRY-IP/` erreichbar.

Vor dem Entpacken prueft der Installer das Release mit dem im Skript hinterlegten Ed25519-Public-Key und kontrolliert Dateigroesse, SHA-256 und Build-Version. Zusaetzlich werden ein eingeschraenkter Systembenutzer und ein systemd-Dienst eingerichtet.

**Sicherheit:** Ein als root ausgefuehrtes Skript aus dem Internet sollte vor der Ausfuehrung kontrolliert werden. Quelltext: [install.sh](install.sh). Die Weboberflaeche auf Port 80 ist ohne TLS nur fuer ein vertrauenswuerdiges LAN oder VPN geeignet; nicht direkt ins Internet weiterleiten.

**Hinweis:** Der Installer ist fuer eine **Erstinstallation** gedacht. Er bricht bei erkannter vorhandener Installation ab und setzt keine Datenbank zurueck. Die KNX-Verbindung ist anfangs deaktiviert. Der Installer richtet zudem den signierten Update-Dienst fuer die Update-Schaltflaeche im Dashboard ein. Updates werden nur nach Anforderung durch einen Administrator ausgefuehrt, nicht unbeaufsichtigt. Vor dem Umschalten wird die SQLite-Datenbank gesichert; bei fehlgeschlagenem Health-Check wird die bisherige Programmversion wieder aktiviert (die Datenbank wird dabei nicht automatisch zurueckgesetzt).

## Updatefunktion bei bereits installierter Binärversion nachruesten

Die bestehende Installation muss **nicht** neu installiert werden. Auf dem Raspberry:

```bash
curl -fsSL https://raw.githubusercontent.com/jotebu/KNX-Alarmserver/main/setup-updates.sh -o /tmp/knx-alarmserver-setup-updates.sh && sudo bash /tmp/knx-alarmserver-setup-updates.sh
```

Das Skript installiert den root-eigenen signaturpruefenden Update-Worker und den systemd-Path-Service. Es startet den Alarmserver nicht neu und behaelt die vorhandene Datenbank und Konfiguration. Es ueberschreibt einen vorhandenen Update-Worker nicht automatisch.

Pruefen:
```bash
systemctl is-active knx-alarmserver-update.path
systemctl status knx-alarmserver-update.service --no-pager
```

Bei einer spaeteren signierten Veroeffentlichung kann ein Admin die Aktualisierung aus der Weboberflaeche ausloesen. Die Update-Protokolle stehen unter `journalctl -u knx-alarmserver-update.service`. Fuer die aktuelle Version 1.0.19 ist noch kein neueres Release verfuegbar, daher kann der produktive Upgrade- und Rollbackpfad erst mit einer Folgeversion durchgaengig getestet werden.

## Releases

https://github.com/jotebu/KNX-Alarmserver/releases

## Versionshistorie

Siehe [CHANGELOG.md](CHANGELOG.md).
