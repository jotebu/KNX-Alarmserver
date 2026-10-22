# Changelog

Alle folgenden Projektänderungen werden hier pro Version dokumentiert, neueste Version zuerst.

## 0.15.11 – 23.10.2026

- KNX-Icon nach dem schlechtesten Verbindungsstatus im Menü einfärben: Rot vor Gelb vor Grün. Ohne konfigurierte Verbindung gelb anzeigen; Speicherfehler bleiben rot.

## 0.15.10 – 23.10.2026

- Überschrift im KNX-Statusmenü bei mehreren Verbindungen automatisch auf „KNX-Verbindungen“ ändern; bei null oder einer Verbindung bleibt die Einzahl.

## 0.15.9 – 23.10.2026

- KNX-Statusmenü verkleinern: Verbindungsnamen mit grünem, rotem oder gelbem Statuspunkt; ein gemeinsamer letzter Empfang unter der Liste. Deaktivierte konfigurierte Verbindungen ebenfalls anzeigen. Zusammenfassende Statuszeile im Menü entfernen, Abstände und Breite anpassen.

## 0.15.8 – 22.10.2026

- Meldeliste beim Öffnen mit 100 Zeilen darstellen und nahe dem Scrollende jeweils 100 weitere einblenden. Summenzähler, Filterergebnisse und Sortierung bleiben unabhängig von der sichtbaren Teilmenge; Filter- und Sortierwechsel beginnen wieder am Listenanfang.

## 0.15.7 – 22.10.2026

- Gesamte Vorgangsnummernspalte „#“ einschließlich Zahlen, Platzhalter und begrenztem Nummerntext mittig ausrichten.

## 0.15.6 – 22.10.2026

- Kleine Sortierpfeile neben den Spaltenüberschriften entfernen. Sortierung per Klick und zugänglicher Sortierstatus bleiben erhalten.

## 0.15.5 – 22.10.2026

- Bestätigte neue Version beim Abruf des Update-Dienststatus erhalten: eine fehlgeschlagene zweite Versionsprüfung darf den Update-Kasten und dessen Button nicht ausblenden, während die Versionsinfo weiterhin eine neue Version meldet.
- Ältere Prüfergebnisse ignorieren. Eine neue erfolgreiche Prüfung bzw. ein geänderter installierter Softwarestand aktualisiert den bekannten Versionsstatus; nach erfolgreichem Update weiterhin „aktuell“ anzeigen.
- Serverseitige erneute Versionsprüfung vor dem tatsächlichen Update bleibt erhalten; ohne jemals bestätigte neuere Version bleibt der Update-Button gesperrt. Rollen- und Dienstprüfung unverändert.

## 0.15.4 – 22.10.2026

- Alle Spalten der Meldeliste per Überschrift auf-/absteigend sortieren: Priorität, Vorgangsnummer, Meldung/Bereich, Zustand, Gekommen, Quittiert, Gegangen und verfügbare Aktion. Aktuelle Richtung mit Pfeil und zugänglichem Sortierstatus kennzeichnen.
- Zahlen numerisch und Zeitstempel chronologisch vergleichen; fehlende Werte unabhängig von der Richtung am Ende anzeigen. Namenssortierung berücksichtigt Bereich/GA/DPT, Quittierungszeit bei Gleichstand den Namen.
- Sortierung während automatischer Aktualisierung sowie Status-/Datumsfilterung erhalten; ursprüngliche Grundsortierung Priorität/Gekommen bis zur ersten Auswahl verwenden. Tastaturbedienung und Fokus auf der gewählten Überschrift erhalten.

## 0.15.3 – 22.10.2026

- Spaltenüberschrift „#“ in der Meldeliste mittig ausrichten.

## 0.15.2 – 22.10.2026

- Untertitel „Aktuelle Meldungen, Quittierungen und Ereignisverlauf.“ auf dem Dashboard entfernen und dessen Platz einschließlich des zusätzlichen Überschriftenabstands freigeben. Zähler und Meldeliste rücken nach oben; Beschreibungen der Verwaltungsseiten bleiben erhalten.

## 0.15.1 – 22.10.2026

- Matrix-Einzeltest als kompakten Dialog mit Schnittstelle und einem Button „Alarm auslösen“ anzeigen. Umfangreiche Vorschau und getrennte Aktionen bleiben dem globalen Testmodus vorbehalten.
- Einzeltest serverseitig als festes Paar aus Alarmwert und Normalwert mit einer Sekunde Abstand ausführen; Ablauf läuft auch nach Schließen des Dialogs weiter. GA und jeweils zuletzt gesendeten Wert mit Phase anzeigen.
- Schnittstellenwahl bei nur einer verfügbaren Verbindung sperren. Mailabschaltung, DPT-/Regelprüfung, Rechte und Abbruch bei Fehlern erhalten.

## 0.15.0 – 22.10.2026

