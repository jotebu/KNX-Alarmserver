# KNX Alarmserver

Eigenständiger Störungs- und Alarmserver für Raspberry Pi OS (64 Bit, Bookworm/Trixie, Python ≥ 3.11). Version **0.10.01 – Inbetriebnahmeversion**. Der Abnahmetest mit einem echten MDT-IP-Router und einem Raspberry Pi steht noch aus.

## Funktionen

- Deutsche, responsive Weboberfläche mit Meldungen, Historie und Telegrammmonitor.
- KNX/IP-Tunneling per UDP oder Multicast-Routing über xknx; mehrere Tunnel konfigurierbar.
- Typisierte DPT-Auswertung über den vollständigen verfügbaren xknx-DPT-Katalog: Binärwerte, Ganzzahlen, Fließkommazahlen, Prozentwerte, Aufzählungen, Text, Datum, Zeit und strukturierte Werte. Nicht jeder von KNX definierte oder herstellerspezifische DPT ist in xknx implementiert. Unbekannte DPT werden abgewiesen; es gibt keinen stillen Rückfall auf einen anderen Untertyp.
- Flexible Alarmregeln: Gleichheit, Ungleichheit, obere/untere Grenzwerte, Wertebereiche, Listen und Textsuche. Numerische Hysterese verhindert Flattern an der Schaltschwelle.
- Strukturierte DPT können über einzelne Felder ausgewertet werden. Datenpunkte mit `monitor` zeigen ihren Wert an, ohne einen Alarm auszulösen.
- Zustände: unbekannt, normal, aktiv/unquittiert, aktiv/quittiert und gegangen/unquittiert.
- Benutzerbezogene Quittierung mit Zeitstempel; SQLite speichert Alarmzustände und Ereignisse.
- Dienststart über systemd, Konfigurationsprüfung, Sicherungsbefehl und Installation in isolierter Python-Umgebung.
- Updates anhand expliziter Git-Versionstags mit vorheriger Datenbanksicherung und Rückwechsel der Programmversion bei fehlgeschlagenem Webstart.
- GitHub Actions für Tests, Paketbau und Vorab-Releases.

Die Anwendung beobachtet empfangene Gruppentelegramme (Write und Response). Sie sendet weder Gruppenleseanforderungen noch Schaltbefehle. Tunneling benötigt dabei die üblichen KNXnet/IP-Verbindungs- und Bestätigungspakete. Sie ersetzt keine zertifizierte Sicherheits-, Brandmelde- oder Einbruchmeldeanlage.

## Erstinstallation

Auf einem Raspberry Pi mit Raspberry Pi OS 64 Bit und Internetzugang:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/jotebu/KNX-Alarmserver.git
cd KNX-Alarmserver
sudo bash scripts/install.sh
```

Beim ersten Durchlauf wird das Passwort für den Webbenutzer `admin` interaktiv angelegt (mindestens 12 Zeichen). Es gibt kein Standardpasswort. Bestehende Konfigurationen werden erhalten. Die erste Installation verwendet den aktuellen Stand des ausgecheckten Repositorys. Für spätere freigegebene Versionen vor der Installation einen geprüften Tag auschecken.

Standardmäßig lauscht der Dienst auf **127.0.0.1:8080**, KNX ist deaktiviert und die Alarmmatrix leer. Das verhindert erfundene Alarmadressen. Bestehende nginx-/Zabbix-Dienste auf Port 80 werden nicht verändert.

Zugriff zunächst über SSH-Tunnel vom eigenen Rechner:

```bash
ssh -L 8080:127.0.0.1:8080 BENUTZER@RASPBERRY-IP
```

Dann `http://127.0.0.1:8080` öffnen. Für dauerhaften LAN-Zugriff einen HTTPS-Reverse-Proxy einrichten. Bei direktem Zugriff über `host = "0.0.0.0"` erfolgt HTTP-Basic-Anmeldung ohne Transportverschlüsselung; nur über ein vertrauenswürdiges Netz/VPN verwenden, keine Portfreigabe ins Internet. Ein Reverse-Proxy sollte zusätzlich Anmeldeversuche begrenzen. Alle Benutzer dieser Version können sämtliche Daten sehen und quittieren; eine Rollenverwaltung ist noch nicht enthalten.

