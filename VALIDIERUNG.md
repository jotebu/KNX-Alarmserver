# Prüfstand

Stand: 22.10.2026. Projektversion 0.14.4, Inbetriebnahmeversion.

## Darstellungsschalter in der Kopfzeile

- Dreistufige Radioauswahl außerhalb und rechts neben dem Benutzermenü für alle Rollen; eindeutige Namen, Tooltips und sichtbare Fokusmarkierung. Animierter Schieber folgt der gespeicherten Auswahl auch bei Tab-Synchronisierung; Automatisch bleibt bei Systemwechsel ausgewählt.
- 32 JavaScript-Tests und ergänzende DOM-Prüfung der echten Radioelemente mit Klicks, genau einer aktiven Stellung, gespeichertem Wert und Anwendung des Light/Dark-Designs erfolgreich. Kein Backend-Verhalten verändert; echte Browser-Sichtprüfung auf dem Raspberry steht aus.

## Telegrammzähler

- Empfang von 300 Telegrammen trotz auf 250 Zeilen begrenztem Ringpuffer vollständig gezählt; ausgehende Telegramme ausgeschlossen. Minuten-/Stundengrenzen, Auslaufen ohne weitere Telegramme und Entfernen alter Zählwerte mit kontrollierter monotoner Uhr geprüft.
- Dashboard-API liefert beide Zähler nur in der Admin-Telegrammansicht. UI zeigt formatierte Werte nur auf der Telegrammseite und aktualisiert auch auf null. Insgesamt 14 KNX-, sieben Web- und 32 JavaScript-Tests erfolgreich.
- Keine zusätzliche KNX-Abfrage oder Datenbankspeicherung; echte Buslastanzeige nach dem Update auf dem Raspberry noch abzunehmen.

## Dark und Light Mode

- Alle bisherigen Dark-Farben nach Rückauflösung der CSS-Variablen exakt mit dem veröffentlichten Stylesheet verglichen; beide Paletten vollständig. Zehn zentrale Text-/Hintergrundkombinationen des Light Mode mit mindestens 4,5:1 Kontrast geprüft.
- Fünf neue JavaScript-Prüfungen: Dark-Voreinstellung vor DOM-Aufbau, Speichern/Neuladen, Automatisch mit beiden Systemwechseln, gesperrter Speicher/fehlende Systemerkennung/ungültige Werte sowie Tab-Synchronisierung und Anmeldung ohne Auswahlfeld. Insgesamt 31 Dashboard-JavaScript-Tests erfolgreich.
- Sieben Webtests einschließlich öffentlichem Theme-Script und Laden vor dem Stylesheet erfolgreich. Bestehende DOM-Prüfungen für Mail, Profile und Kalender sowie Theme-Auswahl mit Admin/User/Viewer erfolgreich.
- Pixelgenaue Sichtprüfung in einem echten Browser und Abnahme auf dem Raspberry stehen aus.

## SMTP-Anbieterhilfe

- Info-Button, modale Hilfe, zehn eindeutige Anbieter, Zuordnung zu sechs konkreten Eingabefeldern und gemeinsame weitere Felder geprüft. Anbieterauswahl zeigt jeweils genau ein Beispiel; Schließen setzt den Buttonzustand zurück und erhält ungespeicherte SMTP-Daten.
- Öffnen/Auswahl/Schließen lösen weder Speichern noch Testmail aus. Externe Quellen ausschließlich HTTPS mit noopener/noreferrer; mailbox.org-App-Passwort, Zoho-Kontotyp/Rechenzentrum und 1&1-/IONOS-Produktabgrenzung explizit dargestellt.
- Anbieterwerte am 22.10.2026 anhand der verlinkten offiziellen Dokumentation geprüft; keine echte SMTP-Verbindung oder Zustellung getestet. Bestehende Mail-, Profil- und Kalender-DOM-Prüfungen sowie Dashboard-Regressionstests erfolgreich. Pixelgenaue Sichtprüfung vor Ort steht aus.

## Mailmodul

