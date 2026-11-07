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

**Hinweis:** Der Installer ist fuer eine **Erstinstallation** gedacht. Er bricht bei erkannter vorhandener Installation ab und setzt keine Datenbank zurueck. Die KNX-Verbindung ist anfangs deaktiviert. Ein automatischer Update-Dienst fuer den Binärbetrieb ist in diesem Installationsweg noch nicht eingerichtet.

## Releases

https://github.com/jotebu/KNX-Alarmserver/releases

## Versionshistorie

Siehe [CHANGELOG.md](CHANGELOG.md).
