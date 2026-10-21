# KNX Alarmserver

Eigenständiger Störungs- und Alarmserver für Raspberry Pi OS (64 Bit, Bookworm/Trixie, Python ≥ 3.11). Version **0.10.08 – Inbetriebnahmeversion**. Der Empfang echter KNX-Gruppentelegramme über einen MDT-IP-Router wurde auf Raspberry Pi bestätigt. ETS-Import und Telegrammempfang wurden vom Anwender bestätigt; Wiederverbindung und Alarmmatrix-Abnahme stehen noch aus.

## Funktionen

- Deutsche, responsive Weboberfläche mit Meldungen, Historie, Telegrammmonitor, KNX-Verbindungsverwaltung und ETS-Gruppenadress-Import.
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

Standardmäßig lauscht der Dienst auf **0.0.0.0:8080**. Die Weboberfläche ist direkt unter `http://RASPBERRY-IP:8080` erreichbar; SSH-Tunnel sind nicht erforderlich. KNX ist zunächst deaktiviert und die Alarmmatrix leer. nginx auf Port 80 wird nicht verändert.

Anmeldung und Sitzungscookie sind bei HTTP unverschlüsselt. Diesen Zugriff nur im vertrauenswürdigen LAN oder über VPN verwenden, ohne Internet-Portfreigabe. Für verschlüsselten Webzugriff einen HTTPS-Reverse-Proxy einrichten und bei Bedarf `host = "127.0.0.1"` setzen. Browser melden sich über ein Formular an; Abmelden beendet die Sitzung. Die Rollen Admin, User und Viewer gelten sowohl im Dashboard als auch für direkte API-Aufrufe.

### Bestehende Installation auf LAN-Zugriff umstellen

Bestehende Konfigurationen werden beim Update erhalten. Mit `--lan` wird gezielt nur `server.host` auf `0.0.0.0` gesetzt; Benutzer, Datenbank, Alarmmatrix und andere Einstellungen bleiben erhalten:

```bash
sudo bash scripts/install.sh --lan
```

Die Option ist idempotent und auch dann verwendbar, wenn LAN-Zugriff bereits manuell aktiviert wurde. Sie ist eine ausdrückliche Konfigurationsänderung; ein Programm-Rückwechsel stellt diese Einstellung nicht automatisch zurück.

Änderungen je Version stehen in [CHANGELOG.md](CHANGELOG.md).

## Konfiguration

```bash
sudo nano /etc/knx-alarmserver/config.toml
sudo nano /etc/knx-alarmserver/alarms.csv
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver check
sudo systemctl restart knx-alarmserver
```

### KNX-Verbindungen im Dashboard

1. Weboberfläche öffnen und anmelden, dann **KNX-Verbindungen** wählen.
2. **Verbindung hinzufügen** wählen und einen eindeutigen Namen angeben.
3. Für **Tunneling (UDP)** die tatsächliche Router-IPv4-Adresse und den Port (gewöhnlich 3671) eintragen. Die lokale IPv4-Adresse ist bei mehreren Netzwerkschnittstellen optional anzugeben.
4. Für **Routing (Multicast)** eine in ETS abgestimmte freie physikalische Adresse sowie die Multicast-Adresse eintragen. Routing benötigt passende Netzwerkeinstellungen.
5. **Verbindung aktiv** und für den Empfang zusätzlich **KNX-Empfang aktivieren** auswählen; **Speichern und übernehmen** anklicken.
6. Oben Verbindungsstatus und letzten Empfang prüfen; unter **Telegramme** den tatsächlichen Verkehr kontrollieren.

Einträge lassen sich bearbeiten, einzeln deaktivieren oder nach Bestätigung löschen. **Aktivierung speichern** übernimmt den globalen Empfangsschalter. **Neu laden** verwirft ungespeicherte Formulareingaben und lädt die aktuelle Konfiguration. Bei gleichzeitiger Bearbeitung wird eine veraltete Version mit einem Hinweis abgewiesen; dann neu laden und die Änderung erneut vornehmen.