- Neue Vorgänge statt wiederholter Telegramme, Quittierungen oder Migration als Versandtrigger; Standard-Opt-out, je Empfänger ein Auftrag, Prioritätsvorlagen/Platzhalter und unveränderte Nachrichtensnapshots geprüft.
- Dauerhafte Warteschlange, transaktionaler Rollback bei Schreibfehler, Wiederanlauf unterbrochener Aufträge, Fehler-Wiederholungen/Maximum und manueller Neustart geprüft. Deaktivierung/gelöschte Empfänger sowie weiter responsive Alarmdatenbank bei langsamem SMTP geprüft.
- SMTP über STARTTLS, direktes TLS und lokalen Relay mit simulierten Transporten geprüft; kein stiller Rückfall ohne TLS. Passwort-Redaktion, Beibehalten/Löschen, Revisionen, ungültige Templates/Header und Admin-/CSRF-Schutz geprüft.
- UI-Prüfung: Verwaltungsseite, Vorlagen je Priorität, Platzhalterhilfe, Passwortfeld, Testmail nur mit gespeicherten Angaben und gültigem Empfänger, Versandstatus/erneute Versuche sowie Benutzer-Schalter. Bestehende Profil-, Meldungs- und Kalenderprüfungen weiterhin erfolgreich.
- Keine realen E-Mails versendet. Verbindung/Zustellung mit dem vorgesehenen SMTP-Server muss nach Konfiguration auf dem Raspberry über die Testmail abgenommen werden.

## Benutzerprofile und kompakte Vorgangsnummer

- Registrierung mit E-Mail/Vor-/Nachname, serverseitige Ablehnung ungültiger/fehlender Angaben und E-Mail-Duplikate, Admin-Rechte, Profiländerung mit Sitzungswiderruf und CLI-Nachtrag ohne Passwort-/Rollenänderung geprüft.
- Migration alter Benutzertabellen und Quittierungen mit erhaltenen Konten, Sitzungen und Alarmzuständen geprüft. Quittierungsnamen überleben Namensänderung und Kontolöschung; fehlende historische Namen werden bei Profilergänzung nachgetragen.
- UI-Prüfung für Admin/User/Viewer: acht Spalten mit schmaler Vorgangsnummer, gemeinsame Bereich/GA/DPT-Zeile und voller Quittierungsname. Kontenformular mit Pflichtfeldern und E-Mail-Eingabetyp geprüft. Raspberry-Datenbank nicht direkt erreichbar; vorhandene Profile müssen nach dem Update per Benutzerverwaltung oder user-profile ergänzt werden.

## Gemeinsame Datumsauswahl und kompakter Seitenkopf

- Gemeinsame Kalenderauswahl für Admin, User und Viewer im DOM geprüft: zwei Monate, Monatswechsel, Einzeltag, umgekehrte Auswahl, Jahreswechsel, Übernehmen/Abbrechen, Escape, Klick außerhalb und Zurücksetzen ohne Änderung des Statusfilters. Keine alten Filterfelder/Schalter oder „GEBÄUDEÜBERWACHUNG“-Elemente vorhanden.
- Lokale Tagesgrenzen einschließlich Endtag sowie Sommer-/Winterzeitwechsel, ungültige Datumswerte und Leerung geprüft; kein zusätzlicher Abruf beim bloßen Auswählen/Abbrechen. Bestehende Dashboard-Regressionstests ausgeführt.
- Kalenderdatei als lokales statisches Asset eingebunden, ohne zusätzliche Laufzeitabhängigkeit. Obere Seitenabstände und responsive Kalenderregeln anhand CSS geprüft; Sichtprüfung auf dem Raspberry steht aus.

## Zähler für abgeschlossene Vorgänge