- KNX-Testmodus zur Ersteinrichtung unter Telegramme: Vorschau mit Alarm-/Normalwerten, Auswahl je Alarm-GA und aktiver Verbindung, getrennte Durchläufe für Alarm und Normal, Fortschritt und Stoppen. Ausschließlich Admins dürfen Bus-Schreibtelegramme auslösen.
- Testwerte aus DPT, Operator, Grenzwert und Hysterese bestimmen und nach KNX-Codierung/Decodierung erneut gegen die Alarmregel prüfen. Unmögliche Wertepaare, reine Beobachtung und strukturierte Feldregeln begründet ausschließen; keine pauschale 0/1-Annahme.
- Fester Abstand von einer Sekunde zwischen abgeschlossenen Schreibvorgängen; nur ein Test oder eine Statusabfrage gleichzeitig. Bei Matrixänderung, Verbindungsverlust oder Dienstwechsel abbrechen; keine automatische Fortsetzung und keine automatische Rücksetzung auf Normal.
- Vor dem ersten Bus-Schreiben laufenden SMTP-Versand abwarten und Mailversand dauerhaft ausschalten. Während des Tests erneutes Aktivieren und Testmails sperren. Benutzerbezogene Empfängereinstellungen bleiben erhalten; bestehende Versandaufträge pausieren. Keine automatische Reaktivierung.
- Nach erfolgreicher Übergabe an die KNX-Schnittstelle Testwerte lokal mit Quelle „KNX-Test“ auswerten und reguläre Vorgänge/Historie führen; keine erfundene Empfangsbestätigung. Normal-Testwerte stellen keine früheren Messwerte wieder her.
- Test-Icon rechts in jeder gespeicherten Matrixzeile für Admins: dieselbe Vorschau und beide Testaktionen für genau einen Eintrag. Bei ungespeicherten Änderungen zunächst Speichern verlangen.

## 0.14.10 – 22.10.2026

- Quittieren-Button in der Meldetabelle mit kleinerer Schrift und geringerem Innenabstand gestalten; Beschriftung ohne Zeilenumbruch vollständig in der kompakten Aktionsspalte darstellen.

## 0.14.9 – 22.10.2026

- Erläuterung unter der Meldeliste und Hinweistext im Zeitraumkalender entfernen. Zeitraum weiterhin mit dem gewählten Statusfilter kombinieren.
- Zeitraum-Button kompakter und unabhängig von Überschrift/Vorgangszähler mittig anordnen; auf schmalen Bildschirmen eine eigene zentrierte Zeile nutzen.
- Gekommen, Quittiert und Gegangen auf 148 Pixel sowie Aktion auf 96 Pixel verschmälern; Zeitstempel kompakt und vollständig darstellen. Vertikale Scrollleiste der Meldetabelle dauerhaft mit reserviertem Platz vorsehen.

## 0.14.8 – 22.10.2026

- Darstellungsschalter im Benutzermenü links mit demselben Innenabstand wie die übrigen Menüeinträge ausrichten.

## 0.14.7 – 22.10.2026

- Sichtbare Beschriftung „Darstellung“ aus dem Benutzermenü entfernen. Position, zugänglicher Name und Funktion des dreistufigen Schalters bleiben erhalten.

## 0.14.6 – 22.10.2026

- Rang aus der Kopfzeile ins aufgeklappte Benutzermenü unter den Benutzernamen verschieben. In der Kopfzeile ausschließlich das Benutzer-Icon anzeigen; Rollen und Berechtigungen beibehalten.

## 0.14.5 – 22.10.2026

- Dreistufigen Darstellungsschalter ins Benutzermenü unter den Benutzernamen verschieben. Mit 108 × 32 Pixeln und kleineren Symbolen an die Menübuttons anpassen; Dark, Light und Automatisch sowie gespeicherte Auswahl beibehalten.
- Zusätzliche Kopfzeilenumbrüche für den externen Schalter wieder entfernen.

## 0.14.4 – 22.10.2026

- Darstellungsauswahl aus dem Benutzermenü rechts daneben in die feste Kopfzeile verschieben: kompakter dreistufiger Schiebeschalter mit Mond, Sonne und Automatik-Symbol.
- Schieber und Symbole an beide Farbpaletten anpassen; gespeicherte Auswahl, Systemautomatik und Tab-Synchronisierung erhalten. Tastaturbedienung, zugängliche Namen, Tooltips und reduzierte Animation berücksichtigen; Kopfzeile auf schmalen Bildschirmen umbrechen.

## 0.14.3 – 22.10.2026

- Minuten- und Stundenzähler auf der Telegrammseite: empfangene Gruppentelegramme aller Verbindungen in den letzten 60 Sekunden bzw. 60 Minuten, laufend mit den Telegrammdaten aktualisiert.
- Unabhängig von Suche, DPT-Erkennung und dem 250-Zeilen-Limit zählen; ausgehende Telegramme ausschließen. Sekundengenaue Zeitfenster mit monotoner Uhr und maximal 3600 Zählwerten im Speicher; nach Dienstneustart bei null beginnen.

## 0.14.2 – 22.10.2026

