"""Stable numeric alarm priorities; display labels remain freely configurable."""
DEFAULTS = [{'priority': 1, 'name': 'Brand'}, {'priority': 2, 'name': 'Warnung'},
            {'priority': 3, 'name': 'Service'}, {'priority': 4, 'name': 'Info'}]
LEGACY = {'critical': 1, 'warning': 2, 'info': 4}


def number(value):
    if isinstance(value, str):
        value = LEGACY.get(value, value)
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            value = int(value)
    if type(value) is not int or not 1 <= value <= 999:
        raise ValueError('Prioritaet muss eine ganze Zahl von 1 bis 999 sein')
    return value


def validate(entries):
    if not isinstance(entries, list) or not 1 <= len(entries) <= 999:
        raise ValueError('Mindestens eine und maximal 999 Prioritaeten erforderlich')
    result, seen = [], set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != {'priority', 'name'}:
            raise ValueError('Prioritaet und Bezeichnung erforderlich')
        if type(row['priority']) is not int:
            raise ValueError('Prioritaetsnummer als ganze Zahl angeben')
        identifier = number(row['priority'])
        name = row['name']
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Bezeichnung mit 1 bis 80 Zeichen erforderlich')
        if identifier in seen:
            raise ValueError('Doppelte Prioritaetsnummer')
        seen.add(identifier)
        result.append({'priority': identifier, 'name': name.strip()})
    return sorted(result, key=lambda row: row['priority'])