- Zähler umfasst gegangene/beendete und quittierte Vorgänge. Wiederauftreten mit älterer Quittierung bleibt getrennt gezählt; Backend- und Dashboard-Regressionstests sowie DOM-Prüfung für alle drei Rollen durchgeführt.
- Statusfilter rechts neben der Meldungsüberschrift, Standard „Meldungen · Aktiv“ sowie Umschalten auf „Meldungen · Abgeschlossen“ und zurück geprüft.
- Reihenfolge, Filter auf Abgeschlossen und erneuter Klick zum Zurücksetzen geprüft. Breite auf großen Bildschirmen im Verhältnis 2:2:2:1:1; bestehende Zweispaltenansicht auf kleinen Bildschirmen erhalten. Sichtprüfung vor Ort steht aus.

## Kompakte Vorgangsliste

- Dashboard-Regressionstests und DOM-Prüfung für Admin, User und Viewer: Ansichtsauswahl innerhalb des zunächst verborgenen Filterbereichs, vereinfachter Zähler, Prioritätsbezeichnung mit Nummern-Tooltip und keine Übernahmehinweise in den Zeilen.
- Drei Zeitspalten mit je 160 Pixeln, linksbündige Überschriften, Zeitstempel ohne Zeilenumbruch und mittige Aktionsspalte anhand der CSS-Regeln geprüft. Sichtprüfung auf dem Raspberry steht aus.

## Gemeinsame Alarmvorgänge

- Eigene Vorgangsnummer, drei unabhängige Zeitpunkte, wiederholter Empfang, Quittierung vor/nach Gehen und erneutes Auftreten vor alter Quittierung geprüft. Quittieren eines älteren Vorgangs lässt einen neuen aktiven Vorgang unquittiert.
- Migration mit erhaltenem Ereignisverlauf und nur aktuellen Zuständen geprüft; kein Vorgang bei initialem Normalwert. Aktuelle Zustände, gespeicherte Matrix, Benutzerkonto und Sitzung bleiben erhalten; lokale SQLite-Sicherung, idempotenter zweiter Start und transaktionaler Wiederanlauf nach absichtlichem Fehler geprüft.
- Historienfilter vor 500er-Begrenzung, vollständige offene Liste, Entfernen eines Alarms ohne erfundenen Gehen-Zeitpunkt, atomarer Rollback bei Live-Schreibfehler und Aufbewahrung offener/zuletzt quittierter Vorgänge geprüft.
- HTTP-Rechte und Herkunftsschutz für Admin/User/Viewer, genaue Vorgangsquittierung sowie UI-Integration mit einer Tabelle, drei Zeitspalten, Benutzer, Ansichtsauswahl, Zählerumschaltung und Viewer-Rechten geprüft.
- Tatsächliche Raspberry-Datenbank und KNX-Geräte sind in dieser Umgebung nicht erreichbar. Die reale Übernahme erfolgt beim Update/ersten Start; visuelle Abnahme vor Ort steht aus.

## Stabiler Alarmzeitstempel

- Wiederholte identische Zustände, abweichende Quelle, Quittierung, erneuter Empfang, Neustart, Gehen sowie Sortierung und Datumsfilter nach changed_at geprüft. Last_seen darf sich ändern, changed_at bleibt bis zum nächsten Alarmzustandswechsel erhalten. Dashboard-Regressionstest zeigt den Zustandswechsel des Vortags trotz späterem Empfang am Folgetag.

## Einklappbare Matrix-Werkzeuge

- Werkzeuge einschließlich CSV und Erläuterungen initial verborgen; Toggle samt aria-expanded geprüft. Suche und Alarmanzahl außerhalb des Werkzeugbereichs, Anzahl rechts. Überschrift/Zurück-Link und Tabelle im gemeinsamen, maximal 1808 Pixel breiten Container mit 24 Pixel Innenabstand.

## Matrixabstände (vorheriger Stand)

- Überschrift nutzt wieder die unveränderte globale main-Breite von 1500 Pixeln und globale Seitenabstände. Nur Matrixpanel zentriert und maximal 1760 Pixel breit; DOM/CSS-Prüfung erfolgreich. Sichtprüfung weiterhin auf dem Raspberry erforderlich.

## Alarmmatrix bei FullHD