## Konfiguration

```bash
sudo nano /etc/knx-alarmserver/config.toml
sudo nano /etc/knx-alarmserver/alarms.csv
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver check
sudo systemctl restart knx-alarmserver
```

Die genaue Struktur steht in [config/config.example.toml](config/config.example.toml). Bei Tunneling `gateway_ip` auf die tatsächliche MDT-IP setzen und `enabled = true` aktivieren. Beispiel-IP-Adressen im Repository stammen aus einem reservierten Dokumentationsnetz. Private Gebäudeadressen, echte Alarmmatrizen, Passwörter und KNX-Schlüssel gehören nicht ins öffentliche Repository.

### MDT, Linienkopplung und Routing

- Für den ersten Test einen freien Tunneling-Kanal des betreffenden MDT-Routers verwenden. Routermodell, Firmware und ETS-Einstellungen müssen zum unverschlüsselten UDP-Tunneling passen.
- Nicht jedes Telegramm einer Unterlinie wird auf der Hauptlinie sichtbar. Filtertabellen, Kopplung, Gruppenadresszuordnung und die MDT-Weiterleitung müssen zu den Alarmadressen passen. Das ist kein KNX-Busmonitor, der beliebigen, ausgefilterten Verkehr über alle Linien hinweg mitschneiden kann.
- Falls notwendig mehrere Tunnel zu den betreffenden Linien konfigurieren. Wiederholte Werte erzeugen keine doppelten Alarmereignisse. Die Empfangsreihenfolge widersprüchlicher Werte ist maßgeblich; es gibt keine automatische Auswahl einer vertrauenswürdigeren Quelle.
- Bei Routing nur einen Empfänger je gemeinsamem Multicast-Netz konfigurieren. VLANs, Firewall und Switch müssen UDP/3671 und die konfigurierte Multicast-Gruppe transportieren. Die physikalische Adresse vorab mit ETS abstimmen.
- Ein geöffnetes Routing-Socket bestätigt keine Verbindung zu einem bestimmten Router. Der letzte Telegrammempfang wird deshalb separat angezeigt.
- KNX IP Secure / Data Secure ist in dieser Version **noch nicht konfigurierbar**. Verschlüsselte Telegramme nicht durch Abschalten der Gebäudesicherheit passend machen; dafür ist eine spätere Secure-Erweiterung erforderlich.

### Alarmmatrix und Datentypen

Semikolongetrennte UTF-8-CSV mit Kopfzeile:

```csv
id;name;group_address;dpt;operator;threshold;hysteresis;field;area;priority
pump;Pumpenstörung;1/2/3;1.005;eq;true;0;;Technik;critical
hot;Übertemperatur;1/2/4;9.001;gt;50;2;;Technik;critical
message;Statustext;1/2/5;16.001;contains;Störung;0;;Technik;warning
```

Diese Gruppenadressen sind ausschließlich Beispiele und dürfen nicht ungeprüft übernommen werden. Weitere Beispiele: [config/alarms.example.csv](config/alarms.example.csv). `config/alarms.csv` enthält bewusst nur den Kopf. Die bestehende Gebäude-Alarmmatrix wird später anhand ihrer echten Spalten in dieses Format überführt; Symcon-Objekt-IDs sind für den direkten KNX-Empfang nicht erforderlich.

