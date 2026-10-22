# KNX Alarmserver

Eigenständiger Störungs- und Alarmserver für Raspberry Pi OS (64 Bit, Bookworm/Trixie, Python ≥ 3.11). Version **0.14.2 – Inbetriebnahmeversion**. Der Empfang echter KNX-Gruppentelegramme über einen MDT-IP-Router wurde auf Raspberry Pi bestätigt. ETS-Import und Telegrammempfang wurden vom Anwender bestätigt; Wiederverbindung und Alarmmatrix-Abnahme stehen noch aus.

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

Standardmäßig lauscht der Dienst direkt auf **0.0.0.0:80**. Die Weboberfläche ist unter `http://RASPBERRY-IP/` erreichbar, ohne Portangabe und ohne nginx. Port 80 muss frei sein. KNX ist zunächst deaktiviert und die Alarmmatrix leer. Der Dienst läuft weiterhin als Benutzer `knx-alarmserver`; systemd gewährt ausschließlich `CAP_NET_BIND_SERVICE` zum Binden niedriger Ports. nginx wird vom Installer weder installiert noch automatisch entfernt.

Anmeldung und Sitzungscookie sind bei HTTP unverschlüsselt. Diesen Zugriff nur im vertrauenswürdigen LAN oder über VPN verwenden, ohne Internet-Portfreigabe. Für verschlüsselten Webzugriff einen HTTPS-Reverse-Proxy einrichten und bei Bedarf `host = "127.0.0.1"` setzen. Browser melden sich über ein Formular an; Abmelden beendet die Sitzung. Die Rollen Admin, User und Viewer gelten sowohl im Dashboard als auch für direkte API-Aufrufe.

### Bestehende Installation direkt auf Port 80 umstellen

Bei einem normalen Update bleiben bestehende `host`-/`port`-Einstellungen erhalten. `--lan` setzt gezielt `server.host` auf `0.0.0.0`, `--port 80` setzt `server.port` auf 80. Beide Optionen lassen sich kombinieren; Benutzer, KNX-Verbindungen, ETS-Katalog, Datenbank und Alarmmatrix bleiben erhalten.

Wenn nginx nur als bisheriger Proxy für diesen Alarmserver verwendet wird, zuerst nginx stoppen, damit Port 80 frei ist. Anschließend installieren:

```bash
cd ~/KNX-Alarmserver
git pull --ff-only
sudo systemctl disable --now nginx
sudo bash scripts/install.sh --lan --port 80
curl --fail --max-time 5 http://127.0.0.1/health/live
```

Nach erfolgreicher Prüfung direkt `http://RASPBERRY-IP/` öffnen. Dann den nicht mehr benötigten nginx entfernen:

```bash
sudo apt-get purge nginx nginx-common
```

Kein `autoremove` nötig. Bei einer Installation ohne nginx die beiden nginx-Befehle auslassen. Andere Webdienste, die Port 80 belegen, müssen vorab auf einen anderen Port verlegt werden. Der Installer entfernt keine fremden Dienste.

Die Optionen sind idempotent. Bei fehlgeschlagenem Dienststart stellt der Installer neben der bisherigen Programmversion und systemd-Datei auch seine explizite Listeneränderung zurück. Bei erfolgreicher Installation bleibt die neue Einstellung dauerhaft gespeichert; ein späterer manueller Programm-Rückwechsel ändert sie nicht.

Änderungen je Version stehen in [CHANGELOG.md](CHANGELOG.md).

## Konfiguration

Die Alarmmatrix wird normalerweise im Dashboard verwaltet. Die folgenden Dateibefehle dienen der Webserver-Konfiguration und der bisherigen Alarm-Startdatei vor dem ersten Dashboard-Speichern.

```bash
sudo nano /etc/knx-alarmserver/config.toml
sudo nano /etc/knx-alarmserver/alarms.csv
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver check
sudo systemctl restart knx-alarmserver
```

### KNX-Verbindungen im Dashboard

1. Als Admin anmelden, oben rechts das Zahnrad öffnen und **KNX Verbindungen** wählen.
2. **Verbindung hinzufügen** wählen und einen eindeutigen Namen angeben.
3. Für **Tunneling (UDP)** die tatsächliche Router-IPv4-Adresse und den Port (gewöhnlich 3671) eintragen. Die lokale IPv4-Adresse ist bei mehreren Netzwerkschnittstellen optional anzugeben.
4. Für **Routing (Multicast)** eine in ETS abgestimmte freie physikalische Adresse sowie die Multicast-Adresse eintragen. Routing benötigt passende Netzwerkeinstellungen.
5. **Verbindung aktiv** und für den Empfang zusätzlich **KNX-Empfang aktivieren** auswählen; **Speichern und übernehmen** anklicken.
6. Oben Verbindungsstatus und letzten Empfang prüfen; unter **Telegramme** den tatsächlichen Verkehr kontrollieren.

Einträge lassen sich bearbeiten, einzeln deaktivieren oder nach Bestätigung löschen. **Aktivierung speichern** übernimmt den globalen Empfangsschalter. **Neu laden** verwirft ungespeicherte Formulareingaben und lädt die aktuelle Konfiguration. Bei gleichzeitiger Bearbeitung wird eine veraltete Version mit einem Hinweis abgewiesen; dann neu laden und die Änderung erneut vornehmen.

Verbindungsänderungen werden ohne Webserver-Neustart übernommen. Dafür werden die bisherigen KNX-Verbindungen geschlossen und neu aufgebaut; während dieser kurzen Unterbrechung können Telegramme fehlen. Speichern bestätigt die Konfiguration, nicht die Erreichbarkeit des Routers. Verbindungsfehler erscheinen im Status und Protokoll.

Die anfänglichen KNX-Einstellungen stammen aus `config.toml`. Ab dem ersten Speichern im Dashboard hat der in SQLite gespeicherte KNX-Abschnitt Vorrang, auch nach Neustarts und Updates. Webserver-Einstellungen bleiben dateibasiert. Die Alarmmatrix wird nach dem ersten Speichern ebenfalls aus SQLite geladen. Ein SQLite-Backup enthält somit auch die Dashboard-Verbindungen. Nur Admins können KNX-Verbindungen und ETS-Import verwalten.

Neuinstallationen enthalten keine vorgegebenen Router-Verbindungen. Bei Updates bleibt die bestehende Konfiguration erhalten. Ein vorhandener Beispielrouter mit `192.0.2.30` muss im Dashboard bearbeitet oder gelöscht werden; diese Dokumentationsadresse ist kein realer Router.