- Der Matrixbereich nutzt bis zu 1760 Pixel Breite, bei kleineren Fenstern mit 24 Pixel Seitenabstand. Die Überschrift nutzt den normalen Seitencontainer. Feste Tabellenaufteilung (100 Prozent insgesamt), 11 Spalten und aufgehobene Feld-Mindestbreiten per DOM/CSS geprüft; 19 JavaScript-Prüfungen erfolgreich. Chromium-Download in dieser Umgebung fehlgeschlagen; visuelle Browserabnahme bei 1920×1080 auf dem Raspberry steht aus.

## Unbekannt-Filter

- Bestehenden API-Test um unbekannten Zustand erweitert: dieser wird gezielt außerhalb der normalen Meldungsliste geladen, Gesamtsummen bleiben gleich.

## Statuszähler als Filter

- API für alle drei Zustandsfilter geprüft, einschließlich unveränderter Gesamtsummen und exakt eines unbekannten Zustands trotz alter Empfangszeiten bekannter Werte. Ungültiger Filter wird abgewiesen. DOM-Prüfung für alle Rollen: Auswahl per Klick, aria-pressed, erneuter Klick hebt Filter auf.
- Bekannte gespeicherte Zustände erhalten unabhängig vom Dienststart die Qualität ok; keine Einstufung als restored.

## Kompakte Detailspalten

- Rechte Detailspalten mit festen Breiten; Meldung/Bereich erhält Restbreite. DOM-Prüfung für drei Rollen: Statusüberschrift, GA/DPT in Meldungszelle und keine Operatoranzeige. 19 JavaScript-Prüfungen erfolgreich; visuelle Abnahme auf Raspberry steht aus.

## Meldungsauswahl und Sortierung

- Normale (auch wiederhergestellte) und unbekannte Zustände aus der Meldungsliste ausgeschlossen; aktive, aktiv quittierte und gegangene nicht quittierte Einträge berücksichtigt. Priorität vor Zeitstempel und unabhängig vom Quittierstatus geprüft. Hinweis „Wert vor Neustart“ entfernt.

## Scrollbare Listen und Filter

- Alle 601 Meldungen in einer Antwort; Historie auf 500 begrenzt, gezielter Suchtreffer und Datumsfilter außerhalb der neuesten 500 nachgewiesen. Zähler unabhängig von Filtern, alte paginierte API weiterhin kompatibel. Filter zunächst eingeklappt und ohne neue Abfrage umschaltbar.

## Meldungstabelle

- KNX-Leseabfrage ausschließlich auf der Admin-Seite Telegramme anzeigen; Meldungsliste enthält keine Abfrage-Steuerung mehr.

- Regel in der Meldungszelle unter Bereich/Priorität, Überschrift Zeitstempel und auf die Meldungsansicht begrenzte Spaltenausrichtung umgesetzt. 19 JavaScript-Prüfungen sowie DOM-Prüfung für drei Rollen, alle 601 Meldungen, 500 Historienzeilen und Filterumschaltung erfolgreich. Visuelle Abnahme auf dem Raspberry steht aus.

## Datumsfilter, kompatible Seiten-API und KNX-Leseabfrage

- 501 Historienereignisse über drei Seiten vollständig und ohne Überschneidungen, Grenzen 201–400, Tagesfilter, leere Suche und Seitenbegrenzung geprüft. 466 Meldungen mit 200/200/66 Einträgen und Filter auf den letzten Empfang geprüft.
- Gesamte Zähler trotz Seitenfilter, lokale Tagesgrenzen einschließlich Endtag, Zurücksetzen auf Seite 1 und direkte Seitenwahl geprüft. Die frühere Seiten-API bleibt kompatibel; die Oberfläche verwendet die neue Listenansicht.
- Leseabfrage mit echten GroupValueRead-Telegrammobjekten und simulierter Übertragung geprüft: keine Schreibtelegramme, kein erfundener Zustand, nur gültige Antworten zählen, Sperre paralleler Abfragen, Verbindungsauswahl und Abbruch beim Stoppen. API-Rechte für Admin/User/Viewer und Aktionsheader geprüft.
- KNX-Abfrage auf dem realen Raspberry/Bus und visuelle Browserabnahme stehen aus; Antworten hängen von ETS-Flags und der Gerätetopologie ab.

