import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from knx_alarmserver.license_protocol import (
    DOMAIN, LicenseError, b64, canonical, key_id, make_request, public_document,
    read_public, read_request, request_hash, unb64, verify_license,
)
from knx_alarmserver.licensing import LicenseManager, device_fingerprint, install_public_key, read_key_file
from knx_alarmserver.store import Store
from test_core import ALARM

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/license-v1.json').read_text())
DEVICE = 'sha256:' + 'a' * 64
EMAIL = 'kunde@example.de'


def test_token(key, email=EMAIL, device=DEVICE):
    import uuid
    request = read_request(make_request(email, device))
    payload = dict(request, plan='lifetime', license_id=str(uuid.uuid4()),
                   issued_at='2026-10-23T09:00:00Z', key_id=key_id(key.public_key()),
                   request_hash=request_hash(request))
    raw = canonical(payload)
    return 'ASKLIC1.' + b64(raw) + '.' + b64(key.sign(DOMAIN + raw))


class LicensingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / 'store.sqlite3'
        self.store = Store(self.database, [ALARM])
        self.key = Ed25519PrivateKey.generate()
        self.key_file = self.root / 'keys.json'
        self.key_file.write_text(json.dumps({'keys': [public_document(self.key.public_key())]}))
        self.manager = LicenseManager(self.store, self.key_file, lambda: (DEVICE, 'rpi-serial'), bundled_keys=None)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_generator_fixture_matches_server_protocol(self):
        public = read_public(FIXTURE['public'])
        self.assertEqual(make_request(EMAIL, DEVICE), FIXTURE['request'])
        license = verify_license(FIXTURE['license'], {key_id(public): public}, email=EMAIL, device=DEVICE)
        self.assertEqual(license['plan'], 'lifetime')

    def test_uploaded_public_key_is_bundled_and_valid(self):
        from knx_alarmserver.licensing import BUNDLED_KEYS
        keys = read_key_file(BUNDLED_KEYS)
        self.assertIn('cb3bb009da270f7e38bb4c04ae947c29', keys)

    def test_trial_is_seven_days_and_updates_do_not_reset_it(self):
        from datetime import datetime, timedelta
        start = datetime.fromisoformat(self.manager.status()['trial_started_at'])
        self.manager.clock = lambda: start
        self.assertEqual(self.manager.status()['trial_days_remaining'], 7)
        self.manager.clock = lambda: start + timedelta(days=6, hours=23)
        self.assertEqual(self.manager.status()['trial_days_remaining'], 1)
        self.assertTrue(self.manager.status()['trial_active'])
        self.manager.clock = lambda: start + timedelta(days=7)
        self.assertFalse(self.manager.status()['trial_active'])
        self.assertEqual(self.manager.status()['state'], 'expired')
        restarted = LicenseManager(self.store, self.key_file, self.manager.fingerprint,
                                   bundled_keys=None, clock=self.manager.clock)
        self.assertEqual(restarted.status()['trial_started_at'], start.isoformat())
        self.assertFalse(restarted.status()['trial_active'])
        self.assertTrue(restarted.activate(EMAIL, test_token(self.key))['licensed'])

    def test_corrupt_trial_is_not_restarted(self):
        with self.store.transaction():
            self.store.db.execute("UPDATE settings SET value='invalid' WHERE name='license_trial'")
        restarted = LicenseManager(self.store, self.key_file, self.manager.fingerprint, bundled_keys=None)
        state = restarted.status()
        self.assertFalse(state['trial_active'])
        self.assertIsNotNone(state['trial_error'])
        self.assertFalse(state['enforcement_enabled'])

    def test_request_normalization_and_invalid_email(self):
        result = self.manager.request(' Kunde@EXAMPLE.DE ')
        self.assertEqual(result['request_code'], make_request(EMAIL, DEVICE))
        self.assertEqual(result['email'], EMAIL)
        with self.assertRaises(LicenseError):
            self.manager.request('not an email')

    def test_activation_persists_and_is_idempotent(self):
        code = test_token(self.key)
        result = self.manager.activate(EMAIL, code)
        self.assertTrue(result['licensed'])
        self.assertFalse(result['enforcement_enabled'])
        self.assertEqual(self.manager.activate(EMAIL, code)['activated_at'], result['activated_at'])
        self.store.close()
        self.store = Store(self.database, [ALARM])
        restarted = LicenseManager(self.store, self.key_file, lambda: (DEVICE, 'rpi-serial'), bundled_keys=None)
        self.assertEqual(restarted.status()['license_id'], result['license_id'])

    def test_bad_signature_identity_or_key_never_replaces_valid_license(self):
        code = test_token(self.key)
        valid = self.manager.activate(EMAIL, code)
        body, signature = code.rsplit('.', 1)
        corrupted = bytearray(unb64(signature))
        corrupted[0] ^= 1
        changed = body + '.' + b64(corrupted)
        for email, token in ((EMAIL, changed), ('other@example.de', code),
                             (EMAIL, test_token(self.key, device='sha256:' + 'b' * 64)),
                             (EMAIL, test_token(Ed25519PrivateKey.generate())), (EMAIL, None)):
            with self.subTest(email=email, code=str(token)[-15:]), self.assertRaises(LicenseError):
                self.manager.activate(email, token)
            self.assertEqual(self.manager.status()['license_id'], valid['license_id'])

    def test_changed_hardware_invalidates_saved_license(self):
        self.manager.activate(EMAIL, test_token(self.key))
        self.manager.fingerprint = lambda: ('sha256:' + 'b' * 64, 'rpi-serial')
        self.assertEqual(self.manager.status()['state'], 'invalid')

    def test_missing_or_invalid_keys_leave_request_available(self):
        self.key_file.unlink()
        self.assertEqual(self.manager.status()['trusted_keys'], 0)
        self.assertTrue(self.manager.request(EMAIL)['request_code'])
        with self.assertRaises(LicenseError):
            self.manager.activate(EMAIL, test_token(self.key))
        self.key_file.write_text('{bad json')
        state = self.manager.status()
        self.assertIsNotNone(state['key_error'])
        self.assertFalse(state['licensed'])

    def test_unavailable_device_does_not_affect_alarms(self):
        self.manager.fingerprint = lambda: (_ for _ in ()).throw(LicenseError('Keine Gerätekennung'))
        self.assertIsNotNone(self.manager.status()['device_error'])
        with self.assertRaises(LicenseError):
            self.manager.request(EMAIL)
        self.store.ingest(ALARM.group_address, 1, '1.1.1')
        self.assertEqual(self.store.snapshot()[0]['status'], 'active')

    def test_hardware_fingerprint_prefers_serial_and_hides_raw_value(self):
        import io
        def read(path, *args, **kwargs):
            values = {'/proc/device-tree/serial-number': b'10000000abcdef12\x00',
                      '/etc/machine-id': b'0123456789abcdef0123456789abcdef\n'}
            if str(path) not in values:
                raise FileNotFoundError()
            return io.BytesIO(values[str(path)])
        with patch.object(Path, 'open', read):
            value, source = device_fingerprint()
        expected = hashlib.sha256(b'ASK-DEVICE-v1\x00rpi-serial\x0010000000abcdef12').hexdigest()
        self.assertEqual(value, 'sha256:' + expected)
        self.assertEqual(source, 'rpi-serial')
        self.assertNotIn('10000000abcdef12', value)

    def test_hardware_fingerprint_fallback_and_failure(self):
        import io
        def read(path, *args, **kwargs):
            if str(path) == '/etc/machine-id':
                return io.BytesIO(b'0123456789abcdef0123456789abcdef\n')
            raise PermissionError()
        with patch.object(Path, 'open', read):
            first = device_fingerprint()
            self.assertEqual(first, device_fingerprint())
        self.assertEqual(first[1], 'machine-id')
        with patch.object(Path, 'open', side_effect=FileNotFoundError()), self.assertRaises(LicenseError):
            device_fingerprint()

    def test_public_key_install_requires_root_and_preserves_old_keys(self):
        source = self.root / 'public.json'
        source.write_text(json.dumps(FIXTURE['public']))
        with patch('os.geteuid', return_value=1000), self.assertRaises(LicenseError):
            install_public_key(source, self.key_file)
        with patch('os.geteuid', return_value=0):
            installed = install_public_key(source, self.key_file)
            self.assertEqual(installed, FIXTURE['public']['key_id'])
            self.assertEqual(install_public_key(source, self.key_file), installed)
        self.assertEqual(len(read_key_file(self.key_file)), 2)
        source.write_text('-----BEGIN PRIVATE KEY-----')
        with patch('os.geteuid', return_value=0), self.assertRaises(LicenseError):
            install_public_key(source, self.key_file)
        self.assertEqual(len(read_key_file(self.key_file)), 2)


class LicenseApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(':memory:', [ALARM])
        self.store.set_password('admin', 'test-password-123', 'admin')
        self.store.set_password('user', 'test-password-123', 'user')
        self.store.set_password('viewer', 'test-password-123', 'viewer')
        public = self.root = Path(self.temp.name) / 'keys.json'
        public.write_text(json.dumps({'keys': [FIXTURE['public']]}))
        manager = LicenseManager(self.store, public, lambda: (DEVICE, 'rpi-serial'), bundled_keys=None)
        self.client = TestClient(create_app({'knx': {'enabled': False}}, self.store, license_manager=manager))
        self.client.__enter__()
        self.headers = {'X-Alarmserver-Action': 'manage-license'}
        self.auth = ('admin', 'test-password-123')

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.close()
        self.temp.cleanup()

    def test_all_license_operations_require_authentication(self):
        self.assertEqual(self.client.get('/api/license').status_code, 401)
        self.assertEqual(self.client.get('/license').status_code, 401)
        self.assertIn('/static/login.js', self.client.get('/license').text)
        self.assertEqual(self.client.post('/api/license/request', json={'email': EMAIL}).status_code, 401)

    def test_viewers_and_users_can_only_read_license_info(self):
        for role in ('user', 'viewer'):
            auth = (role, 'test-password-123')
            self.assertEqual(self.client.get('/license', auth=auth).status_code, 200)
            self.assertEqual(self.client.get('/api/license', auth=auth).status_code, 200)
            for path, payload in (('request', {'email': EMAIL}), ('activate', {'email': EMAIL, 'code': FIXTURE['license']})):
                self.assertEqual(self.client.post('/api/license/' + path, auth=auth, headers=self.headers, json=payload).status_code, 403)

    def test_csrf_schema_and_size_limits(self):
        path = '/api/license/request'
        for headers in ({}, dict(self.headers, Origin='https://foreign.invalid'), dict(self.headers, **{'Sec-Fetch-Site': 'cross-site'})):
            self.assertEqual(self.client.post(path, auth=self.auth, headers=headers, json={'email': EMAIL}).status_code, 403)
        for payload in ({}, {'email': EMAIL, 'keys': []}, {'email': None}):
            self.assertEqual(self.client.post(path, auth=self.auth, headers=self.headers, json=payload).status_code, 422)
        self.assertEqual(self.client.post(path, auth=self.auth, headers=self.headers, content='x' * 8193).status_code, 413)

    def test_generator_request_and_activation_end_to_end(self):
        result = self.client.post('/api/license/request', auth=self.auth, headers=self.headers, json={'email': EMAIL})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['request_code'], FIXTURE['request'])
        activated = self.client.post('/api/license/activate', auth=self.auth, headers=self.headers,
                                     json={'email': EMAIL, 'code': FIXTURE['license']})
        self.assertEqual(activated.status_code, 200)
        self.assertTrue(activated.json()['licensed'])
        state = self.client.get('/api/license', auth=self.auth).json()
        self.assertNotIn('code', state)
        self.assertEqual(state['license_email'], EMAIL)
        self.assertFalse(state['enforcement_enabled'])

    def test_license_file_import_uses_signed_email_and_keeps_valid_license_on_errors(self):
        path = '/api/license/import'
        response = self.client.post(path, auth=self.auth, headers=self.headers,
                                    content=('\ufeff' + FIXTURE['license'] + '\n').encode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['license_email'], EMAIL)
        original_id = response.json()['license_id']
        for raw, expected in ((b'', 422), (b'\xff\xfe', 422), (b'bad', 422), (b'x' * 8193, 413)):
            result = self.client.post(path, auth=self.auth, headers=self.headers, content=raw)
            self.assertEqual(result.status_code, expected)
            self.assertEqual(self.client.get('/api/license', auth=self.auth).json()['license_id'], original_id)

    def test_license_file_import_requires_admin_and_origin_protection(self):
        for role in ('user', 'viewer'):
            result = self.client.post('/api/license/import', auth=(role, 'test-password-123'),
                                      headers=self.headers, content=FIXTURE['license'])
            self.assertEqual(result.status_code, 403)
        self.assertEqual(self.client.post('/api/license/import', auth=self.auth, content=FIXTURE['license']).status_code, 403)


if __name__ == '__main__':
    unittest.main()