Die manuelle Alternative steht in [config/config.example.toml](config/config.example.toml). Private Gebäudeadressen, echte Alarmmatrizen, Passwörter und KNX-Schlüssel gehören nicht ins öffentliche Repository. KNX IP Secure und Data Secure bleiben noch nicht unterstützt.

### ETS-Gruppenadressen im Dashboard importieren

In ETS im Gruppenadressen-Fenster den gewünschten Baum auswählen, rechts anklicken und **Gruppenadressen exportieren** wählen. Für Namen, Beschreibungen und DPT vorzugsweise das aktuelle **XML-Format** verwenden; das alte ETS4-kompatible XML enthält keine DPT-Angaben. Siehe [KNX-Exportdokumentation](https://support.knx.org/hc/en-us/articles/360022237580-Group-Address-Export).

1. Als Admin im Zahnradmenü **ETS-Import** öffnen und `.xml` oder `.csv` auswählen (maximal 4 MiB / 10000 Adressen je Datei).
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

### Prioritäten festlegen

Admins öffnen **Zahnrad → Prioritäten** (`/priorities`). Die Tabelle enthält zunächst **1 Brand, 2 Warnung, 3 Service, 4 Info**. Nummern von 1 bis 999 sind möglich; je kleiner die Zahl, desto höher die Priorität. Bezeichnungen frei ändern, neue Nummern ergänzen oder ungenutzte Nummern entfernen. Mindestens ein Eintrag muss bleiben. Vor dem Entfernen oder Ändern einer verwendeten Nummer die betroffenen Alarme umstellen.

In der Alarmmatrix wählen Admins und User die Nummer mit der aktuellen Bezeichnung. Alarme und CSVs speichern ausschließlich die Nummer. Eine Umbenennung wirkt nach der nächsten Dashboard-Aktualisierung, ohne die Zuordnung, den Alarmzustand oder die Historie zu ändern. Meldungen desselben Status werden nach Prioritätsnummer sortiert. Die Beispieldatei verwendet eine aktuell konfigurierte Nummer.

Alte Werte werden kompatibel gelesen: `critical` → `1`, `warning` → `2`, `info` → `4`. Diese Umstellung bewahrt die bisherige Rangfolge; bereits vorhandene Zuordnungen nach inhaltlicher Bedeutung prüfen, insbesondere wenn „critical“ früher auch für technische Meldungen verwendet wurde. Neue Exporte enthalten Zahlen.

### Alarmmatrix und Datentypen

Admins und User öffnen über das Zahnrad **Alarmmatrix** (`/matrix`). Über **Werkzeuge anzeigen** Hinzufügen, Speichern und CSV-Funktionen einblenden. Die Suche und die rechts angeordnete Alarmanzahl bleiben immer sichtbar. Zeilen hinzufügen, alle Felder direkt in der Tabelle bearbeiten und **Matrix speichern** wählen. Interne IDs werden ausschließlich vom Server automatisch vergeben; vorhandene IDs bleiben bei Bearbeitungen erhalten. Entfernen wird beim Speichern wirksam. Suche und Seiten mit jeweils 100 Zeilen erleichtern große Matrizen; gespeichert wird immer die gesamte Matrix. Die Oberfläche warnt vor ungespeicherten Änderungen.

**Beispiel-CSV herunterladen** liefert eine direkt importierbare Vorlage. **Gespeicherte Matrix als CSV** exportiert den aktuellen gespeicherten Stand. **CSV ergänzen** importiert zusätzliche Alarme mit neuen IDs. Vorhandene Gruppenadressen werden nicht überschrieben; doppelte Adressen oder ungültige Zeilen lehnen den gesamten Import ab. Erst manuelle Änderungen speichern oder verwerfen. Maximal 5000 Alarme und 2 MiB je Import. Eine parallel gespeicherte Änderung wird erkannt und muss vor dem erneuten Speichern geladen werden.

CSV für Dashboard-Import und Export: semikolongetrenntes UTF-8 mit Kopfzeile **ohne ID**. Text mit Semikolon oder Anführungszeichen korrekt als CSV quotieren:


```csv
name;group_address;dpt;operator;threshold;hysteresis;field;area;priority
Pumpenstörung;1/2/3;1.005;eq;true;0;;Technik;2
Übertemperatur;1/2/4;9.001;gt;50;2;;Technik;2
Statustext;1/2/5;16.001;contains;Störung;0;;Technik;2
```

Diese Gruppenadressen sind ausschließlich Beispiele und dürfen nicht ungeprüft übernommen werden. Weitere Beispiele ohne ID: [config/alarmmatrix.example.csv](config/alarmmatrix.example.csv). Bestehende Installationen lesen vor dem ersten Dashboard-Speichern weiterhin die bisherige `alarms.csv` mit ID-Spalte; vorhandene IDs, Zustände und Historie bleiben erhalten. Danach hat die in SQLite gespeicherte Matrix Vorrang, auch beim CLI-Befehl `check`, nach Neustarts und Updates. Ein SQLite-Backup enthält somit auch die Matrix. Die alte Datei wird nicht überschrieben; Änderungen daran haben nach dem Dashboard-Speichern keine Wirkung mehr. Symcon-Objekt-IDs sind für den direkten KNX-Empfang nicht erforderlich.

| Feld | Bedeutung |
| --- | --- |
| Interne ID | Vom Server fortlaufend vergeben, z. B. `alarm-000001`; schreibgeschützt und nicht in der Dashboard-CSV. Bestehende Alt-IDs bleiben erhalten. |
| `name` | Anzeigename |
| `group_address` | KNX-Gruppenadresse, dreistufig |
| `dpt` | Exakter DPT, z. B. `9.001`, `16.001`, `20.102`; Hauptnummern sind möglich, wenn xknx dafür einen Basistyp bereitstellt |
| `operator` | `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `between`, `outside`, `contains`, `in`, `monitor` |
| `threshold` | JSON-Wert oder Klartext; z. B. `true`, `50`, `[20,80]`, `[1,4]` oder `Störung` |
| `hysteresis` | Nichtnegative Zahl in derselben Einheit wie der dekodierte Messwert; sonst `0` |
| `field` | Optionaler Feldpfad für strukturierte DPT, z. B. `control`, `hour` oder `items.0`; richtet sich nach der xknx-Dekodierung |
| `area` | Bereich/Ort |
| `priority` | Ganze Prioritätsnummer aus der konfigurierten Tabelle, z. B. `1`, `2`, `3`, `4`; kleinere Zahl = höhere Priorität. Die Bezeichnung wird nicht in der CSV gespeichert. |

JSON-Zahlen werden als Zahlen, `true`/`false` als Boolean behandelt. Text, der wie JSON aussieht (etwa der Text `123`), als JSON-String und mit korrekter CSV-Quotierung speichern; Excel/CSV-Schreibprogramme übernehmen diese Quotierung. Textsuche ist groß-/kleinschreibungsabhängig. `eq` vergleicht dekodierte Werte; bei Fließkommazahlen sind Grenzwertregeln meist geeigneter.

Aufzählungen werden für Regeln auf ihren numerischen KNX-Wert normalisiert; die Anzeige ergänzt den Namen, soweit xknx ihn bereitstellt. Komplexe Werte werden als JSON angezeigt und über `field` ausgewertet. Datum/Zeit sind strukturierte Werte oder ISO-Text entsprechend dem Decoder. Für komplizierte DPT zunächst `monitor` verwenden und die tatsächlich dekodierten Feldnamen prüfen. Nicht vorhandene Felder oder ein falscher Werttyp werden als DPT-/Regelfehler angezeigt.

Beispiel Hysterese: `gt;50;2` aktiviert bei **> 50** und bleibt aktiv, solange der Wert **> 48** ist. Bei **≤ 48** geht der Alarm. `ge` schließt den Grenzwert ein. Bei `outside;[20,80];3` aktiviert ein Wert **< 20** oder **> 80** und geht nach Rückkehr in **[23,77]**. Hysterese muss bei Bereichsregeln kleiner als die halbe Bereichsbreite sein.

Verfügbare DPT auflisten:

```bash
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver dpt-list
```

Es ist in dieser Version ein Datenpunkt je Gruppenadresse vorgesehen. Für mehrere Regeln auf derselben Adresse ist später eine Trennung von Datenpunkt- und Regelkonfiguration nötig. Bei Änderungen von Gruppenadresse, DPT oder Regel im Dashboard wird nur der betroffene aktuelle Zustand zurückgesetzt, bis ein neues Telegramm eintrifft. Name, Bereich und Priorität können ohne Zustandsverlust geändert werden. Änderungen und Entfernen werden mit Benutzer und Zeit in der Historie protokolliert; bestehende Ereignisse bleiben erhalten.

## Gemeinsame Meldungsliste: ein Vorgang je Auftreten

Die Oberfläche führt aktuelle und abgeschlossene Alarmvorgänge in **einer Tabelle**. Jede Zeile gehört zu einem konkreten Auftreten und erhält eine automatische Vorgangsnummer. Die Alarmdefinition in der Matrix behält ihre eigene ID. Ein erneutes Kommen nach dem Gehen erzeugt einen neuen Vorgang, auch wenn der vorherige noch unquittiert ist.

Spalten: **Priorität · # · Meldung/Bereich · Zustand · Gekommen · Quittiert · Gegangen · Aktion**. Die Quittierung enthält Datum/Uhrzeit und den vollständigen Namen. Bereich, GA und DPT stehen gemeinsam unter dem Meldungstext; die Vorgangsnummer steht in der schmalen Spalte **#**. Nummern mit mehr als vier Ziffern werden platzsparend gekürzt und im Tooltip vollständig angezeigt. Wiederholte Telegramme oder Leseantworten mit gleicher Alarmbedingung verändern keinen dieser drei Zeitpunkte. Quittieren ist eine Kenntnisnahme und verändert nicht den KNX-Wert. Es ist vor oder nach dem Gehen möglich und gilt ausschließlich für die ausgewählte Vorgangsnummer. Ein älterer Vorgang lässt sich unabhängig vom neueren Auftreten derselben Störung quittieren.

Die fünf Statuszähler wählen direkt Aktiv/offen, Aktiv/quittiert, Gegangen/offen, Abgeschlossen oder Unbekannt; ein erneuter Klick kehrt zur Standardansicht zurück (aktiv ODER unquittiert). Rechts neben „Meldungen“ steht der ausgewählte Filter, im Standard „Aktiv“. Unbekannt zeigt separat konfigurierte Punkte ohne bekannten Zustand; diese sind noch keine Alarmvorgänge. Die Zähler beziehen sich auf alle gespeicherten Vorgänge, unabhängig vom Zeitraum. Dadurch können mehrere gegangene offene Vorgänge derselben Alarmdefinition gezählt werden.

Die Tabelle scrollt innerhalb der Seite, mit sichtbaren Spaltenüberschriften. Offene Vorgänge werden vollständig angezeigt. **Abgeschlossen** zeigt höchstens die neuesten 500 passenden Vorgänge; der Datumsfilter durchsucht den gesamten gespeicherten Bestand vor der Begrenzung. Die Anzeige sortiert nach Priorität (1 zuerst), dann nach Gekommen absteigend. **Zeitraum auswählen** öffnet einen gemeinsamen Kalender: Beginn und Ende durch zwei Klicks auswählen und **Übernehmen** wählen. Auch ein einzelner Tag oder ein Zeitraum über Monats-/Jahresgrenzen ist möglich. Der Filter bezieht sich auf Gekommen und lokale Kalendertage, einschließlich des gesamten Endtags. Fehlende Gekommen-Zeitpunkte werden bei Datumsfilter nicht berücksichtigt. **Zeitraum zurücksetzen** entfernt nur die zeitliche Eingrenzung; der gewählte Status bleibt erhalten. Die Datumsauswahl funktioniert auch mit Tastatur (Pfeile, Bild auf/ab, Enter; Escape zum Abbrechen). Die Telegrammseite behält ihr sichtbares Suchfeld.

### Übernahme bestehender Daten

Beim ersten Start wird die bestehende SQLite-Datenbank automatisch ergänzt. Vor der Übernahme einer gefüllten Datenbank erstellt der Server eine konsistente lokale Sicherung neben der Datenbank: `alarmserver.sqlite3.before-occurrences-<Nummer>.sqlite3`, nur für den Dienstbenutzer lesbar. Scheitert diese Sicherung, wird die Migration nicht begonnen. Schemaänderung, Übernahme und Abschlussmarkierung erfolgen transaktional; ein Abbruch ist wiederholbar.

Gespeicherte aktuelle Zustände, IDs, Werte, Empfangs-/Wechselzeiten, Quittierende, Benutzer, Sitzungen, Matrix, Prioritäten, KNX-Konfiguration und Ereignisse bleiben erhalten. Erhaltene Kommen-/Gehen-/Quittierungsereignisse werden zu Vorgängen zusammengeführt. Der gespeicherte aktuelle Zustand hat bei der Zuordnung Vorrang. Bereits früher gelöschte Ereignisse lassen sich nicht rekonstruieren: Fehlende Zeiten bleiben leer, unvollständige Verläufe werden gekennzeichnet. Historische Namen stammen soweit vorhanden aus den Ereignissen; Bereich, GA, DPT und Priorität alter Vorgänge werden soweit möglich aus der aktuellen Matrix übernommen. Neue Vorgänge speichern diese Angaben beim Auftreten.

Änderung von Adresse/DPT/Regel oder Entfernen eines Alarms beendet die bisherige Auswertung mit einer ausdrücklichen Kennzeichnung. Dafür wird **kein fiktiver Gegangen-Zeitpunkt** erzeugt. Nicht quittierte alte Vorgänge bleiben bearbeitbar. Die Aufbewahrungsdauer (`retention_days`, standardmäßig 365 Tage) entfernt ausschließlich abgeschlossene Vorgänge, deren Ende und Quittierung lange genug zurückliegen. Aktive oder unquittierte Vorgänge bleiben erhalten. Das technische Ereignisprotokoll bleibt zusätzlich gespeichert und über `/api/history` erreichbar, erscheint aber nicht mehr als separate Bedienliste. Der Telegrammmonitor behält seinen bisherigen Ringpuffer.

## Mailversand bei neuen Störungen

Admins öffnen **Verwaltung → Mail-Konfiguration** (`/mail`). Unterstützt werden SMTP über STARTTLS (typisch 587), direktes TLS (typisch 465) und ein unverschlüsselter lokaler Relay. Server, Port, optionale SMTP-Anmeldung, Absenderadresse/-name und Serverbezeichnung eintragen. Die optionale Dashboard-Adresse steht als Platzhalter zur Verfügung. Es sind keine zusätzlichen Python-Pakete erforderlich.

Über den **Info-Button „i“** neben „Mail-Konfiguration“ öffnet sich eine Hilfe mit zehn Anbieterbeispielen. Die Auswahl zeigt exakt die Feldnamen des Alarmservers und offizielle Quellen (Prüfstand 22.10.2026). Öffnen/Schließen verändert keine Konfiguration und löst keinen Versand aus. SMTP-Benutzer und Absender sind durch die eigene zum Postfach gehörende Adresse zu ersetzen.

| Anbieter | SMTP-Beispiel | Port / Auswahl im Alarmserver | Anmeldung / Besonderheit |
| --- | --- | --- | --- |
| [Zoho Mail](https://www.zoho.com/de/mail/help/zoho-smtp.html) | smtp.zoho.com (US-Privatkonto) | 465 / TLS | Eigene Serverdetails nach Kontotyp/Rechenzentrum verwenden; App-Passwort bei 2FA |
| [1&1 Hosting / IONOS](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/) | smtp.ionos.de | 465 / TLS | Vollständige Postfachadresse und Postfachpasswort; andere 1&1-Produkte können abweichen |
| [GMX Deutschland](https://hilfe.gmx.net/pop-imap/imap/imap-serverdaten.html) | mail.gmx.net | 587 / STARTTLS | Vollständige Adresse und App-Passwort |
| [Gmail](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app?hl=de) | smtp.gmail.com | 587 / STARTTLS | Vollständige Adresse und verfügbares Google-App-Passwort; 2FA erforderlich |
| [WEB.DE](https://hilfe.web.de/pop-imap/imap/imap-serverdaten.html) | smtp.web.de | 587 / STARTTLS | Vollständige Adresse und App-Passwort |
| [Telekom / T-Online](https://www.telekom.de/hilfe/apps-dienste/e-mail/posteingang-postausgang-server) | securesmtp.t-online.de | 465 / TLS | Vollständige Adresse und separates Passwort für E-Mail-Programme |
| [STRATO](https://www.strato.de/faq/mail/e-mailserver-adressen-ports-ssl-tls/) | smtp.strato.de | 465 / TLS | Vollständige Postfachadresse und Postfachpasswort |
| [Yahoo Mail](https://help.yahoo.com/kb/new-yahoo-mail/imap-server-settings-yahoo-mail-sln4075.html) | smtp.mail.yahoo.com | 465 / TLS | Vollständige Adresse und Yahoo-App-Passwort |
| [mailbox.org](https://kb.mailbox.org/en/business/e-mail/e-mail-configuration/) | smtp.mailbox.org | 465 / TLS | Haupt-E-Mail-Adresse und Postfachpasswort bzw. Mail-App-Passwort mit SMTP-Berechtigung |
| [iCloud Mail](https://support.apple.com/de-li/102525) | smtp.mail.me.com | 587 / STARTTLS | Vollständige iCloud-Adresse und App-spezifisches Passwort |

Die Beispiele ersetzen keine kontospezifische Freigabe. Das Modul unterstützt aktuell SMTP mit Benutzername/Passwort, einschließlich nutzbarer App-Passwörter, aber keine OAuth2-Anmeldung. Ein Konto, dessen Richtlinien App-Passwörter ausschließen und OAuth2 erzwingen, lässt sich nicht durch Eingeben eines normalen Kennworts anbinden.

1. SMTP-Konfiguration und Vorlagen speichern. Ein leeres Passwortfeld erhält das gespeicherte SMTP-Passwort; „Gespeichertes SMTP-Passwort entfernen“ löscht es. Das Passwort wird nie zurück an den Browser übertragen. Es liegt im Klartext in der lokalen SQLite-Datenbank, die einschließlich ihrer Backups entsprechend geschützt werden muss; der Dienst verwendet `UMask=0077`.
2. Über **Testmail senden** eine Nachricht mit der gespeicherten Konfiguration prüfen. Das funktioniert auch bei ausgeschaltetem automatischem Versand. Die Testmail wird ausschließlich durch den Admin-Klick ausgelöst. Eine Annahme durch SMTP ist noch keine Bestätigung des Eingangs im Postfach.
3. In **Benutzerverwaltung → Bearbeiten** bei den gewünschten Empfängern **Mails bei neuen Störungen erhalten** aktivieren. Empfängeradresse ist die E-Mail-Adresse des Kontos. Neue und bestehende Konten sind zunächst nicht für Mail aktiviert; auch Viewer können Empfänger sein. Nur Admins ändern diese Einstellung.
4. Automatischen Mailversand aktivieren und speichern. Ab diesem Zeitpunkt entsteht je neuem Alarmvorgang und aktiviertem Empfänger ein eigener Versandauftrag. Wiederholte Telegramme/Leseantworten, Quittierung, Gehen und Neustart erzeugen keine neue Benachrichtigung. Bereits vorhandene Vorgänge werden nicht nachversendet; erneut gegangen/aktiv gewordene Alarme erhalten eine neue Vorgangsnummer und damit einen neuen Auftrag.

Je Priorität lassen sich **Betreff und Text** frei bearbeiten. Fehlende Vorlagen neuer Prioritäten erhalten die Standardvorlage. Beispiel-Betreff: `[{prioritaetsname}] {meldung} · Vorgang #{vorgangsnummer}`. Verfügbare Platzhalter zeigt die Oberfläche; wörtliche Klammern mit `{{` und `}}` schreiben. Es werden reine Textmails gesendet.

| Bereich | Platzhalter |
| --- | --- |
| Meldung | `{vorgangsnummer}`, `{alarm_id}`, `{meldung}`, `{bereich}`, `{status}` |
| Priorität/KNX | `{prioritaet}`, `{prioritaetsname}`, `{gruppenadresse}`, `{dpt}`, `{quelle}` |
| Zeit/Wert/Regel | `{gekommen}`, `{gekommen_iso}`, `{wert}`, `{einheit}`, `{operator}`, `{schwellwert}`, `{hysterese}`, `{feld}` |
| Server | `{server_name}`, `{server_url}` |
| Empfänger | `{empfaenger_vorname}`, `{empfaenger_nachname}`, `{empfaenger_name}`, `{empfaenger_email}` |

`{gekommen}` verwendet die Zeitzone des Raspberry; `{gekommen_iso}` enthält den ursprünglichen ISO-Zeitpunkt mit Zeitzone. Daten, Empfänger und gerenderter Text werden bei Entstehen des Vorgangs festgehalten. Nachrichten gehen einzeln an jeden Empfänger. Benutzer, die vor dem tatsächlichen Versand deaktiviert oder gelöscht wurden, erhalten ausstehende Nachrichten nicht mehr. Globales Deaktivieren pausiert die Warteschlange.

Der Hintergrundversand hält während der SMTP-Verbindung keine Datenbanksperre. Versandaufträge überleben Neustarts. Nach Fehlern wird bis zu fünfmal versucht (Wartezeiten 30 Sekunden, 2, 8 und 32 Minuten). Danach steht der Auftrag unter **Fehlgeschlagen**; nach Korrektur der Serverdaten **Fehlgeschlagene erneut versuchen** wählen. Die Übersicht zeigt Statussummen und die letzten 20 Aufträge; erfolgreiche/abgebrochene Aufträge unterliegen der konfigurierten Aufbewahrungsdauer. Das SMTP-Passwort und rohe SMTP-Fehlerantworten werden nicht in dieser Übersicht ausgegeben.

SMTP bietet keine transaktionale Zustellbestätigung: Wird eine Nachricht angenommen und der Prozess vor dem Speichern dieses Ergebnisses unterbrochen, kann beim Wiederholen eine doppelte Mail entstehen. Eine stabile Message-ID bleibt bei Wiederholungen erhalten. Dies gilt auch nach einer Zeitüberschreitung mit unklarem Serverergebnis; die Warteschlange verhindert dagegen doppelte Aufträge durch wiederholte KNX-Telegramme.

## KNX-Status manuell abfragen

Admins können in **Telegramme → Status abfragen** die unbekannten Werte oder alle Gruppenadressen der Alarmmatrix lesen. Bei mehreren Verbindungen die passende Linie wählen; ohne Auswahl wird die erste aktive Verbindung verwendet. Nicht die gesamte ETS-Adressliste wird abgefragt. Die Abfrage läuft unabhängig von der ausgewählten Meldungsseite und ihren Filtern im Hintergrund mit höchstens zwei Leseanfragen pro Sekunde. Fortschritt nennt gesendete Anfragen und gültige Antworten; das Senden einer Anfrage allein ist kein bestätigter Messwert. Gleichzeitige Abfragen werden abgewiesen. Dienstende oder KNX-Konfigurationswechsel beendet eine laufende Abfrage.

Es werden ausschließlich **GroupValueRead**-Telegramme gesendet, keine Werte geschrieben und keine Alarmquittierungen oder Reset-Befehle ausgeführt. Ein Gerät muss das Lesen seines Kommunikationsobjekts erlauben (Lesen-/Read-Flag); Filtertabellen und sendende Gruppenadresse müssen passen. Ohne gültige Antwort bleibt der bisherige Zustand erhalten. Empfangene Antworten durchlaufen dieselbe Dekodierung und Alarmregel wie normale Telegramme und können damit auch echte Alarme auslösen.

In ETS: **Diagnose → Gruppenmonitor → Start → Gruppenfunktionen**, gewünschte Gruppenadresse wählen und **Lesen** drücken. Alternativ Gruppenadresse markieren und im Kontextmenü den Wert lesen. Die Flags werden am Kommunikationsobjekt des antwortenden Geräts parametriert und anschließend auf das Gerät geladen. Ein Geräte-Neustart ist dafür kein geeigneter pauschaler Statusabruf.

Dokumentation: [KNX Gruppenmonitor lesen](https://support.knx.org/hc/en-us/articles/360019107679-Extended-options-Group-Monitor), [Gruppenadressen lesen](https://support.knx.org/hc/en-us/articles/360009510539-Group-Address-Read-Write-Display).

## Zustände und Quittierung

Ein kommender Alarm wird unquittiert gespeichert. Quittieren setzt den lokalen Quittierungsstatus, nicht den KNX-Wert. Geht eine unquittierte Störung, bleibt sie als „Gegangen · unquittiert“ stehen. Ein erneutes Kommen erzeugt einen eigenen Vorgang mit neuer Quittierung; ältere Vorgänge bleiben unverändert. Wiederholte identische Telegramme aktualisieren den Empfangszeitpunkt ohne neue Alarmereignisse.

Gespeicherte Zustände bleiben nach einem Neustart erhalten und werden nicht als alte Werte klassifiziert. Vor dem ersten Empfang heißt der Zustand „Unbekannt“. Ungültige Nutzdaten setzen einen sichtbaren DPT-/Regelfehler und behalten den letzten gültigen Alarmzustand. `Normal` bedeutet zuletzt empfangener Normalwert, nicht zyklisch geprüfte Erreichbarkeit. Eine manuelle Statusabfrage steht auf der Telegrammseite bereit. Zyklische Statusüberwachung, automatische Initialabfragen, Entprellung und Verzögerungen sind noch nicht enthalten. Zustandswechsel während eines Ausfalls können durch den rein passiven Empfänger nicht rekonstruiert werden.

## Betrieb und Sicherung

```bash
systemctl status knx-alarmserver --no-pager
journalctl -u knx-alarmserver -f
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver user-add admin@example.org --first-name Beispiel --last-name Admin
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver backup /var/lib/knx-alarmserver/backups/manuell.sqlite3
```

Bei `user-add` wird ein vorhandenes Benutzerpasswort ersetzt; vorhandene Namen bleiben erhalten. Neue Konten benötigen eine E-Mail-Adresse und Vor-/Nachnamen, die bei fehlenden Optionen interaktiv abgefragt werden. Um ausschließlich Namen eines vorhandenen Kontos nachzutragen, ohne Passwort, Rolle oder Sitzungen zu ändern:

```bash
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver user-profile admin@example.org Beispiel Admin
```

 Kennwörter werden mit PBKDF2 und individuellem Salt gespeichert. Das Backup-Ziel darf noch nicht existieren. Die SQLite-Backup-API berücksichtigt WAL-Daten; eine einzelne aktive `.sqlite3`-Datei nicht einfach kopieren. Zusätzlich `/etc/knx-alarmserver` sichern. Im Betrieb erfolgt keine automatische NAS-Sicherung; ein vorhandenes Backupkonzept muss gesondert angebunden werden.

Ereignisse werden standardmäßig 365 Tage behalten und stündlich bereinigt (`retention_days`). Der Telegrammmonitor enthält nur die letzten 250 Telegramme im RAM. Der aktuelle Wert wird gespeichert, aber es gibt keine vollständige Messwert-Zeitreihe. Update-Sicherungen und alte Programmverzeichnisse werden nicht automatisch entfernt.

`/health/live` bestätigt ausschließlich einen laufenden Webprozess. `/api/ready` benötigt Anmeldung und liefert nur bei aktivierten, bereiten KNX-Verbindungen HTTP 200; sonst 503. Routing-Bereitschaft bezeichnet das lokale Socket, keine nachgewiesene Bus-Erreichbarkeit.

## Updates und Releases

Sobald ein entsprechender geprüfter Versionstag veröffentlicht wurde:

```bash
sudo bash /opt/knx-alarmserver/current/source/scripts/update.sh v0.14.2
```

Der Befehl installiert genau diesen Tag, prüft die Paketversion und erhält die lokale Konfiguration. Das ist ein über GitHub verwaltetes **Python-Paket mit systemd-Installer**, noch kein Debian-APT-Repository und kein `.deb`-Paket. Python-Abhängigkeiten werden von PyPI geladen; Internetzugang ist erforderlich. Direkte Abhängigkeiten sind fest versioniert, transitive Abhängigkeiten sind noch nicht vollständig mit Hashes gesperrt.

Vor einem Update wird eine konsistente SQLite-Sicherung angelegt. Schlägt der anschließende Webstart fehl, wird die vorige Programmversion aktiviert. Die Datenbank wird dabei nicht automatisch zurückgesetzt. Bei künftigen Schemaänderungen müssen Rückwärtskompatibilität und Rücksicherung explizit geprüft werden. Ein erfolgreicher Webstart beweist noch keine KNX-Verbindung.

Entwickler veröffentlichen nach erfolgreichen Tests einen Tag, dessen Name der Paketversion entspricht:

```bash
git tag v0.14.2
git push origin v0.14.2
```

Der Release-Workflow testet erneut, baut Wheel und Source-Paket und veröffentlicht ein GitHub-Vorab-Release mit SHA256-Prüfsummen. Er installiert nichts auf dem Raspberry. Release-Tags werden nicht vom Alarmserver automatisch erzeugt oder verändert. Der erste echte KNX-/Pi-Test ist vor produktiver Freigabe erforderlich.

## Dashboard und eigene Verwaltungsseiten

Die Hauptseite zeigt Zähler, Meldungen und Historie. Die Kopfzeile bleibt auf allen Seiten beim Scrollen sichtbar; die Versionsnummer befindet sich ebenfalls dort. Der bisherige Fußtext entfällt. Auf schmalen Bildschirmen nutzt die Leiste zwei Zeilen, und Menüs öffnen darunter innerhalb des sichtbaren Bereichs. Der bisherige KNX-Informationskasten und die Verwaltungsreiter entfallen. Oben rechts stehen:

- **KNX-Symbol:** grün, wenn alle aktiven Verbindungen bereit sind; rot bei Verbindungs- oder Speicherfehlern; gelb bei deaktiviertem bzw. noch nicht konfiguriertem Empfang. Beim Aufklappen erscheinen Einzelzustände und letzter Empfang. Ohne aktuelle Serverantwort wird der Status rot als unbekannt markiert.
- **Zahnrad:** Admins und User können die Alarmmatrix (`/matrix`) verwalten. Die folgenden weiteren Funktionen sind ausschließlich für Admins sichtbar: Telegramme (`/telegrams`), KNX Verbindungen (`/knx`), ETS-Import (`/ets`), Prioritäten (`/priorities`), Benutzerverwaltung (`/users`). Jede Funktion hat eine eigene URL mit direkter serverseitiger Rechteprüfung.
- **Benutzersymbol mit Rang:** Aufklappen zeigt den Benutzernamen, Kennwort ändern (`/account/password`) und Abmelden. Alle Rollen können ausschließlich ihr eigenes Kennwort mit Prüfung des bisherigen Kennworts ändern. Danach erneut anmelden; sämtliche bisherigen Sitzungen dieses Kontos werden beendet.

Im **Benutzermenü → Darstellung** können alle Rollen **Dark**, **Light** oder **Automatisch** wählen. Dark erhält das bisherige Farbdesign und ist die Voreinstellung. Automatisch folgt der Hell-/Dunkel-Einstellung des Betriebssystems, auch bei Änderungen während der Nutzung. Die Auswahl gilt auf allen Seiten einschließlich Anmeldung und wird im jeweiligen Browser für diese Serveradresse gespeichert; andere geöffnete Tabs übernehmen sie ebenfalls. Bei gesperrtem Browserspeicher bleibt der Wechsel für die laufende Seite möglich.

Menüs lassen sich per Maus, Tastatur und Touch bedienen, außerhalb anklicken oder mit Escape schließen. Ein Link führt von jeder Unterseite zum Dashboard zurück.

## Versionsanzeige und Update über das Dashboard

Die Versionsnummer in der feststehenden Kopfzeile öffnet `/versions` mit der Versionshistorie. Beim Öffnen wird unabhängig von den Alarmabfragen die Version auf GitHub geprüft. Nur wenn eine numerisch neuere Version bestätigt ist, erscheint die Nummer rot; der Tooltip nennt die neue Version. Eine nicht mögliche Prüfung bleibt ohne Fehlermeldung und ohne rote Markierung. Der Server puffert erfolgreiche Prüfungen fünf Minuten, erfolglose für 30 Sekunden. Beim Öffnen einer Seite und bei **Status prüfen** werden diese Puffer ausdrücklich umgangen. Der Abruf verwendet die GitHub-API mit Cache-Unterdrückung und bei deren Ausfall einen zweiten Abrufweg über raw.githubusercontent.com. Fehlerursachen stehen im Dienstprotokoll, automatische Prüfungen bleiben in der Oberfläche still. Die Prüfung sendet keine Gebäudedaten oder Zugangsdaten an GitHub.

Die Historie ist für alle angemeldeten Rollen lesbar. Sie wird als sicherer Text mit Versionsüberschriften und Listen dargestellt; bei fehlendem GitHub-Zugriff dient die lokal installierte CHANGELOG.md als Rückfall. Der Kasten **Alarmserver aktualisieren** erscheint nur für Admins mit einer bestätigten neueren Version. **Status prüfen** steht neben der Versionsinfo außerhalb des Kastens und ist für alle angemeldeten Rollen erreichbar. Ein Klick zeigt sofort den laufenden Abruf, sperrt den Button bis zum Abschluss und meldet danach das Ergebnis samt Prüfzeitpunkt. Bei einer fehlgeschlagenen manuellen Prüfung erscheint eine Rückmeldung; die automatische Prüfung bleibt still. Update-Fortschritt und Ergebnis werden außerhalb des Kastens angezeigt, damit sie auch nach erfolgreicher Installation sichtbar bleiben. Der Update-Button ist ausschließlich bei einer bestätigten neueren Version, verfügbarem Update-Dienst und ohne laufendes Update aktiv. Vor dem Start prüft der Server die Version erneut ohne Verwendung des Zwischenspeichers; ist keine neuere Version bestätigt, wird kein Update angefordert. Auch der Update-Helfer überspringt gleiche oder ältere Versionen. Ein direkter Update-API-Aufruf durch User oder Viewer wird weiterhin abgewiesen.

Einmalig diese Version per PuTTY mit `git pull --ff-only` und `sudo bash scripts/install.sh` installieren. Dadurch werden neben dem Webdienst auch ein root-eigener Update-Helfer und `knx-alarmserver-update.path` eingerichtet. Danach als Admin über **Versionsnummer → Versionshistorie → Update installieren** starten.

Das Dashboard zeigt angefordert, Herunterladen, Installation und anschließend Erfolg oder Fehler an. Nach einer Verbindungsunterbrechung beim Dienstneustart wird der Status erneut abgefragt. Bei Erfolg lässt sich die Oberfläche neu laden. Der Update-Status bleibt unabhängig vom Webprozess bestehen; es läuft höchstens eine Dashboard-Anforderung gleichzeitig.

Installiert wird ausdrücklich der aktuelle Stand von **main** aus `https://github.com/jotebu/KNX-Alarmserver.git`, kein Release-Tag und keine vom Browser gewählte Quelle. Vor dem Klick erscheint ein Hinweis auf den kurzzeitigen Ausfall von Oberfläche und KNX-Empfang. Vorhandene Konten, Kennwörter, Rollen, Host/Port, KNX-Verbindungen, ETS-Katalog und Alarmdaten bleiben erhalten. Der vorhandene Installer erstellt vor dem Update eine konsistente SQLite-Sicherung und aktiviert bei einem erkannten Startfehler wieder die bisherige Programmversion.

Der Webprozess bleibt ohne root-Rechte und ohne sudo-Berechtigung. Er darf nur eine leere Anforderungsdatei in seinem Datenverzeichnis erstellen. Ein separater systemd-Dienst mit fest installiertem, root-eigenem Python-Helfer liest keine Anforderungsparameter, lädt ausschließlich das feste Repository und ruft den Installer auf. Statusdateien werden atomar in einem root-eigenen Laufzeitverzeichnis geschrieben. Es werden keine GitHub-Zugangsdaten benötigt oder gespeichert. Fehlerdetails auf dem Raspberry prüfen:

```bash
sudo journalctl -u knx-alarmserver-update -n 100 --no-pager
systemctl status knx-alarmserver-update.path --no-pager
```

Die Update-Funktion ist nur mit dem über den Installer eingerichteten systemd-Dienst verfügbar. Installationen in anderen Umgebungen melden den fehlenden Helfer und bieten keinen aktiven Update-Button an. Bei einem Update aus dem Dashboard wird der lokale Checkout `~/KNX-Alarmserver` nicht verändert; installiert wird eine neue Kopie des Repositorys. Für spätere manuelle Installationen diesen Checkout zuerst mit `git pull --ff-only` aktualisieren.

## Anmeldung und Benutzerverwaltung

| Rolle | Meldungen / Historie sehen | Quittieren | Alarmmatrix verwalten | KNX / ETS / Benutzer verwalten |
|---|---|---|---|---|
| Admin | Ja | Ja | Ja | Ja |
| User | Ja | Ja | Ja | Nein |
| Viewer | Ja | Nein | Nein | Nein |

Nach dem Update im Browser die Serveradresse öffnen und mit dem bisherigen Konto anmelden. Bestehende Konten erhalten bei der Migration die Rolle **Admin**, ihre Kennwörter bleiben gültig. Neue Konten legt ein Admin im Zahnradmenü unter **Benutzerverwaltung** an; die vorausgewählte Rolle ist Viewer. Dort können Admins auch Rollen ändern, Kennwörter setzen und Konten löschen. Für neue Konten sind eine gültige E-Mail-Adresse als Benutzername sowie Vor- und Nachname erforderlich. Der Benutzername bleibt beim Bearbeiten unverändert; Namen können bearbeitet werden. Bestehende Logins werden bei Updates nicht umbenannt. Quittierungen speichern den vollständigen Namen zusätzlich zur internen Benutzerkennung; spätere Namensänderungen oder das Löschen des Kontos verändern diesen historischen Namen nicht. Bisherige Quittierungen ohne Namen werden beim erstmaligen Ergänzen des Profils zugeordnet. Der letzte Admin kann nicht gelöscht oder herabgestuft werden.

Admins und User sehen das Zahnradmenü; User erhalten darin ausschließlich die Alarmmatrix. Viewer sehen weder Verwaltung noch Quittierschaltflächen. Telegramme sind eine Admin-Verwaltungsseite. Der Server verweigert die entsprechenden API-Aufrufe unabhängig vom Dashboard mit HTTP 403. Quittierungen protokollieren weiterhin den angemeldeten Benutzer und Zeitpunkt. Bisherige Quittierungsnamen bleiben auch nach Löschen eines Kontos erhalten.

Eine Browser-Sitzung gilt 12 Stunden und überlebt einen Dienstneustart. Ein zufälliges Sitzungstoken liegt im HttpOnly-Cookie mit SameSite=Strict; in SQLite wird nur sein SHA256-Hash gespeichert. Bei direktem HTTPS setzt der Server zusätzlich Secure. Das Cookie ist nicht an eine IP-Adresse gebunden. Bei den regelmäßigen Dashboard-Abfragen wird die Sitzung geprüft, nicht erneut PBKDF2 berechnet. Passwörter bleiben individuell gesalzen mit PBKDF2-SHA256 und 600.000 Durchläufen gespeichert. Weder Passwörter noch Tokens erscheinen in API-Benutzerlisten. Es gibt keine Standardkennwörter.

Abmelden widerruft die aktuelle Sitzung. Rollen- und Passwortänderungen sowie Kontolöschung widerrufen alle Sitzungen des betroffenen Kontos; anschließend erneut anmelden. API-Werkzeuge können weiterhin explizite HTTP-Basic-Zugangsdaten senden; auch dafür gelten die aktuellen Rollen. Der Browser fordert keine HTTP-Basic-Anmeldung mehr an.

Der frühere Schalter `KNX_ALARMSERVER_DISABLE_AUTH` wird nicht mehr ausgewertet. Auch ein vorhandenes `no-login-test.conf` kann die Anmeldung nicht mehr abschalten. `/test/hallo` entfällt. Die alte Testdatei kann nach dem Update entfernt werden:

```bash
sudo rm -f /etc/systemd/system/knx-alarmserver.service.d/no-login-test.conf
sudo systemctl daemon-reload
```

Falls ein Admin-Kennwort verloren geht, lässt sich über PuTTY ein Admin-Konto anlegen oder wiederherstellen; das Kennwort wird verdeckt abgefragt:

```bash
sudo -u knx-alarmserver /opt/knx-alarmserver/current/venv/bin/knx-alarmserver user-add admin@example.org --role admin
```

Ohne `--role` bleibt bei vorhandenen Konten die Rolle erhalten. Das erste neue CLI-Konto wird Admin, weitere CLI-Konten werden standardmäßig Viewer. Die Datenbank bleibt auch bei Rückkehr zu einer älteren Programmversion um die Rollen- und Sitzungstabellen erweitert; vor Updates erzeugt der Installer ein konsistentes SQLite-Backup.

## Verhalten bei Verbindungsproblemen

Das Dashboard holt Status, Meldungen und die gewählte Ansicht mit einer gemeinsamen Anfrage ab. Die Sitzung wird dafür einmal pro Aktualisierung geprüft; nur beim expliziten Basic-API-Zugriff wird das Passwort erneut berechnet. Leseanfragen einschließlich Antwortinhalt werden nach 10 Sekunden abgebrochen; Versions-/Update-Statusabfragen mit zwei möglichen externen Abrufwegen erhalten 20 Sekunden; Speicheraktionen nach 30 Sekunden. Eine ausbleibende Speicherbestätigung bedeutet nicht zwingend, dass nichts gespeichert wurde: zuerst **Neu laden** und den Stand prüfen, bevor erneut gespeichert wird.

Im Normalbetrieb erfolgt die nächste Aktualisierung fünf Sekunden nach Abschluss der vorherigen. Nach Fehlern steigt die Wartezeit auf 10, 20 und maximal 30 Sekunden; nach erfolgreichem Abruf wieder auf fünf Sekunden. Verdeckte Browser-Tabs pausieren die automatische Abfrage und aktualisieren beim Zurückkehren. Schreibaktionen werden nicht automatisch wiederholt. Angezeigte Daten bleiben bei Fehlern sichtbar und werden als möglicherweise veraltet gekennzeichnet.

`/health/live` verwendet keinen synchronen Worker für Passwortprüfungen. Ein Timeout beim TCP-Verbindungsaufbau ist dadurch jedoch nicht automatisch behoben. Die gemeldeten zeitweisen LAN-Ausfälle konnten im lokalen Lasttest nicht reproduziert werden; die Korrekturen beheben einen nachgewiesenen Hänger der Dashboard-Aktualisierung und reduzieren die Anfragebelastung.

## Entwicklung und Prüfung

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m unittest discover -s tests -v
node --test tests/dashboard_*.cjs
bash -n scripts/install.sh scripts/update.sh
```

GitHub CI prüft Python 3.11 und 3.13, die echten Decoder von xknx, Alarmregeln und die HTTP-API. Ohne installierte Web-/KNX-Abhängigkeiten werden diese Integrationstests lokal als übersprungen angezeigt; reine Konfigurations-, Regel- und Datenbanktests benötigen nur Python. Die CI verlangt ausdrücklich die Bibliotheksimporte. Genau ein Webworker ist vorgesehen; mehrere Worker würden mehrere Busverbindungen erzeugen.

## Nächste Ausbaustufen

1. Routermodell, KNX-Secure-Nutzung, Filtertabellen und tatsächlichen Telegrammempfang prüfen.
2. Echte Alarmmatrix importieren und mit Testalarmen abnehmen.
3. Alarmmatrix anhand realer Telegramme und quittierpflichtiger Testalarme abnehmen.
4. Push, Zeitprogramme, Eskalation und zyklische Erreichbarkeitsüberwachung.
5. Debian-Paket/APT-Verteilung, vollständige Dependency-Lockdatei und weitere Hardwaretests.