## Zahlenprioritäten

- Nummer und Bezeichnung getrennt; Standardwerte 1 Brand, 2 Warnung, 3 Service, 4 Info. Tests für Live-Umbenennung ohne Zustandsverlust, CSV-Zahlen, Legacy-Migration, unbekannte Nummern, Löschschutz, Revisionen und Rollen.

## Alarmmatrix im Dashboard

- Gesamter Prüfstand: 124 Python-Tests und 21 Dashboard-Tests erfolgreich.

- Gemeinsame Validierung für Tabellenzeilen und CSV, automatische IDs, sofortige Auswertung, Neustart-Persistenz, Bearbeitung mit Zustandserhalt bzw. gezieltem Reset, unveränderte Historie und Datenbankfehler mit Rücknahme geprüft.
- API-Prüfungen für Admin/User/Viewer, fremde Herkunft, fehlenden Aktionsheader, parallele Revisionen, CSV-Vorlage und abgelehnten Doppelimport.
- Dashboard-Tests für neue Zeilen ohne selbst vergebene ID, Speichern mit Revision und CSV-Import nur ohne ungespeicherte Änderungen. DOM-Prüfung aller Seiten und der Tabellenbearbeitung mit simulierten Serverantworten für Admin und User erfolgreich; echte visuelle Browser- und Raspberry-Abnahme steht aus.

## Automatisches Neuladen nach Updates

- Timer-Test bestätigt genau einen Aufruf zum Neuladen nach 500 Millisekunden bei beobachtetem Update-Erfolg. Ein gespeicherter Erfolg beim Seitenaufruf und laufende Updates lösen keinen solchen Timer aus.

## Update-Erfolgsmeldung

- Dashboard-Test prüft: gespeicherter früherer Erfolg bleibt ausgeblendet; beobachteter Installationsabschluss wird angezeigt; erneutes Öffnen blendet die Meldung und den Neuladen-Button wieder aus. Alle siebzehn Dashboard-Tests erfolgreich.
- Update-Polling mit altem und anschließend neuem Serverstand geprüft: Versionshinweis wechselt ohne Seitenneuladen auf „Installierte Version ist aktuell.“; Versionslink und Update-Kasten werden gleichzeitig angepasst.

## Manuelle Versionsprüfung und Update-Kasten

- Abruf über GitHub-API mit No-Cache-Headern und eindeutiger Query sowie Rückfall auf Raw-Datei durch simulierte Antworten geprüft.
- HTTP-Abfragen mit refresh=true umgehen sowohl Versions- als auch Historienpuffer; neue Version und neue Historie ohne Ablauf der Pufferfrist getestet.
- Sofortige Rückmeldung, gesperrter Prüfbutton, Abschluss mit Prüfzeitpunkt und Update-Kasten nur bei neuerem Stand getestet. Prüfbutton steht unabhängig vom Update-Kasten zur Verfügung.
- Ursache eines eventuellen zusätzlichen Netzwerk-/GitHub-Zugriffsfehlers auf dem Raspberry ist hier nicht nachgewiesen; dieser muss bei Bedarf anhand des Dienstprotokolls geprüft werden.

## Feststehende Kopfzeile

- Gemeinsame Kopfzeile fest positioniert; Abstand zum Seiteninhalt und Sprungmarken passend zur Höhe definiert. Dieselbe CSS-Regel gilt für die Anmeldung.
- Versionslink nur noch in der Kopfzeile; bisheriger Fußtext und Footer entfernt. Bestehende Prüfungen für Versionsanzeige und Zugriff bleiben gültig.
- Mobile Leiste und Menüs mit eigener Höhen-/Breitenregel ergänzt; echte visuelle Browserabnahme steht weiter aus.

## Update nur bei neuerer Version

