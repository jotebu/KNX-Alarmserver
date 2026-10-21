# DPT-Unterstützung

Stand: 21.10.2026. Der Alarmserver verwendet xknx 4.0.0 plus den expliziten lokalen Zahlendecoder für die Hauptnummer 20. Der Laufzeitkatalog enthält 231 Einträge in 30 Familien: 219 konkrete Untertypen und 12 numerische/binäre Hauptnummern. Ein vorhandener Decoder bedeutet nicht, dass alle Untertypen seiner Familie implementiert sind.

## Hauptnummern und Untertypen

Direkt ohne Untertyp unterstützt: **1, 2, 5, 6, 7, 8, 9, 12, 13, 14, 20, 29**.

Familien mit mindestens einem konkreten Decoder: **1–14, 16–20, 29, 232, 235, 242, 243, 249–254**. In diesen Bereichen sind einzelne Untertypen verfügbar; die genaue Liste liefert `knx-alarmserver dpt-list` beziehungsweise die API `/api/dpts`. Hauptnummern anderer Familien werden nicht automatisch auf einen vermeintlich passenden Untertyp abgebildet.

| Angabe | Verhalten |
| --- | --- |
| `20` / `DPT-20` | Ein Byte als Zahl 0–255; keine Betriebsart geraten. Importhinweis weist auf fehlenden Untertyp hin. |
| `20.102` / `DPST-20-102` | Automatik (0), Komfort (1), Standby (2), Sparbetrieb / Nacht (3), Schutzbetrieb (4). Reservierte Werte werden vom spezifischen Decoder abgewiesen. |
| `20.105` | HVAC-Reglerbetriebsart entsprechend xknx. |
| `20.60102` | Von xknx angebotener, nicht standardisierter HVAC-Status mit Bitfeldern. Nicht mit `20.102` verwechseln. |
| Beispielsweise `20.001`, `20.003`, `20.103` | Noch kein spezifischer Decoder; der ETS-Import erhält die originale Angabe und zeigt Rohdaten. Kein stiller Rückfall auf `20` oder `20.102`. |

Eine Hauptnummer zusammen mit genau einem passenden Untertyp, etwa `DPT-20,DPST-20-102`, wird auf den ausdrücklich vorhandenen Untertyp normalisiert. Zwei unterschiedliche Untertypen bleiben mehrdeutig; ein nicht unterstützter Untertyp wird nicht auf die ebenfalls genannte Hauptnummer zurückgesetzt.

DPT 20 ist eine 8-Bit-Aufzählung (KNX-Bezeichnung N8). Die numerische Grunddarstellung und die Semantik eines Untertyps sind getrennt. Die allgemeinen Werte 0–255 sind keine Zusage, dass jeder Wert für jeden Untertyp gültig ist.

## Abgleich mit der veröffentlichten KNX-Übersicht

Referenz ist die öffentlich bereitgestellte **KNX-DPT-Spezifikation v02.02.01 (2021), Übersicht Seiten 17–25**. Der Abgleich ist keine Aussage über sämtliche späteren Ergänzungen oder herstellerspezifischen Typen.

Vollständig ohne spezifischen Decoder sind dort folgende Familien:

| Bereich | Noch nicht implementierte Familien |
| --- | --- |
| Unter 100 | 15, 21–28, 30–31 |
| 200–231 | 200–207, 209–225, 229–231 |
| 234–248 | 234, 236–241, 244–248 |
| Ab 255 | 255–257, 265–274, 276–284 |

In bereits teilweise unterstützten Familien fehlen gegenüber dieser Übersicht außerdem:

- **6.020**.
- **DPT 20:** 20.001–20.008, 20.011–20.014, 20.017, 20.020–20.022, 20.100–20.101, 20.103–20.104, 20.106–20.115, 20.120–20.122, 20.600–20.613, 20.801–20.804, 20.1000–20.1005, 20.1200, 20.1202–20.1209. Die spezifischen Standarddecoder 20.102 und 20.105 sind vorhanden.

Praktisch wichtige Ausbaubereiche sind Status-/Bitfelder (21/22), Szeneninformationen (26/27), UTF-8-Text (28) und zusammengesetzte Mess-/Reglerdaten (etwa 222). Zusätzlich ist die Familie 275 aus weiteren HVAC-Erweiterungen noch nicht implementiert; sie gehört nicht zur oben genannten Übersicht. Ein Update der Bibliothek wird erst nach Prüfung freigegebener Versionen und Regressionstests vorgenommen, nicht anhand einer noch unveröffentlichten Änderungsliste.

## Gefundene Importbeschränkung

Der bisherige Import akzeptierte höchstens dreistellige Untertypen. Dadurch wurden zehn bereits vorhandene Decoder fälschlich nicht erkannt:

**1.1200, 1.1201, 9.60000, 12.1200, 12.1201, 13.1200, 13.1201, 14.1200, 14.1201, 20.60102.**

Import und Alarmmatrix akzeptieren jetzt Untertypen bis 65535; die tatsächliche Decoderverfügbarkeit bleibt separat geprüft. Alle 231 Katalogeinträge werden in direkter und ETS-Schreibweise getestet. Ein gültiges Zahlenformat allein macht einen unbekannten Untertyp nicht unterstützt.

Bestehende ETS-Einträge werden beim Update nicht umgedeutet. Für die neu erkannten Zuordnungen den Export im Dashboard erneut prüfen und übernehmen. Der Katalog kann ergänzt werden; ein Löschen vorhandener Verbindungen oder Alarme ist nicht nötig.

## Quellen

- [KNX Association: veröffentlichte DPT-Spezifikation](https://support.knx.org/hc/en-us/articles/15392604906514-Interworking-Datapoint-types)
- [MDT: Unterschied HVAC Mode / HVAC Status](https://www.mdt.de/download/MDT_LSG_Visualisierung_des_HVAC_Status.pdf)
- Installierter xknx-4.0.0-Katalog und ausführbare Projektprüfungen.
- [xknx: Entwicklungsstand und Änderungsübersicht](https://github.com/XKNX/xknx/blob/main/docs/changelog.md)