- Bisheriges Farbdesign unverändert als Dark Mode erhalten und vollständigen Light Mode für Dashboard, Verwaltungsseiten, Formulare, Tabellen, Kalender, Dialoge und Anmeldung ergänzen.
- Auswahl „Dark“, „Light“ oder „Automatisch“ im Benutzermenü für alle Rollen. Automatisch folgt der Systemeinstellung auch bei laufender Nutzung; Dark bleibt die Voreinstellung.
- Auswahl im Browser speichern, zwischen Tabs synchronisieren und vor dem Laden der Styles anwenden. Bei gesperrtem Browserspeicher bleibt die aktuelle Seite umschaltbar.

## 0.14.1 – 22.10.2026

- Info-Button „i“ bei der Mail-Konfiguration mit zehn recherchierten Anbieterbeispielen: Zoho, 1&1 Hosting/IONOS, GMX, Gmail, WEB.DE, Telekom, STRATO, Yahoo, iCloud und mailbox.org.
- Beispiele den tatsächlichen Eingabefeldern zuordnen: SMTP-Host, Port, Verbindung, Benutzername, Passwortart und Absender. Allgemeine Felder, App-Passwörter und Kontotyp-/Rechenzentrumsunterschiede erläutern; offizielle Anbieterquellen und Prüfdatum anzeigen.
- Hilfe bleibt rein informativ und verändert keine SMTP-Daten; modal mit Anbieterauswahl und Schließen/Escape. Nur SMTP-Beispiele mit nutzbarer Passwort-/App-Passwort-Anmeldung aufnehmen.

## 0.14.0 – 22.10.2026

- Mail-Konfiguration unter Verwaltung: eigener/externer SMTP-Server, STARTTLS/direktes TLS/lokaler Relay, optionale Anmeldung, Absender und Serverbezeichnung. SMTP-Passwort nur schreibend entgegennehmen, bei leerem Feld erhalten und nie über die API zurückgeben.
- Betreff-/Textvorlage je Priorität mit dokumentierten Platzhaltern für Meldung, Bereich, GA/DPT, Vorgangsnummer, Beginn, Priorität, Wert/Regel, Quelle, Server und Empfänger. Neue Prioritäten erhalten eine Standardvorlage; ungültige Platzhalter/Formatierungen ablehnen.
- Mail-Empfang je Benutzer in der Benutzerverwaltung aktivieren/deaktivieren (standardmäßig aus). Nur bei neuem Auftreten mit neuer Vorgangsnummer automatische Mails erzeugen; keine nachträgliche Benachrichtigung bestehender Vorgänge.
- Dauerhafte, transaktionale Warteschlange je Empfänger mit Hintergrundversand, fünf automatischen Versuchen, Wiederanlauf und Statusübersicht. Deaktivierte/gelöschte Empfänger vor Versand berücksichtigen; fehlgeschlagene Mails manuell erneut versuchen. Testmail mit gespeicherter SMTP-Konfiguration.
- Update-Meldung auf „Installation läuft. Der Webdienst wird danach neu gestartet.“ ändern.

## 0.13.5 – 22.10.2026

- Neue Benutzer mit E-Mail-Adresse als Benutzername sowie verpflichtendem Vor- und Nachnamen anlegen; serverseitig validieren. Benutzerverwaltung, CLI und Erstinstallation entsprechend ergänzen. Bestehende Konten, Kennwörter, Rollen und Logins erhalten.
- Vollständigen Namen bei Quittierung zusätzlich zur internen Kennung speichern und in der Meldeliste anzeigen. Historische Namen bleiben bei späterer Profiländerung oder Kontolöschung erhalten; fehlende Namen beim Ergänzen des Kontoprofils nachtragen. CLI-Befehl user-profile zur gezielten Ergänzung vorhandener Konten.
- GA und DPT mit Punkt getrennt rechts neben den Bereich setzen. Vorgangsnummer aus dem Meldungstext in eine schmale Spalte „#“ zwischen Priorität und Meldung verschieben; lange Nummern im Tooltip vollständig anzeigen.

## 0.13.4 – 22.10.2026

- Versteckten Filterbereich samt Ansichtspulldown, Meldungssuche und Einblend-Schalter entfernen. Statusfilter direkt über die Zähler verwenden.
- Ein gemeinsames Zeitraumfeld mit zwei Monatskalendern statt separater Von-/Bis-Felder: Beginn/Ende auswählen, Übernehmen, Abbrechen und Zurücksetzen; Tastaturbedienung und schmale Bildschirme unterstützen. Lokale Endtage vollständig berücksichtigen, Statusfilter beim Zurücksetzen beibehalten.
- „GEBÄUDEÜBERWACHUNG“ auf allen Seiten einschließlich Anmeldung entfernen und obere Abstände verkleinern, um mehr Platz für Inhalte zu schaffen.

## 0.13.3 – 22.10.2026

- Statusfilter rechts neben „Meldungen“ mit Punkt als Trennzeichen anzeigen: „Meldungen · Aktiv“, „Meldungen · Abgeschlossen“ usw.