Verbindungsänderungen werden ohne Webserver-Neustart übernommen. Dafür werden die bisherigen KNX-Verbindungen geschlossen und neu aufgebaut; während dieser kurzen Unterbrechung können Telegramme fehlen. Speichern bestätigt die Konfiguration, nicht die Erreichbarkeit des Routers. Verbindungsfehler erscheinen im Status und Protokoll.

Die anfänglichen KNX-Einstellungen stammen aus `config.toml`. Ab dem ersten Speichern im Dashboard hat der in SQLite gespeicherte KNX-Abschnitt Vorrang, auch nach Neustarts und Updates. Webserver-Einstellungen und Alarmmatrix bleiben weiterhin dateibasiert. Ein SQLite-Backup enthält somit auch die Dashboard-Verbindungen. Nur Admins können KNX-Verbindungen und ETS-Import verwalten.

Neuinstallationen enthalten keine vorgegebenen Router-Verbindungen. Bei Updates bleibt die bestehende Konfiguration erhalten. Ein vorhandener Beispielrouter mit `192.0.2.30` muss im Dashboard bearbeitet oder gelöscht werden; diese Dokumentationsadresse ist kein realer Router.

Die manuelle Alternative steht in [config/config.example.toml](config/config.example.toml). Private Gebäudeadressen, echte Alarmmatrizen, Passwörter und KNX-Schlüssel gehören nicht ins öffentliche Repository. KNX IP Secure und Data Secure bleiben noch nicht unterstützt.

### ETS-Gruppenadressen im Dashboard importieren