- Button bleibt bei gleicher/älterer Version, fehlgeschlagener Prüfung, fehlendem Helfer oder laufendem Update deaktiviert.
- Server prüft vor einer Anforderung ohne Cache; unbestätigte Updates erzeugen keine Anforderungsdatei. Root-Helfer überspringt gleiche oder ältere Versionen vor dem Installeraufruf.

## Dashboard-Menüs, eigene Seiten und Update

- 87 Python-Tests und elf JavaScript-Tests erfolgreich: Rollenmatrix einschließlich Admin-Telegrammseite, eigene Kennwortänderung für alle Rollen mit Sitzungssperre und Rollenerhalt, CSRF-/Parameterprüfung und verweigerte direkte Fremdzugriffe.
- Update-Anforderungsdatei und Statusanzeige mit lokal isolierten Testpfaden geprüft. Fehlender Helfer, aktive oder doppelte Anforderung und Symlinks behandelt.
- Root-Worker und Installer verwenden für veröffentlichte Programmdateien eine lesbare Maske; private Daten-/Konfigurationsverzeichnisse bleiben explizit geschützt.
- Root-Worker mit simuliertem Git-/Installationsprozess geprüft: feste Quelle und main-Zweig, keine Auswertung der Anforderungsbytes, atomarer lesbarer Status, Erfolg erst nach erfolgreicher Installation und Fehler nach Abbruch. Keine echte Paketinstallation im Prüfcontainer durchgeführt.
- JavaScript-Prüfung für Rang/Benutzername, Adminmenü, Quittierschaltflächen, separate Navigation und grüne/rote/gelbe KNX-Anzeige erfolgreich.
- Versionen numerisch statt lexikalisch verglichen; neuere/gleiche/ältere Version, Pufferung, fehlgeschlagene Prüfung ohne Meldung, lokale Historie und Rechte für alle Rollen getestet.
- Vollständige DOM-Simulation für alle Seiten und Rollen: sichere Historientexte, Kennwortbestätigung, Update-Anforderung, rote Versionsmarkierung nur bei neuer Version und stille Offline-Prüfung erfolgreich. Keine visuelle Browserabnahme; ein lokaler Browser war nicht verfügbar.
- systemd-Update auf einem echten Raspberry und vollständige Betriebsabnahme stehen noch aus.

## Direkter Webzugriff auf Port 80

- 72 Python-Tests und sechs JavaScript-Tests erfolgreich.

- Port 80 als Vorgabe und Erhalt explizit konfigurierter Ports geprüft.
- Port allein sowie Host und Port gemeinsam migriert; wiederholte Ausführung, fehlende Schlüssel, Konfigurationserhalt und Dateirechte geprüft. Ungültige oder uneindeutige Ports verändern die Datei nicht.
- systemd-Datei mit unverändertem Dienstbenutzer und ausschließlich CAP_NET_BIND_SERVICE geprüft; einzig der auf diesem Prüfhost nicht installierte ExecStart-Pfad wird beanstandet. Shellsyntax erfolgreich geprüft.
- Umstellung und Entfernung von nginx auf dem Raspberry stehen noch aus.

## Anmeldung und Benutzerrollen

- 68 Python-Tests einschließlich Rollenmatrix, verweigerter direkter Konfigurations- und Benutzeraktionen, Login, Logout, Sitzungsablauf, Widerruf und Migration bestehender Kennwörter erfolgreich.
- Alte Datenbank mit dreispaltiger Benutzertabelle migriert; Konten und Sitzungen nach Neustart und konsistentem Backup geprüft.
- Schutz des letzten Admins, Eingabevalidierung, unbekannte Benutzer, doppelte Namen, Größenlimit und Herkunfts-/Aktionsheader geprüft. Benutzerliste enthält keine Hashes oder Passwörter.
- Passwortberechnung beim Login hält keine Alarm-/Datenbanksperre; parallele Alarmabfrage während blockierter Passwortprüfung getestet.
- Wiederholte Dashboard-Abrufe über Sitzung führen keine Passwortberechnung aus. Der frühere Testschalter kann Anmeldung und Rechte nicht umgehen.
- Sechs JavaScript-Tests erfolgreich. JavaScript-Rollenprüfung: Einstellungsreiter für User/Viewer ausgeblendet, Quittierschaltfläche für Viewer entfernt; Verlust von Adminrechten schließt Einstellungsansichten.
- Vollständige Dashboard-DOM-Simulation für alle Rollen einschließlich Anlegen eines Kontos, Passwortbestätigung, sicherer Darstellung von Benutzernamen und Navigation erfolgreich.
- Update und Browser-Anmeldung auf dem Raspberry sowie visuelle Abnahme stehen noch aus. Keine Behebung der ungeklärten Netzwerkausfälle behauptet.