## 0.13.2 – 22.10.2026

- Zusätzlichen Statuszähler „Abgeschlossen“ zwischen „Gegangen · offen“ und „Unbekannt“ einfügen. Klick filtert abgeschlossene Vorgänge; erneuter Klick setzt den Filter zurück.
- Gewählten Statusfilter links vor „Meldungen“ mit Punkt als Trennzeichen anzeigen; Standardansicht „Aktiv · Meldungen“.
- Abgeschlossen und Unbekannt teilen sich auf breiten Bildschirmen den bisherigen Platz des Unbekannt-Zählers. Anzahl abgeschlossener Vorgänge unabhängig von Such-/Datumsfiltern und der 500er-Anzeigegrenze berechnen.

## 0.13.1 – 22.10.2026

- Zeitspalten Gekommen, Quittiert und Gegangen kompakter und linksbündig ausrichten; vollständige Zeitstempel ohne Zeilenumbruch, Aktion mittig.
- Prioritäten als Bezeichnung anzeigen, Nummer im Tooltip. Übernahmehinweise aus den Zeilen entfernen; gespeicherte Vorgangsdaten beibehalten.
- Vorgangszähler auf „Vorgänge: Anzahl“ vereinfachen und rechts anordnen. Ansichtsauswahl in den einklappbaren Filterbereich verschieben.

## 0.13.0 – 22.10.2026

- Gemeinsame Vorgangsliste statt getrennter aktueller Meldungen und Ereignishistorie: eine Zeile pro Auftreten mit Gekommen, Quittiert/Benutzer und Gegangen. Wiederholte Telegramme verändern diese Zeiten nicht.
- Separate Vorgangsnummern und gezielte Quittierung: erneutes Auftreten bleibt unabhängig von älteren noch offenen Quittierungen desselben Alarms. Viewer bleiben ohne Quittierungsrechte.
- Ansichten Offen (Standard), Aktiv/offen, Aktiv/quittiert, Gegangen/offen, Abgeschlossen, Alle und separat Unbekannt. Zähler unabhängig von Suche/Datum; Priorität und Gekommen bestimmen die Reihenfolge. Historische Ansichten auf die neuesten 500 Treffer begrenzen, Filter durchsuchen den vollständigen Bestand.
- Vorhandene Zustände und Ereignisse automatisch und transaktional übernehmen; vorab lokale SQLite-Sicherung bei gefüllter Datenbank. Bestehende Matrix, Benutzer, Sitzungen und Konfiguration beibehalten. Fehlende historische Zeiten kennzeichnen, keine Zeitpunkte erfinden.
- Matrixänderungen/-entfernung ohne fingiertes Gehen protokollieren; aktive/unquittierte Vorgänge vor automatischer Löschung schützen. Technisches Ereignisprotokoll und bisherige API bleiben erhalten.

## 0.12.13 – 22.10.2026

- Zeitstempel der Meldungsliste auf den bereits gespeicherten Zeitpunkt des Alarmzustandswechsels (gekommen/gegangen) umstellen. Wiederholte gleiche Telegramme und KNX-Leseantworten verschieben den Alarmzeitpunkt nicht mehr.
- Sortierung und Datumsfilter verwenden denselben Zustandswechselzeitpunkt. Quittierungszeit bleibt separat; Empfangszeit wird weiterhin intern aktualisiert. Vorhandene Zustandswechselzeiten werden ohne Datenmigration verwendet.

## 0.12.12 – 22.10.2026

- Matrix-Werkzeuge samt Erläuterungen, Speichern, Hinzufügen, CSV-Import und Downloads zunächst einklappen; über „Werkzeuge anzeigen“ einblenden.
- Suche, Seitenauswahl und Alarmanzahl in einer Zeile belassen; Alarmanzahl am rechten Rand. Rückmeldungen zu Änderungen/Speichern bleiben sichtbar.
- Überschrift und Zurück-Link wieder an der gemeinsamen Breite des Matrixbereichs ausrichten; Tabellenbreite bei FullHD unverändert gegenüber dem vorherigen Stand.

## 0.12.11 – 22.10.2026

- Überschrift und Zurück-Link der Alarmmatrix wieder mit dem normalen Seitencontainer und denselben Abständen wie auf den anderen Verwaltungsseiten ausrichten.
- Nur den Matrixbereich verbreitern, zentrieren und auf 1760 Pixel begrenzen. Dadurch bei FullHD etwas schmaler als zuvor, mit unveränderter kompakter Spaltenaufteilung.

## 0.12.10 – 22.10.2026

- Alarmmatrix über die verfügbare Bildschirmbreite anzeigen und die bisherigen pauschalen Mindestbreiten der Eingabefelder entfernen.
- Spaltenbreiten nach Inhalt aufteilen: mehr Platz für Name und Bereich, kompakte Zahlen-/DPT-/Operatorfelder. Bei FullHD und 100 % Browserzoom passen alle Spalten in die Tabelle; auf schmaleren Bildschirmen bleibt horizontales Scrollen möglich.

