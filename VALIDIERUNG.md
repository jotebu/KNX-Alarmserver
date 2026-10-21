# Prüfstand

Stand: 21.10.2026. Projektversion 0.10.08, Inbetriebnahmeversion.

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