In ETS im Gruppenadressen-Fenster den gewünschten Baum auswählen, rechts anklicken und **Gruppenadressen exportieren** wählen. Für Namen, Beschreibungen und DPT vorzugsweise das aktuelle **XML-Format** verwenden; das alte ETS4-kompatible XML enthält keine DPT-Angaben. Siehe [KNX-Exportdokumentation](https://support.knx.org/hc/en-us/articles/360022237580-Group-Address-Export).

1. Im Dashboard **ETS-Import** öffnen und `.xml` oder `.csv` auswählen (maximal 4 MiB / 10000 Adressen je Datei).
2. **Vorschau prüfen** klicken. Noch nichts wird gespeichert. Namen, DPT, Änderungen und Hinweise kontrollieren; über Suche und Seitenwechsel auch größere Exporte prüfen.
3. Standardmäßig **Ergänzen / vorhandene Adressen aktualisieren** verwenden. Dabei bleiben Adressen außerhalb der Datei erhalten. **Gesamten ETS-Katalog ersetzen** entfernt nach Bestätigung die nicht enthaltenen Katalogeinträge; Alarmregeln werden in beiden Modi erhalten.
4. **Vorschau übernehmen** klicken. Die Zuordnungen gelten sofort für danach empfangene Telegramme. Bereits im Telegrammring vorhandene Einträge werden nicht nachträglich umgedeutet.

Der Katalog wird in SQLite gespeichert, übersteht Neustarts und Updates und ist im vorhandenen SQLite-Backup enthalten. **Gespeicherten Katalog laden** zeigt den aktuellen Gesamtstand. Der Import verändert weder den KNX-Router noch die ETS-Datei und legt keine Alarmregeln an. Diese benötigen weiterhin eine eigene Alarmmatrix. Für bestehende Alarme hat der DPT der Alarmregel Vorrang vor dem ETS-Katalog.

Unterstützt werden XML-Gruppenadress-Exporte mit dreistufigen, zweistufigen oder numerischen Adressen (intern dreistufig normalisiert). CSV benötigt eine Kopfzeile und eine erkennbare Adressspalte (`Address`, `Gruppenadresse` oder `Adresse`), dazu `Name`, `Group name` oder die Hierarchiespalten `Main`/`Middle`/`Sub`. Semikolon, Komma und Tabulator werden erkannt. Unterstützt sind insbesondere ETS 3/1, 1/1 und 1/3; ETS 3/3 ohne Adressspalte bitte als XML exportieren. CSV kann UTF-8, UTF-16 mit BOM oder Windows-1252 verwenden; XML UTF-8 oder UTF-16 mit BOM. Vollständige `.knxproj`-Archive, OPC-Dateien und kennwortgeschützte Projekte werden noch nicht eingelesen.

`DPST-9-1` wird beispielsweise zu `9.001`. Eine Hauptnummer zusammen mit genau einem passenden Untertyp wird auf diesen konkreten Typ normalisiert. Fehlende oder mehrere unterschiedliche Untertypen sowie nicht unterstützte Untertypen werden markiert und nicht geraten. Für solche Katalogeinträge bleibt die Rohwertanzeige erhalten; eindeutige DPT in ETS korrigieren und erneut exportieren. Doppelte oder ungültige Gruppenadressen lehnen die gesamte Datei ab. Fehlgeschlagene Datei- oder Vorschauprüfungen verändern den gespeicherten Katalog nicht. Bei gleichzeitigem Import wird eine veraltete Vorschau abgewiesen. Eine Speicherbestätigung nach Timeout zuerst über den gespeicherten Katalog prüfen.

### MDT, Linienkopplung und Routing

- Für den ersten Test einen freien Tunneling-Kanal des betreffenden MDT-Routers verwenden. Routermodell, Firmware und ETS-Einstellungen müssen zum unverschlüsselten UDP-Tunneling passen.
- Nicht jedes Telegramm einer Unterlinie wird auf der Hauptlinie sichtbar. Filtertabellen, Kopplung, Gruppenadresszuordnung und die MDT-Weiterleitung müssen zu den Alarmadressen passen. Das ist kein KNX-Busmonitor, der beliebigen, ausgefilterten Verkehr über alle Linien hinweg mitschneiden kann.
- Falls notwendig mehrere Tunnel zu den betreffenden Linien konfigurieren. Wiederholte Werte erzeugen keine doppelten Alarmereignisse. Die Empfangsreihenfolge widersprüchlicher Werte ist maßgeblich; es gibt keine automatische Auswahl einer vertrauenswürdigeren Quelle.
- Bei Routing nur einen Empfänger je gemeinsamem Multicast-Netz konfigurieren. VLANs, Firewall und Switch müssen UDP/3671 und die konfigurierte Multicast-Gruppe transportieren. Die physikalische Adresse vorab mit ETS abstimmen.
- Ein geöffnetes Routing-Socket bestätigt keine Verbindung zu einem bestimmten Router. Der letzte Telegrammempfang wird deshalb separat angezeigt.
- KNX IP Secure / Data Secure ist in dieser Version **noch nicht konfigurierbar**. Verschlüsselte Telegramme nicht durch Abschalten der Gebäudesicherheit passend machen; dafür ist eine spätere Secure-Erweiterung erforderlich.

### DPT-Abdeckung

Die genaue Abdeckung und noch fehlende Familien stehen in [DPT-SUPPORT.md](DPT-SUPPORT.md). `20` allein wird als 1-Byte-Zahl 0–255 angezeigt. `20.102` verwendet die deutschen HVAC-Betriebsarten; bitcodierter HVAC-Status bleibt getrennt. Unbekannte konkrete Untertypen werden nicht auf andere DPT umgedeutet. Vier- und fünfstellige Untertypen werden angenommen, wenn der passende Decoder vorhanden ist. Bereits importierte ETS-Zuordnungen nach dem Update über eine neue Vorschau erneut übernehmen, damit bisher abgewiesene DPT neu geprüft werden.

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

Es ist in dieser Version ein Datenpunkt je Gruppenadresse vorgesehen. Für mehrere Regeln auf derselben Adresse ist später eine Trennung von Datenpunkt- und Regelkonfiguration nötig. Werden Gruppenadresse, DPT oder Regel eines bereits gespeicherten Alarms geändert, eine neue ID verwenden; vorhandene Zustände werden nicht stillschweigend umgedeutet.

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
sudo bash /opt/knx-alarmserver/current/source/scripts/update.sh v0.10.08
```

Der Befehl installiert genau diesen Tag, prüft die Paketversion und erhält die lokale Konfiguration. Das ist ein über GitHub verwaltetes **Python-Paket mit systemd-Installer**, noch kein Debian-APT-Repository und kein `.deb`-Paket. Python-Abhängigkeiten werden von PyPI geladen; Internetzugang ist erforderlich. Direkte Abhängigkeiten sind fest versioniert, transitive Abhängigkeiten sind noch nicht vollständig mit Hashes gesperrt.

Vor einem Update wird eine konsistente SQLite-Sicherung angelegt. Schlägt der anschließende Webstart fehl, wird die vorige Programmversion aktiviert. Die Datenbank wird dabei nicht automatisch zurückgesetzt. Bei künftigen Schemaänderungen müssen Rückwärtskompatibilität und Rücksicherung explizit geprüft werden. Ein erfolgreicher Webstart beweist noch keine KNX-Verbindung.

Entwickler veröffentlichen nach erfolgreichen Tests einen Tag, dessen Name der Paketversion entspricht:

```bash
git tag v0.10.08
git push origin v0.10.08
```

Der Release-Workflow testet erneut, baut Wheel und Source-Paket und veröffentlicht ein GitHub-Vorab-Release mit SHA256-Prüfsummen. Er installiert nichts auf dem Raspberry. Release-Tags werden nicht vom Alarmserver automatisch erzeugt oder verändert. Der erste echte KNX-/Pi-Test ist vor produktiver Freigabe erforderlich.

## Anmeldung und Benutzerverwaltung

| Rolle | Meldungen, Historie und Telegramme sehen | Quittieren | KNX / ETS / Benutzer verwalten |
|---|---|---|---|
| Admin | Ja | Ja | Ja |
| User | Ja | Ja | Nein |
| Viewer | Ja | Nein | Nein |

Nach dem Update im Browser die Serveradresse öffnen und mit dem bisherigen Konto anmelden. Bestehende Konten erhalten bei der Migration die Rolle **Admin**, ihre Kennwörter bleiben gültig. Neue Konten legt ein Admin unter **Benutzerverwaltung** an; die vorausgewählte Rolle ist Viewer. Dort können Admins auch Rollen ändern, Kennwörter setzen und Konten löschen. Der Benutzername bleibt beim Bearbeiten unverändert. Der letzte Admin kann nicht gelöscht oder herabgestuft werden.

Die Einstellungsreiter sind bei User und Viewer ausgeblendet; Viewer sehen auch keine Quittierschaltflächen. Der Server verweigert die entsprechenden API-Aufrufe unabhängig vom Dashboard mit HTTP 403. Quittierungen protokollieren weiterhin den angemeldeten Benutzer und Zeitpunkt. Bisherige Quittierungsnamen bleiben auch nach Löschen eines Kontos erhalten.

Eine Browser-Sitzung gilt 12 Stunden und überlebt einen Dienstneustart. Ein zufälliges Sitzungstoken liegt im HttpOnly-Cookie mit SameSite=Strict; in SQLite wird nur sein SHA256-Hash gespeichert. Bei direktem HTTPS setzt der Server zusätzlich Secure. Das Cookie ist nicht an eine IP-Adresse gebunden. Bei den regelmäßigen Dashboard-Abfragen wird die Sitzung geprüft, nicht erneut PBKDF2 berechnet. Passwörter bleiben individuell gesalzen mit PBKDF2-SHA256 und 600.000 Durchläufen gespeichert. Weder Passwörter noch Tokens erscheinen in API-Benutzerlisten. Es gibt keine Standardkennwörter.

Abmelden widerruft die aktuelle Sitzung. Rollen- und Passwortänderungen sowie Kontolöschung widerrufen alle Sitzungen des betroffenen Kontos; anschließend erneut anmelden. API-Werkzeuge können weiterhin explizite HTTP-Basic-Zugangsdaten senden; auch dafür gelten die aktuellen Rollen. Der Browser fordert keine HTTP-Basic-Anmeldung mehr an.

Der frühere Schalter `KNX_ALARMSERVER_DISABLE_AUTH` wird nicht mehr ausgewertet. Auch ein vorhandenes `no-login-test.conf` kann die Anmeldung nicht mehr abschalten. `/test/hallo` entfällt. Die alte Testdatei kann nach dem Update entfernt werden:

```bash
sudo rm -f /etc/systemd/system/knx-alarmserver.service.d/no-login-test.conf
sudo systemctl daemon-reload
```

Falls ein Admin-Kennwort verloren geht, lässt sich über PuTTY ein Admin-Konto anlegen oder wiederherstellen; das Kennwort wird verdeckt abgefragt:

```bash
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver user-add admin --role admin
```

Ohne `--role` bleibt bei vorhandenen Konten die Rolle erhalten. Das erste neue CLI-Konto wird Admin, weitere CLI-Konten werden standardmäßig Viewer. Die Datenbank bleibt auch bei Rückkehr zu einer älteren Programmversion um die Rollen- und Sitzungstabellen erweitert; vor Updates erzeugt der Installer ein konsistentes SQLite-Backup.

## Verhalten bei Verbindungsproblemen

Das Dashboard holt Status, Meldungen und die gewählte Ansicht mit einer gemeinsamen Anfrage ab. Die Sitzung wird dafür einmal pro Aktualisierung geprüft; nur beim expliziten Basic-API-Zugriff wird das Passwort erneut berechnet. Leseanfragen einschließlich Antwortinhalt werden nach 10 Sekunden abgebrochen; Speicheraktionen nach 30 Sekunden. Eine ausbleibende Speicherbestätigung bedeutet nicht zwingend, dass nichts gespeichert wurde: zuerst **Neu laden** und den Stand prüfen, bevor erneut gespeichert wird.

Im Normalbetrieb erfolgt die nächste Aktualisierung fünf Sekunden nach Abschluss der vorherigen. Nach Fehlern steigt die Wartezeit auf 10, 20 und maximal 30 Sekunden; nach erfolgreichem Abruf wieder auf fünf Sekunden. Verdeckte Browser-Tabs pausieren die automatische Abfrage und aktualisieren beim Zurückkehren. Schreibaktionen werden nicht automatisch wiederholt. Angezeigte Daten bleiben bei Fehlern sichtbar und werden als möglicherweise veraltet gekennzeichnet.

`/health/live` verwendet keinen synchronen Worker für Passwortprüfungen. Ein Timeout beim TCP-Verbindungsaufbau ist dadurch jedoch nicht automatisch behoben. Die gemeldeten zeitweisen LAN-Ausfälle konnten im lokalen Lasttest nicht reproduziert werden; die Korrekturen beheben einen nachgewiesenen Hänger der Dashboard-Aktualisierung und reduzieren die Anfragebelastung.

## Entwicklung und Prüfung

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m unittest discover -s tests -v
node --test tests/dashboard_polling.cjs
bash -n scripts/install.sh scripts/update.sh
```

GitHub CI prüft Python 3.11 und 3.13, die echten Decoder von xknx, Alarmregeln und die HTTP-API. Ohne installierte Web-/KNX-Abhängigkeiten werden diese Integrationstests lokal als übersprungen angezeigt; reine Konfigurations-, Regel- und Datenbanktests benötigen nur Python. Die CI verlangt ausdrücklich die Bibliotheksimporte. Genau ein Webworker ist vorgesehen; mehrere Worker würden mehrere Busverbindungen erzeugen.

## Nächste Ausbaustufen

1. Routermodell, KNX-Secure-Nutzung, Filtertabellen und tatsächlichen Telegrammempfang prüfen.
2. Echte Alarmmatrix importieren und mit Testalarmen abnehmen.
3. Alarmmatrix-Verwaltung in der Weboberfläche.
4. Push/E-Mail, Zeitprogramme, Eskalation und zyklische Erreichbarkeitsüberwachung.
5. Debian-Paket/APT-Verteilung, vollständige Dependency-Lockdatei und weitere Hardwaretests.