## 0.12.9 – 22.10.2026

- Auch den Zähler „Unbekannt“ als Filterbutton anbieten. Bei expliziter Auswahl ausschließlich unbekannte Alarme aus der gesamten Matrix laden, unabhängig von ihrer Ausblendung in der normalen Meldungsliste.
- Erneutes Anklicken oder Filter zurücksetzen kehrt zur normalen Meldungsansicht zurück. Filterauswahl und leere Ergebnisliste passend beschriften.

## 0.12.8 – 22.10.2026

- Drei Statuszähler als zugängliche Filterbuttons: Aktiv/offen, Aktiv/quittiert und Gegangen/offen. Erneutes Anklicken oder Filter zurücksetzen hebt die Auswahl auf. Prioritäts-/Zeitsortierung bleibt erhalten, Gesamtsummen bleiben unabhängig vom Listenfilter.
- Unbekannt-Zähler auf tatsächlich unbekannte Alarmzustände beschränken. Gespeicherte bekannte Werte nach Neustart nicht als alt klassifizieren; entsprechende Hinweise und Auswahltexte entfernen. KNX-Abfrage „Unbekannte Werte“ liest nur noch Adressen ohne bekannten Zustand.

## 0.12.7 – 22.10.2026

- Wertspalte in „Status“ umbenennen. Gruppenadresse und DPT unter Meldung/Bereich anzeigen; Operator, Grenzwert und Hysterese dort entfernen (weiterhin in der Alarmmatrix verfügbar).
- Status, Zeitstempel und Quittierung mit festen kompakten Spaltenbreiten am rechten Tabellenrand gruppieren; Meldung/Bereich erhält die übrige Breite.

## 0.12.6 – 22.10.2026

- Zusatzhinweis „Wert vor Neustart“ aus der Meldungsliste entfernen.

- Meldungsliste auf aktive, aktiv quittierte und gegangene noch nicht quittierte Alarme/Störungen beschränken. Normale und unbekannte Zustände erscheinen nicht als Meldung; Zähler und Statusabfrage bleiben vollständig.
- Meldungen zuerst nach Priorität (kleinste Nummer zuerst), dann nach Zeitstempel (neueste zuerst) sortieren, unabhängig vom Quittierstatus. Den bisherigen Filter „Nur offene / unbekannte“ entfernen.

## 0.12.5 – 22.10.2026

- Such- und Datumsfilter in Meldungen und Historie über „Filter anzeigen“ ein-/ausklappen; aktive Filter bleiben beim Einklappen wirksam und sind am Button erkennbar.
- Tabellen innerhalb der verfügbaren Seitenhöhe scrollen, mit sichtbaren Spaltenüberschriften. Seitennavigation entfernen und alle passenden Meldungen zusammen anzeigen.
- Historie auf die neuesten 500 Treffer beschränken; Suche und Datum filtern weiterhin den vollständigen gespeicherten Ereignisbestand vor der Begrenzung. Trefferzahl anzeigen.

## 0.12.4 – 22.10.2026

- KNX-Statusabfrage aus der Meldungsliste auf die bestehende Admin-Seite Telegramme verschieben, einschließlich Verbindungsauswahl und Fortschritt.

- Meldungstabelle: Regel unterhalb von Bereich und Priorität anzeigen. Wert und Gruppenadresse bleiben in der Wertspalte.
- „Letzter Empfang“ in „Zeitstempel“ umbenennen. Wert/Regel, Zeitstempel und Quittierung kompakt am rechten Tabellenrand ausrichten; Meldung/Bereich erhält den übrigen Platz.

## 0.12.3 – 22.10.2026

- Meldungen und Ereignishistorie serverseitig mit 200 Einträgen pro Seite laden; vor/zurück und direkte Seitenwahl. Alle gespeicherten Historienereignisse sind erreichbar, statt nur der bisherigen letzten 200.
- Datumsfilter von/bis einschließlich des gesamten Endtags sowie Suche über alle Treffer vor der Seiteneinteilung. Historie nach Ereigniszeitpunkt, Meldungen nach letztem Empfang filtern. Die Dashboard-Zähler bleiben unabhängig von Seiten und Filtern vollständig.
- KNX-Statusabfrage für Admins und User: unbekannte/alte oder alle Alarmadressen über eine wählbare aktive Verbindung lesen. Nur GroupValueRead, maximal zwei Anfragen pro Sekunde, Fortschritt und gültige Antworten anzeigen. Keine erfundenen Normalwerte bei ausbleibender Antwort.
- Parallele Leseabfragen sperren und bei Verbindungswechsel/Dienstende abbrechen. Bestehende Aufbewahrungsdauer und Telegrammmonitor-Ringpuffer bleiben wirksam.

## 0.12.2 – 21.10.2026

