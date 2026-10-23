"""Offline-Lizenzierung. Die Laufzeitbegrenzung bleibt bis zur Abnahme deaktiviert."""
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .license_protocol import LicenseError, make_request, normalize_email, read_public, verify_license

KEY_FILE = Path('/etc/knx-alarmserver/license-keys.json')
BUNDLED_KEYS = Path(__file__).with_name('license-keys.json')
MAX_KEY_BYTES = 65536


def device_fingerprint():
    # Keine MAC/IP/Hostname: Änderungen am Netz ändern die Lizenzidentität nicht.
    sources = (
        ('rpi-serial', Path('/proc/device-tree/serial-number')),
        ('rpi-serial', Path('/sys/firmware/devicetree/base/serial-number')),
        ('dmi-uuid', Path('/sys/class/dmi/id/product_uuid')),
        ('machine-id', Path('/etc/machine-id')),
    )
    for kind, path in sources:
        try:
            with path.open('rb') as handle:
                value = handle.read(257).decode('ascii').strip('\x00\r\n\t ').lower()
        except (OSError, UnicodeError):
            continue
        if (not 8 <= len(value) <= 128 or not re.fullmatch('[0-9a-f-]+', value)
                or not set(value) - {'0', '-', 'f'}):
            continue
        digest = hashlib.sha256(('ASK-DEVICE-v1\x00' + kind + '\x00' + value).encode('ascii')).hexdigest()
        return 'sha256:' + digest, kind
    raise LicenseError('Keine stabile Gerätekennung lesbar. Lizenzanfrage nicht möglich.')


def read_key_file(path=KEY_FILE):
    path = Path(path)
    if not path.exists():
        return {}
    with path.open('rb') as handle:
        raw = handle.read(MAX_KEY_BYTES + 1)
    if len(raw) > MAX_KEY_BYTES:
        raise LicenseError('Prüfschlüsseldatei ist zu groß.')
    try:
        document = json.loads(raw)
        if (not isinstance(document, dict) or set(document) != {'keys'}
                or not isinstance(document['keys'], list) or len(document['keys']) > 32):
            raise LicenseError('Ungültige Prüfschlüsseldatei.')
        keys = {}
        for entry in document['keys']:
            key = read_public(entry)
            if entry['key_id'] in keys:
                raise LicenseError('Doppelte Prüfschlüsselkennung.')
            keys[entry['key_id']] = key
        return keys
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise LicenseError('Ungültige Prüfschlüsseldatei.') from exc


def install_public_key(source, destination=KEY_FILE):
    if os.geteuid() != 0:
        raise LicenseError('Prüfschlüssel müssen mit sudo installiert werden.')
    with Path(source).open('rb') as handle:
        raw = handle.read(8193)
    if len(raw) > 8192:
        raise LicenseError('Öffentlicher Schlüssel ist zu groß.')
    try:
        document = json.loads(raw)
        read_public(document)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise LicenseError('Exportierten öffentlichen JSON-Schlüssel verwenden, keinen privaten Schlüssel.') from exc
    destination = Path(destination)
    existing = read_key_file(destination)
    if document['key_id'] in existing:
        return document['key_id']
    if len(existing) >= 32:
        raise LicenseError('Höchstens 32 öffentliche Prüfschlüssel erlaubt.')
    from .license_protocol import public_document
    entries = [public_document(key) for key in existing.values()] + [document]
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.license-keys-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump({'keys': entries}, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o644)
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)
    return document['key_id']


class LicenseManager:
    def __init__(self, store, key_file=KEY_FILE, fingerprint=device_fingerprint, bundled_keys=BUNDLED_KEYS):
        self.store = store
        self.key_file = key_file
        self.fingerprint = fingerprint
        self.bundled_keys = bundled_keys

    def keys(self):
        try:
            keys = read_key_file(self.bundled_keys) if self.bundled_keys is not None else {}
            keys.update(read_key_file(self.key_file))
            return keys, None
        except (OSError, LicenseError):
            logging.getLogger(__name__).warning('Öffentliche Lizenzprüfschlüssel nicht lesbar oder ungültig')
            return {}, 'Prüfschlüsseldatei nicht lesbar oder ungültig.'

    def status(self):
        keys, key_error = self.keys()
        result = {'state': 'unlicensed', 'licensed': False, 'enforcement_enabled': False,
                  'trusted_keys': len(keys), 'key_error': key_error,
                  'device': None, 'device_source': None, 'device_error': None,
                  'license_email': None, 'license_id': None, 'issued_at': None,
                  'activated_at': None, 'error': None}
        try:
            device, source = self.fingerprint()
            result.update(device=device, device_source=source)
        except LicenseError as exc:
            result['device_error'] = str(exc)
            device = None
        with self.store.lock:
            row = self.store.db.execute("SELECT value FROM settings WHERE name='license'").fetchone()
        if not row:
            return result
        try:
            saved = json.loads(row['value'])
            if device is None:
                raise LicenseError('Lizenz kann ohne Gerätekennung nicht geprüft werden.')
            data = verify_license(saved['code'], keys, device=device)
            result.update(state='licensed', licensed=True, license_email=data['email'],
                          license_id=data['license_id'], issued_at=data['issued_at'],
                          activated_at=saved['activated_at'])
        except (ValueError, KeyError, TypeError, RecursionError):
            result.update(state='invalid', error='Gespeicherte Lizenz konnte für diesen Server nicht bestätigt werden.')
        return result

    def request(self, email):
        device, source = self.fingerprint()
        code = make_request(email, device)
        return {'request_code': code, 'email': normalize_email(email), 'device': device, 'device_source': source}

    def activate(self, email, code):
        keys, error = self.keys()
        if error or not keys:
            raise LicenseError('Noch kein gültiger öffentlicher Prüfschlüssel installiert. Bitte Anbieter kontaktieren.')
        device, _ = self.fingerprint()
        verify_license(code, keys, email=email, device=device)
        with self.store.transaction():
            # Fehlversuche verändern eine vorhandene gültige Aktivierung nicht.
            row = self.store.db.execute("SELECT value FROM settings WHERE name='license'").fetchone()
            try:
                previous = json.loads(row['value']) if row else {}
                if not isinstance(previous, dict):
                    previous = {}
            except (ValueError, RecursionError):
                previous = {}
            saved = previous if previous.get('code') == code.strip() else {
                'code': code.strip(), 'activated_at': datetime.now(timezone.utc).isoformat()}
            self.store.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('license',?)",
                                  (json.dumps(saved),))
        return self.status()