| Feld | Bedeutung |
| --- | --- |
| `id` | Dauerhaft eindeutige ID mit Buchstaben, Zahlen, `_` oder `-` |
| `name` | Anzeigename |
| `group_address` | KNX-Gruppenadresse, dreistufig |
| `dpt` | Exakter DPT, z. B. `9.001`, `16.001`, `20.102`; Hauptnummern sind möglich, wenn xknx dafür einen Basistyp bereitstellt |
| `operator` | `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `between`, `outside`, `contains`, `in`, `monitor` |
| `threshold` | JSON-Wert oder Klartext; z. B. `true`, `50`, `[20,80]`, `[1,4]` oder `Störung` |
| `hysteresis` | Nichtnegative Zahl in derselben Einheit wie der dekodierte Messwert; sonst `0` |
| `field` | Optionaler Feldpfad für strukturierte DPT, z. B. `control`, `hour` oder `items.0`; richtet sich nach der xknx-Dekodierung |
| `area` | Bereich/Ort |
| `priority` | `info`, `warning`, `critical` |

JSON-Zahlen werden als Zahlen, `true`/`false` als Boolean behandelt. Text, der wie JSON aussieht (etwa der Text `123`), als JSON-String und mit korrekter CSV-Quotierung speichern; Excel/CSV-Schreibprogramme übernehmen diese Quotierung. Textsuche ist groß-/kleinschreibungsabhängig. `eq` vergleicht dekodierte Werte; bei Fließkommazahlen sind Grenzwertregeln meist geeigneter.

Aufzählungen werden für Regeln auf ihren numerischen KNX-Wert normalisiert; die Anzeige ergänzt den Namen, soweit xknx ihn bereitstellt. Komplexe Werte werden als JSON angezeigt und über `field` ausgewertet. Datum/Zeit sind strukturierte Werte oder ISO-Text entsprechend dem Decoder. Für komplizierte DPT zunächst `monitor` verwenden und die tatsächlich dekodierten Feldnamen prüfen. Nicht vorhandene Felder oder ein falscher Werttyp werden als DPT-/Regelfehler angezeigt.

Beispiel Hysterese: `gt;50;2` aktiviert bei **> 50** und bleibt aktiv, solange der Wert **> 48** ist. Bei **≤ 48** geht der Alarm. `ge` schließt den Grenzwert ein. Bei `outside;[20,80];3` aktiviert ein Wert **< 20** oder **> 80** und geht nach Rückkehr in **[23,77]**. Hysterese muss bei Bereichsregeln kleiner als die halbe Bereichsbreite sein.

Verfügbare DPT auflisten:

```bash
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver dpt-list
```

Es ist in Version 0.10.01 ein Datenpunkt je Gruppenadresse vorgesehen. Für mehrere Regeln auf derselben Adresse ist später eine Trennung von Datenpunkt- und Regelkonfiguration nötig. Werden Gruppenadresse, DPT oder Regel eines bereits gespeicherten Alarms geändert, eine neue ID verwenden; vorhandene Zustände werden nicht stillschweigend umgedeutet.

## Zustände und Quittierung

Ein kommender Alarm wird unquittiert gespeichert. Quittieren setzt den lokalen Quittierungsstatus, nicht den KNX-Wert. Geht eine unquittierte Störung, bleibt sie als „Gegangen · unquittiert“ stehen. Ein erneutes Kommen erfordert eine neue Quittierung. Wiederholte identische Telegramme aktualisieren den Empfangszeitpunkt ohne neue Alarmereignisse.

Nach Neustart sind zuvor gespeicherte Werte als alt markiert, bis ein gültiges Telegramm eintrifft. Vor dem ersten Empfang heißt der Zustand „Unbekannt“. Ungültige Nutzdaten setzen einen sichtbaren DPT-/Regelfehler und behalten den letzten gültigen Alarmzustand. `Normal` bedeutet zuletzt empfangener Normalwert, nicht zyklisch geprüfte Erreichbarkeit. Zyklische Statusüberwachung, Initialabfragen, Entprellung und Verzögerungen sind noch nicht enthalten. Zustandswechsel während eines Ausfalls können durch den rein passiven Empfänger nicht rekonstruiert werden.

## Betrieb und Sicherung

```bash
systemctl status knx-alarmserver --no-pager
journalctl -u knx-alarmserver -f
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver user-add andy
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver backup /var/lib/knx-alarmserver/backups/manuell.sqlite3
```

Bei `user-add` wird ein vorhandenes Benutzerpasswort ersetzt. Kennwörter werden mit PBKDF2 und individuellem Salt gespeichert. Das Backup-Ziel darf noch nicht existieren. Die SQLite-Backup-API berücksichtigt WAL-Daten; eine einzelne aktive `.sqlite3`-Datei nicht einfach kopieren. Zusätzlich `/etc/knx-alarmserver` sichern. Im Betrieb erfolgt keine automatische NAS-Sicherung; ein vorhandenes Backupkonzept muss gesondert angebunden werden.

Ereignisse werden standardmäßig 365 Tage behalten und stündlich bereinigt (`retention_days`). Der Telegrammmonitor enthält nur die letzten 250 Telegramme im RAM. Der aktuelle Wert wird gespeichert, aber es gibt keine vollständige Messwert-Zeitreihe. Update-Sicherungen und alte Programmverzeichnisse werden nicht automatisch entfernt.

`/health/live` bestätigt ausschließlich einen laufenden Webprozess. `/api/ready` benötigt Anmeldung und liefert nur bei aktivierten, bereiten KNX-Verbindungen HTTP 200; sonst 503. Routing-Bereitschaft bezeichnet das lokale Socket, keine nachgewiesene Bus-Erreichbarkeit.

## Updates und Releases

Sobald ein entsprechender geprüfter Versionstag veröffentlicht wurde:

```bash
sudo bash /opt/knx-alarmserver/current/source/scripts/update.sh v0.10.02
```

Der Befehl installiert genau diesen Tag, prüft die Paketversion und erhält die lokale Konfiguration. Das ist ein über GitHub verwaltetes **Python-Paket mit systemd-Installer**, noch kein Debian-APT-Repository und kein `.deb`-Paket. Python-Abhängigkeiten werden von PyPI geladen; Internetzugang ist erforderlich. Direkte Abhängigkeiten sind fest versioniert, transitive Abhängigkeiten sind noch nicht vollständig mit Hashes gesperrt.

Vor einem Update wird eine konsistente SQLite-Sicherung angelegt. Schlägt der anschließende Webstart fehl, wird die vorige Programmversion aktiviert. Die Datenbank wird dabei nicht automatisch zurückgesetzt. Bei künftigen Schemaänderungen müssen Rückwärtskompatibilität und Rücksicherung explizit geprüft werden. Ein erfolgreicher Webstart beweist noch keine KNX-Verbindung.

Entwickler veröffentlichen nach erfolgreichen Tests einen Tag, dessen Name der Paketversion entspricht:

```bash
git tag v0.10.01
git push origin v0.10.01
```

Der Release-Workflow testet erneut, baut Wheel und Source-Paket und veröffentlicht ein GitHub-Vorab-Release mit SHA256-Prüfsummen. Er installiert nichts auf dem Raspberry. Release-Tags werden nicht vom Alarmserver automatisch erzeugt oder verändert. Der erste echte KNX-/Pi-Test ist vor produktiver Freigabe erforderlich.

## Entwicklung und Prüfung

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m unittest discover -s tests -v
bash -n scripts/install.sh scripts/update.sh
```

GitHub CI prüft Python 3.11 und 3.13, die echten Decoder von xknx, Alarmregeln und die HTTP-API. Ohne installierte Web-/KNX-Abhängigkeiten werden diese Integrationstests lokal als übersprungen angezeigt; reine Konfigurations-, Regel- und Datenbanktests benötigen nur Python. Die CI verlangt ausdrücklich die Bibliotheksimporte. Genau ein Webworker ist vorgesehen; mehrere Worker würden mehrere Busverbindungen erzeugen.

## Nächste Ausbaustufen

1. Routermodell, KNX-Secure-Nutzung, Filtertabellen und tatsächlichen Telegrammempfang prüfen.
2. Echte Alarmmatrix importieren und mit Testalarmen abnehmen.
3. Konfigurationsverwaltung in der Weboberfläche, Benutzerrollen und Login-Sitzungen.
4. Push/E-Mail, Zeitprogramme, Eskalation und zyklische Erreichbarkeitsüberwachung.
5. Debian-Paket/APT-Verteilung, vollständige Dependency-Lockdatei und weitere Hardwaretests.
