# Prüfstand

Stand: 21.10.2026. Projektversion 0.10.14, Inbetriebnahmeversion.

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
