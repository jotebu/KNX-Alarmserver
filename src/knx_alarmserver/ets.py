"""Bounded import of ETS group-address exports, never complete project archives."""

import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET

from .dpt import transcoder

MAX_BYTES = 4 * 1024 * 1024
MAX_ADDRESSES = 10000


def address(value):
    parts = str(value).strip().split('/')
    if any(not re.fullmatch(r'[0-9]+', p) for p in parts):
        raise ValueError(f'Ungueltige Gruppenadresse: {value}')
    numbers = list(map(int, parts))
    if len(numbers) == 3 and all(n <= limit for n, limit in zip(numbers, (31, 7, 255))):
        a, b, c = numbers
    elif len(numbers) == 2 and numbers[0] <= 31 and numbers[1] <= 2047:
        a, sub = numbers
        b, c = sub >> 8, sub & 255
    elif len(numbers) == 1 and numbers[0] <= 65535:
        a, b, c = numbers[0] >> 11, (numbers[0] >> 8) & 7, numbers[0] & 255
    else:
        raise ValueError(f'Gruppenadresse ausserhalb KNX-Bereich: {value}')
    return f'{a}/{b}/{c}'


def dpt_number(value):
    value = value.strip()
    match = re.fullmatch(r'DPST-(\d+)-(\d+)', value, re.I)
    if match:
        main, sub = map(int, match.groups())
        if 1 <= main <= 999 and 0 <= sub <= 999:
            return f'{main}.{sub:03d}'
    match = re.fullmatch(r'(?:DPT-)?([1-9][0-9]{0,2})(?:\.([0-9]{1,3}))?', value, re.I)
    if match:
        return str(int(match[1])) + (f'.{int(match[2]):03d}' if match[2] else '')
    raise ValueError('DPT nicht erkannt')


def record(raw_address, name, description='', source=''):
    ga = address(raw_address)
    name, description, source = name.strip(), description.strip(), source.strip()
    if len(name) > 500 or len(description) > 4000 or len(source) > 2000:
        raise ValueError(f'{ga}: Name, Beschreibung oder DPT-Angabe zu lang')
    warnings, candidates = [], []
    invalid = False
    for token in re.split(r'[,;\s]+', source):
        if not token:
            continue
        try:
            number = dpt_number(token)
            if number not in candidates:
                candidates.append(number)
        except ValueError:
            invalid = True
    selected = candidates[0] if len(candidates) == 1 and not invalid else None
    if not source:
        warnings.append('DPT fehlt; Rohwertanzeige')
    elif invalid:
        warnings.append('DPT-Angabe nicht erkannt; Rohwertanzeige')
    elif len(candidates) > 1:
        warnings.append('Mehrere DPT zugeordnet; Rohwertanzeige')
    if selected:
        try:
            transcoder(selected)
        except ValueError:
            warnings.append('DPT nicht unterstuetzt; Rohwertanzeige')
            selected = None
    return {'address': ga, 'name': name or ga, 'description': description,
            'dpt_source': source, 'dpts': candidates, 'dpt': selected, 'warnings': warnings}


def _xml(text):
    # Decode before checking, so UTF-16 cannot bypass the DTD/entity prohibition.
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', text, re.I):
        raise ValueError('XML mit DTD oder Entitaeten wird nicht angenommen')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ValueError(f'Ungueltiges XML: {error}') from None
    if root.tag.split('}')[-1] != 'GroupAddress-Export':
        raise ValueError('ETS-Gruppenadress-Export erwartet, keine Projektdatei')
    for element in root.iter():
        if element.tag.split('}')[-1] == 'GroupAddress':
            yield record(element.get('Address', ''), element.get('Name', ''),
                         element.get('Description', ''), element.get('DPTs', element.get('DatapointType', '')))


def _key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold().replace('ä', 'a').replace('ü', 'u').replace('ö', 'o'))


def _csv(text):
    try:
        dialect = csv.Sniffer().sniff(text[:16384], delimiters=';,\t')
    except csv.Error:
        raise ValueError('CSV-Trennzeichen nicht erkannt; XML oder CSV mit Kopfzeile verwenden') from None
    rows = csv.reader(io.StringIO(text), dialect, strict=True)
    try:
        header = [_key(v) for v in next(rows)]
        def column(*names):
            return next((i for i, name in enumerate(header) if name in names), None)
        ai = column('address', 'groupaddress', 'gruppenadresse', 'adresse')
        if ai is None:
            raise ValueError('CSV-Kopf benoetigt Address/Gruppenadresse; bevorzugt XML exportieren')
        names = [i for i, name in enumerate(header) if name in ('name', 'groupname', 'gruppenname', 'main', 'middle', 'sub', 'hauptgruppe', 'mittelgruppe', 'untergruppe')]
        explicit_name = column('name', 'groupname', 'gruppenname')
        if explicit_name is not None:
            names = [explicit_name]
        if not names:
            raise ValueError('CSV-Kopf benoetigt Name/Group name oder Main/Middle/Sub')
        di = column('dpts', 'dpt', 'datapointtype', 'datapointtypes', 'datenpunkttyp', 'datentyp', 'datapoint')
        ci = column('description', 'beschreibung')
        # ETS 1/3 exports put the three numeric parts in Main, Sub and Address.
        split_style = 'groupname' in header and 'main' in header and 'sub' in header
        for line, values in enumerate(rows, 2):
            if not values or not any(v.strip() for v in values):
                continue
            if len(values) != len(header):
                raise ValueError(f'CSV Zeile {line}: Spaltenanzahl stimmt nicht')
            raw = values[ai].strip()
            if not raw or '-' in raw:
                continue  # ETS hierarchy rows are not group addresses.
            if split_style and '/' not in raw:
                raw = f'{values[header.index("main")]}/{values[header.index("sub")]}/{raw}'
            name = next((values[i] for i in reversed(names) if values[i].strip()), '')
            try:
                yield record(raw, name, values[ci] if ci is not None else '', values[di] if di is not None else '')
            except ValueError as error:
                raise ValueError(f'CSV Zeile {line}: {error}') from None
    except (csv.Error, StopIteration) as error:
        raise ValueError(f'Ungueltige oder leere CSV: {error}') from None


def parse_export(raw, filename):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('Datei leer oder groesser als 4 MiB')
    suffix = filename.rsplit('.', 1)[-1].lower()
    if suffix not in {'xml', 'csv'}:
        raise ValueError('ETS-Gruppenadressen als XML oder CSV exportieren; .knxproj wird noch nicht unterstuetzt')
    try:
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        if suffix == 'xml':
            raise ValueError('XML muss UTF-8 oder UTF-16 mit BOM verwenden') from None
        text = raw.decode('cp1252')
    entries, seen = [], set()
    for item in (_xml(text) if suffix == 'xml' else _csv(text)):
        if item['address'] in seen:
            raise ValueError(f'Doppelte Gruppenadresse {item["address"]}; Export zuerst bereinigen')
        seen.add(item['address'])
        entries.append(item)
        if len(entries) > MAX_ADDRESSES:
            raise ValueError('Maximal 10000 Gruppenadressen pro Datei')
    if not entries:
        raise ValueError('Keine Gruppenadressen im Export gefunden')
    entries.sort(key=lambda e: tuple(map(int, e['address'].split('/'))))
    return {'entries': entries, 'count': len(entries),
            'warnings': sum(bool(e['warnings']) for e in entries),
            'digest': hashlib.sha256(raw).hexdigest()}
