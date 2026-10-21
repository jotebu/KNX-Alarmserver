"""One shared validator and CSV format for interactive and imported alarm rows."""
import csv
from dataclasses import asdict
import io
import json

from .config import Alarm, parse_alarms
from .dpt import transcoder

FIELDS = [name for name in Alarm.__dataclass_fields__ if name != 'id']
MAX_ROWS = 5000
MAX_BYTES = 2 * 1024 * 1024


class MatrixConflict(ValueError):
    pass


def editable(alarm):
    row = asdict(alarm)
    row['threshold'] = json.dumps(alarm.threshold, ensure_ascii=False, allow_nan=False)
    row['hysteresis'] = str(alarm.hysteresis)
    row['priority'] = str(alarm.priority)
    return row


def validate_rows(rows):
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError('Maximal 5000 Alarme erlaubt')
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=['id', *FIELDS], delimiter=';')
    writer.writeheader()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', *FIELDS}:
            raise ValueError('Alle Alarmspalten erforderlich; keine unbekannten Felder erlaubt')
        if any(not isinstance(value, str) or len(value) > 2048 for value in row.values()):
            raise ValueError('Alarmfelder als Text mit maximal 2048 Zeichen angeben')
        writer.writerow(row)
    handle.seek(0)
    alarms = parse_alarms(handle)
    for alarm in alarms:
        transcoder(alarm.dpt)
    return alarms


def parse_csv(raw):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), delimiter=';', strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(FIELDS) or set(reader.fieldnames) != set(FIELDS):
            raise ValueError('CSV-Kopf erwartet: ' + ';'.join(FIELDS) + ' (ohne ID)')
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'CSV Zeile {reader.line_num}: Spaltenanzahl stimmt nicht')
            rows.append({**row, 'id': ''})
            if len(rows) > MAX_ROWS:
                raise ValueError('Maximal 5000 CSV-Zeilen erlaubt')
        if not rows:
            raise ValueError('CSV enthaelt keine Alarme')
        return rows
    except (UnicodeError, csv.Error) as error:
        raise ValueError('Gueltige UTF-8-CSV mit Semikolon erforderlich') from error


def csv_text(rows):
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def example_csv(priority=2):
    return csv_text([
        dict(zip(FIELDS, ['Beispiel Pumpenstoerung', '31/7/250', '1.005', 'eq', 'true', '0', '', 'Technik', str(priority)])),
        dict(zip(FIELDS, ['Beispiel Uebertemperatur', '31/7/251', '9.001', 'gt', '50', '2', '', 'Technik', str(priority)])),
    ])