## DPT-Prüfung und Korrekturen

- 61 Python-Tests und vier JavaScript-Tests erfolgreich; Shell-/JavaScript-Syntax geprüft.
- Hauptnummer plus ein passender Untertyp ist eindeutig; mehrere konkrete Untertypen oder ein nicht unterstützter Untertyp werden nicht geraten.
- Registry von xknx 4.0.0 und Hauptnummern gegen veröffentlichte KNX-Übersicht abgeglichen; verbleibende Lücken in DPT-SUPPORT.md dokumentiert.
- Numerischer DPT-20-Basisdecoder, deutsche 20.102-Anzeige und klare Trennung zum bitcodierten HVAC-Status geprüft.
- Alle 231 Katalogeinträge in direkter und ETS-Schreibweise durch die Importprüfung getestet; bislang abgewiesene vier-/fünfstellige Untertypen nun erkannt.
- Alarmmatrix mit vierstelligem Untertyp und Abweisung von Untertypen über 65535 geprüft.
- Bereits gespeicherte ETS-Zuordnungen bleiben erhalten und werden erst bei erneutem Import neu bewertet. Nutzertest auf Raspberry steht aus.

## ETS-Import und Telegrammanzeige

- 56 Python-Tests erfolgreich, keine übersprungen; vier JavaScript-Regressionstests und Shell-/JavaScript-Syntax erfolgreich.
- XML mit Namensraum, UTF-8/UTF-16, zwei- und dreistufigen sowie numerischen Adressen geprüft. CSV mit Hierarchiezeilen, Semikolon, Komma, Tabulator, Windows-1252 und ETS-Varianten 3/1, 1/1, 1/3 geprüft.
- Fehlende, mehrdeutige, ungültige und nicht unterstützte DPT behalten Rohwertanzeige; doppelte und ungültige Adressen, DTD/Entitäten und Übergrößen werden abgewiesen.
- Vorschau ohne Speicherung, Rechte-/Herkunftsprüfung, geänderte Datei und veraltete Revision, Ergänzen/Ersetzen, Persistenz, Backup und Fehler ohne Katalogänderung getestet.
- Echte xknx-Dekodierung für importierte Adressen ohne Alarmregel sowie Vorrang vorhandener Alarm-DPT geprüft.
- DOM-Simulation: Dateivorschau vor Übernahme, Suchfilter, Seitenwechsel bei 205 Adressen, sichere Textdarstellung, Importanfrage, Katalog laden, Navigation und Telegrammnamen mit Einheiten erfolgreich. Keine visuelle Browserabnahme dieser Erweiterung.
- Nutzer hat MDT-Verbindung mit Status CONNECTED und eingehenden Gruppentelegrammen am Raspberry bestätigt. Der Anwender hat den ETS-Import bestätigt; die Alarmmatrix-Abnahme steht noch aus.
- Zeitweise Web-Timeouts weiterhin ungeklärt; sie traten auch beim unabhängigen Python-Testserver auf. Keine Behebung durch diese Funktion behauptet.

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
- MDT-Wiederverbindung und Alarmmatrix-Abnahme.
- NAS-Backup anpassen; alter Timer bleibt bis dahin deaktiviert.

Änderungen stehen in [CHANGELOG.md](CHANGELOG.md).