- Prioritäten als stabile ganze Zahlen speichern: zunächst 1 Brand, 2 Warnung, 3 Service, 4 Info; kleine Zahl bedeutet hohe Priorität.
- Neue bearbeitbare Prioritätentabelle für Admins: Bezeichnungen ändern, weitere Nummern anlegen und ungenutzte Nummern entfernen. Verwendete Nummern sind vor versehentlichem Entfernen geschützt; parallele Änderungen werden erkannt.
- Alarmmatrix für Admins und User bietet Nummer und aktuelle Bezeichnung zur Auswahl. Dashboard zeigt beide; Umbenennen ändert weder Alarmzuordnung noch Zustände oder Historie.
- CSV-Vorlage und Export enthalten ausschließlich die Prioritätsnummer. Ältere critical/warning/info-Werte werden beim Laden in 1/2/4 übersetzt, damit vorhandene Installationen und CSVs lesbar bleiben.

## 0.12.1 – 21.10.2026

- Dashboard-Updates abgeschlossen; automatisches Neuladen nach erfolgreichem Update auf 0,5 Sekunden verkürzt.
- Neuer Bereich „Alarmmatrix“ für Admins und User: Alarme in einer Tabelle anlegen, bearbeiten und entfernen; sofortige Übernahme ohne Dienst- oder KNX-Neustart.
- Interne fortlaufende IDs für neue Alarme automatisch serverseitig vergeben. Bestehende IDs und Historien bleiben erhalten; Änderungen von Adresse, DPT oder Auswertungsregel setzen nur den betroffenen aktuellen Zustand zurück.
- Alarmmatrix dauerhaft in SQLite speichern. Nach dem ersten Speichern hat sie gegenüber der bisherigen Start-CSV Vorrang, auch bei Neustarts, Updates und CLI-Prüfung.
- Semikolongetrennte UTF-8-CSV ohne ID-Spalte importieren; Beispiel-CSV und Export des gespeicherten Stands herunterladen. Import ergänzt Alarme, ohne bestehende Gruppenadressen zu überschreiben.
- Gemeinsame Validierung von Tabelle und CSV, atomare Speicherung, Schutz vor parallelem Überschreiben, Begrenzung auf 5000 Alarme und 2 MiB je Anfrage. Viewer erhalten keine Matrix-Verwaltung; Admin-Funktionen bleiben geschützt.

## 0.10.17 – 21.10.2026

- Zusätzlichen Bestätigungsdialog für „Update starten“ entfernt. Der freigegebene Update-Button startet die Aktualisierung direkt und wird sofort gegen Mehrfachklicks gesperrt.

## 0.10.16 – 21.10.2026

- Oberfläche zwei Sekunden nach einem auf der Seite beobachteten erfolgreichen Update automatisch einmal neu laden. Gespeicherte frühere Erfolge lösen kein Neuladen aus.

## 0.10.15 – 21.10.2026

- Versionshinweis beim Abruf des Update-Fortschritts ebenfalls aktualisieren: Nach bestätigtem aktuellem Installationsstand ersetzt „Installierte Version ist aktuell.“ den bisherigen Hinweis auf eine neue Version, ohne manuelles Neuladen.

- Update-Erfolgsmeldung und anschließenden Neuladen-Button nur anzeigen, wenn die geöffnete Seite das Update gestartet oder dessen laufenden Fortschritt beobachtet hat. Gespeicherte Erfolge früherer Updates bleiben beim erneuten Öffnen oder Neuladen ausgeblendet.

## 0.10.14 – 21.10.2026

- „Kennwort ändern“ und „Abmelden“ im Benutzermenü einheitlich darstellen; abweichende ältere Button-Formatierung entfernt.
- Versionsnummer in der Kopfzeile auch beim Überfahren ohne Unterstreichung anzeigen. Der Link zur Versionshistorie bleibt klickbar.

## 0.10.13 – 21.10.2026

- Versionsprüfung beim Öffnen und über „Status prüfen“ ohne lokalen Zwischenspeicher ausführen. GitHub-API als ersten Abrufweg und Raw-Datei als Rückfall nutzen; HTTP-Caches per Header und eindeutiger URL umgehen. Fehler im Dienstprotokoll erfassbar machen.
- Kasten „Alarmserver aktualisieren“ nur für Admins bei bestätigter neuerer Version anzeigen. Rollen-/Dashboard-Aktualisierungen blenden ihn bei aktuellem Stand nicht erneut ein.
- „Status prüfen“ neben die allgemeine Versionsinfo verschoben und für alle Rollen zugänglich gemacht. Fortschritt sofort anzeigen, Button während der Prüfung sperren und anschließend Ergebnis mit Prüfzeitpunkt melden.
- Automatische Prüfungen bleiben bei Fehlern still; ein ausdrücklich angeforderter manueller Abruf erhält eine Rückmeldung. Versions-/Update-Leseanfragen bekommen 20 Sekunden für die begrenzten externen Abrufwege.
- Update-Fortschritt und Ergebnis außerhalb des nur bei veraltetem Stand sichtbaren Kastens anzeigen. Tests für Cache-Umgehung, Abrufrückfall und manuelle Rückmeldung ergänzt.

## 0.10.12 – 21.10.2026

- Kopfzeile auf allen Seiten einschließlich Anmeldung fest am oberen Bildschirmrand halten; Seiteninhalt beginnt darunter.
- Versionsnummer aus dem Fußbereich in die feste Kopfzeile verschoben. Versionshistorie und rote Update-Markierung bleiben erhalten.
- Bisherigen Fußtext entfernt. Schmale Bildschirme erhalten eine zweizeilige Kopfzeile; aufklappbare Menüs bleiben unterhalb der Leiste im sichtbaren Bereich.

## 0.10.11 – 21.10.2026

- Update-Button nur bei einer bestätigten neueren Version, verfügbarem Update-Dienst und ohne laufendes Update aktivieren. Bei fehlgeschlagener Versionsprüfung bleibt er ohne zusätzliche Prüfmeldung deaktiviert.
- Update-API prüft unmittelbar vor der Anforderung erneut ohne Cache. Gleiche, ältere oder nicht bestätigte Versionen lösen keine Installation aus; auch der root-eigene Helfer prüft vor der Installation nochmals den Versionsvergleich.
- Tests für Buttonzustände, erzwungene Versionsprüfung, verweigerte Anforderung und Überspringen gleicher/älterer Versionen ergänzt.

## 0.10.10 – 21.10.2026

- Hauptseite auf Meldungen, Historie und Zähler reduziert; KNX-Informationskasten und bisherige Verwaltungsreiter entfernt.
- Kopfzeile mit Benutzersymbol und Rang, aufklappbarem Benutzernamen, eigener Kennwortänderung und Abmelden ergänzt.
- Admin-Zahnrad mit eigenen, serverseitig geschützten Seiten für Telegramme, KNX Verbindungen, ETS-Import und Benutzerverwaltung eingerichtet.
- KNX-Status als farbiges Symbol mit Details: grün bereit, rot Fehler, gelb deaktiviert/nicht eingerichtet. Bei fehlender Serverantwort Status als unbekannt markieren.
- Eigene Kennwortänderung für alle Rollen mit Prüfung des bisherigen Kennworts; Rolle erhalten und alle bisherigen Kontositzungen widerrufen.
- Versionsnummer öffnet Versionshistorie für alle Rollen; Admin-Updatebutton auf dieser Seite mit Statusanzeige und Wiederaufnahme nach Webdienst-Neustart. Separater root-eigener systemd-Helfer installiert ausschließlich den aktuellen main-Stand des festen GitHub-Repositorys; der Webserver erhält keine allgemeinen root-/sudo-Rechte.
- Installer richtet Update-Pfadüberwachung ein. Updates laufen unabhängig vom Webprozess; doppelte Anforderungen und Browserparameter werden abgewiesen. Bestehende Daten und Konfiguration bleiben erhalten; Installer-Backup und Rückwechsel bei Startfehlern bleiben aktiv.
- Versionsprüfung beim Öffnen mit numerischem Vergleich und Zwischenspeicherung. Bestätigte neue Version rot hervorheben; fehlgeschlagene Prüfung bleibt still. Historie von GitHub oder lokal, sichere Textdarstellung ohne HTML-Ausführung.
- Rollen, eigene Kennwortänderung, Seitenzugriffe, Update-Anforderung, Erfolgs-/Fehlerzustände, Symlink-Behandlung, Menüs, KNX-Farben und Versionsanzeige geprüft.

## 0.10.09 – 21.10.2026

- Direkten Webzugriff auf Port 80 als Vorgabe für neue Installationen eingerichtet: `http://RASPBERRY-IP/`, ohne nginx-Proxy.
- systemd gewährt dem unverändert unprivilegierten Dienstkonto ausschließlich `CAP_NET_BIND_SERVICE` für niedrige Ports. Keine Ausführung des Alarmservers als root.
- Installer und Update-Skript unterstützen `--port PORT`, kombinierbar mit `--lan`. Bestehende Einstellungen werden nur bei ausdrücklicher Optionswahl geändert.
- Bei fehlgeschlagenem Start auch die explizite Host-/Portänderung zurücksetzen. Health-Prüfung an die neue Portvorgabe angepasst.
- Umstellung bestehender Installationen und anschließende Entfernung von nginx dokumentiert. Konten, Rollen, Passwörter, KNX-/ETS-Daten und Alarmzustände bleiben erhalten.
- Portvorgabe, Erhalt expliziter Ports, wiederholte gezielte Migration, fehlende Schlüssel und Abweisung ungültiger oder uneindeutiger Einstellungen geprüft.

## 0.10.08 – 21.10.2026

- Anmeldung wieder verpflichtend; den bisherigen Testschalter ohne Login und die Testseite entfernt. Bestehende Kennwörter erhalten, vorhandene Konten als Admin migriert.
- Formularanmeldung mit 12-Stunden-Sitzung und Abmelden ergänzt. HttpOnly-/SameSite-Cookie, serverseitig nur Tokenhash, keine wiederholte Passwortberechnung bei Dashboard-Abfragen.
- Rollen Admin (alles), User (ansehen und quittieren), Viewer (nur ansehen) auf allen betroffenen API-Endpunkten durchgesetzt. Einstellungsreiter nur für Admin, Quittierschaltflächen nur für Admin und User.
- Benutzerverwaltung im Dashboard: anlegen, Rolle ändern, Kennwort neu setzen, löschen. Letzten Admin schützen; betroffene Sitzungen bei Änderungen und Löschung widerrufen. Quittierungshistorie bleibt erhalten.
- CLI um explizite Rollenwahl zur Einrichtung und Wiederherstellung von Admin-Konten erweitert. Dokumentation und Tests für Migration, Rollen, direkte API-Zugriffe, Sitzungen und Bedienoberfläche ergänzt.

## 0.10.07 – 21.10.2026

- DPT-Unterstützung geprüft und in `DPT-SUPPORT.md` dokumentiert: Hauptnummern, Untertypen und fehlende Familien getrennt ausgewiesen.
- DPT 20 ohne Untertyp als expliziten numerischen 1-Byte-Aufzählungswert 0–255 ergänzt. Keine automatische Deutung als Heizungsbetriebsart und kein Rückfall unbekannter Untertypen auf einen anderen DPT.
- Eine Hauptnummer zusammen mit genau einem passenden Untertyp im ETS-Export gilt als eindeutige Zuordnung (z. B. DPT-20 plus DPST-20-102). Unterschiedliche Untertypen bleiben mehrdeutig.
- DPT 20.102 zeigt deutsche Betriebsarten mit ursprünglichem Zahlenwert. Bitcodierter HVAC-Status bleibt separat.
- Fehler in ETS- und Alarmmatrix-Validierung korrigiert: vier- und fünfstellige Untertypen bis 65535 werden jetzt angenommen, wenn ein passender Decoder vorhanden ist. Betrifft unter anderem 1.1200, 12.1200 und 20.60102.
- Prüfung aller registrierten DPT in direkter und ETS-Schreibweise sowie Tests für 20, 20.102, abweichenden HVAC-Status, Nutzdatenlänge und Alarm-CSV ergänzt.
- Bereits importierte Zuordnungen bleiben unverändert; für neu erkannte DPT den ETS-Export erneut prüfen und übernehmen.

## 0.10.06 – 21.10.2026

- Dashboard um ETS-Import erweitert: XML-Gruppenadress-Export sowie CSV mit Kopfzeile und Adressspalte auswählen, Vorschau prüfen und anschließend übernehmen.
- Gruppenadresskatalog mit Namen, Beschreibungen und DPT dauerhaft in SQLite speichern; ergänzen/aktualisieren oder nach Bestätigung ersetzen. Vorschau und Katalog mit Suche und Seitenansicht.
- Importierte Zuordnungen für neu empfangene Telegramme sofort verwenden, ohne KNX-Neuverbindung oder Dienstneustart. Alarmregeln werden nicht automatisch erzeugt und behalten ihre konfigurierten DPT.
- Zweistufige und numerische XML-Adressen in dreistufige Adressen normalisieren. Fehlende, mehrdeutige, unbekannte und nicht unterstützte DPT markieren; Rohdaten bleiben sichtbar.
- Größenlimit, XML-DTD-/Entitätensperre, atomare Übernahme, veraltete Vorschauen und geänderte Dateien prüfen. Login-Testmodus bleibt verfügbar; der zeitweise Web-Timeout ist weiterhin ungeklärt.
- Parser, API, Persistenz, Backup und Telegrammdekodierung getestet. Vollständige .knxproj-Dateien werden noch nicht unterstützt.

## 0.10.05 – 21.10.2026

- Einfache „Hallo Welt“-Seite unter `/test/hallo` nur im Testmodus ergänzt, ohne JavaScript und Datenbankzugriff.

- Expliziter Testbetrieb ohne Web-Anmeldung über `KNX_ALARMSERVER_DISABLE_AUTH=1`: Seite, Dateien und API überspringen HTTP-Basic-Auswertung, Benutzerabfrage und Passwortprüfung vollständig.
- Der Testmodus benötigt kein Benutzerkonto; Quittierungen werden als `ohne-anmeldung` gespeichert. Aktionsheader und Herkunftsprüfung bleiben aktiv.
- Anmeldung bleibt standardmäßig eingeschaltet. Bestehende Benutzer und Kennwörter werden nicht gelöscht; Rückkehr durch Entfernen der systemd-Testkonfiguration.
- Tests für Lesezugriffe, KNX-Konfigurationsänderung, Quittierung, ignorierte alte Authorization-Header und weiterhin geschützten Normalbetrieb ergänzt.
- Dient zur Eingrenzung der gemeldeten Timeouts; eine Behebung dieser Ausfälle ist damit noch nicht bestätigt.

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

