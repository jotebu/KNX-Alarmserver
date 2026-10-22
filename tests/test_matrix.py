from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from knx_alarmserver.store import Store
from knx_alarmserver.matrix import editable, example_csv, parse_csv, MatrixConflict
from test_core import ALARM


def fresh(address='2/1/1'):
    row = editable(ALARM)
    row.update(id='', name='Neuer Alarm', group_address=address)
    return row


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'matrix.sqlite3'
        self.store = Store(self.path, [ALARM])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def save(self, rows, append=False):
        return self.store.save_matrix(rows, self.store.matrix()['revision'], 'editor', append)

    def test_automatic_ids_live_evaluation_and_restart(self):
        rows = self.save([fresh()])['rows']
        identifier = rows[0]['id']
        self.assertRegex(identifier, r'^alarm-[0-9]+$')
        self.store.ingest('2/1/1', 1, '1.1.1')
        self.assertEqual(self.store.snapshot()[0]['status'], 'active')
        self.store.close()
        self.store = Store(self.path, [ALARM])
        self.assertEqual(self.store.matrix()['rows'][0]['id'], identifier)
        self.assertEqual(self.store.snapshot()[0]['status'], 'active')
        self.assertFalse(self.store.snapshot()[0]['fresh'])
        self.assertNotIn('pump', self.store.alarms)

    def test_edit_resets_only_rule_state_and_preserves_history(self):
        self.store.ingest(ALARM.group_address, 1, '1.1.1')
        row = self.store.matrix()['rows'][0]
        row['name'] = 'Neuer Name'
        self.save([row])
        self.assertEqual(self.store.snapshot()[0]['status'], 'active')
        row['threshold'] = 'false'
        self.save([row])
        self.assertEqual(self.store.snapshot()[0]['status'], 'unknown')
        self.assertTrue(any(e['kind'] == 'active' for e in self.store.history()))
        self.assertTrue(any(e['kind'] == 'matrix_updated' and e['username'] == 'editor' for e in self.store.history()))
        self.store.close()
        self.store = Store(self.path, [ALARM])
        self.assertEqual(self.store.alarms['pump'].threshold, False)

    def test_stale_revision_duplicate_address_and_invalid_dpt_are_atomic(self):
        initial = self.store.matrix()
        for rows in [[fresh('1/2/3'), editable(ALARM)], [{**fresh(), 'dpt': '999.001'}], [{**fresh(), 'id': 'chosen-id'}]]:
            with self.assertRaises(ValueError):
                self.save(rows)
            self.assertEqual(self.store.matrix(), initial)
        self.save([fresh()])
        with self.assertRaises(MatrixConflict):
            self.store.save_matrix([], initial['revision'], 'other')
        self.assertEqual(len(self.store.alarms), 1)

    def test_csv_roundtrip_append_and_no_id_reuse(self):
        self.save(parse_csv(example_csv().encode()), append=True)
        self.assertEqual(len(self.store.alarms), 3)
        ids = set(self.store.alarms)
        self.save([])
        self.assertFalse(self.store.snapshot())
        self.save([fresh()])
        self.assertFalse(set(self.store.alarms) & ids)
        with self.assertRaises(ValueError):
            parse_csv(b'id;name\nchosen;test\n')
        with self.assertRaises(ValueError):
            parse_csv(b'')

    def test_effective_matrix_and_backup_include_dashboard_changes(self):
        from knx_alarmserver.config import load_configured_alarms
        self.save([fresh()])
        config = {'server': {'database': str(self.path), 'alarms': str(self.path.parent / 'missing.csv')}}
        self.assertEqual(load_configured_alarms(config), list(self.store.alarms.values()))
        target = self.path.parent / 'backup.sqlite3'
        self.store.backup(target)
        restored = Store(target, [ALARM])
        try:
            self.assertEqual(restored.matrix(), self.store.matrix())
        finally:
            restored.close()

    def test_simultaneous_editors_cannot_overwrite_each_other(self):
        from concurrent.futures import ThreadPoolExecutor
        revision = self.store.matrix()['revision']
        def save(address):
            try:
                self.store.save_matrix([fresh(address)], revision, 'editor')
                return 'saved'
            except MatrixConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, ['2/1/1', '2/1/2']))
        self.assertCountEqual(results, ['saved', 'conflict'])

    def test_database_failure_keeps_live_matrix_and_saved_state(self):
        initial = self.store.matrix()
        with patch.object(self.store, '_event', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.save([fresh()])
        self.assertEqual(self.store.matrix(), initial)
        self.assertIsNone(self.store.db.execute("SELECT value FROM settings WHERE name='alarm_matrix'").fetchone())


class MatrixWebTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        self.store = Store(':memory:', [])
        for role in ['admin', 'user', 'viewer']:
            self.store.set_password(role, 'test-password-123', role)
        self.client = TestClient(create_app({'knx': {'enabled': False}}, self.store))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.close()

    def test_roles_csrf_import_example_and_conflict(self):
        for role in ['admin', 'user', 'viewer']:
            auth=(role, 'test-password-123')
            for path in ['/matrix','/api/matrix','/api/matrix/example.csv','/api/matrix/export.csv']:
                self.assertEqual(self.client.get(path, auth=auth).status_code, 403 if role=='viewer' else 200, (role,path))
            payload={'rows':[fresh()], 'revision':self.store.matrix()['revision']}
            response=self.client.put('/api/matrix', auth=auth, headers={'X-Alarmserver-Action':'manage-matrix'}, json=payload)
            self.assertEqual(response.status_code, 403 if role=='viewer' else 200)
            if role!='viewer':
                self.assertEqual(self.client.put('/api/matrix', auth=auth, headers={'X-Alarmserver-Action':'manage-matrix'}, json=payload).status_code,409)
        auth=('user','test-password-123')
        payload={'rows':[], 'revision':self.store.matrix()['revision']}
        self.assertEqual(self.client.put('/api/matrix',auth=auth,json=payload).status_code,403)
        self.assertEqual(self.client.put('/api/matrix',auth=auth,json=payload,headers={'X-Alarmserver-Action':'manage-matrix','Origin':'http://foreign'}).status_code,403)
        sample=self.client.get('/api/matrix/example.csv',auth=auth)
        self.assertIn('attachment',sample.headers['content-disposition'])
        response=self.client.post('/api/matrix/import',auth=auth,headers={'X-Alarmserver-Action':'manage-matrix'},json={'csv':sample.text,'revision':self.store.matrix()['revision']})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(response.json()['rows']),3)
        before=self.store.matrix()
        duplicate=self.client.post('/api/matrix/import',auth=auth,headers={'X-Alarmserver-Action':'manage-matrix'},json={'csv':sample.text,'revision':before['revision']})
        self.assertEqual(duplicate.status_code,422)
        self.assertEqual(self.store.matrix(),before)
        self.assertEqual(self.client.get('/api/matrix').status_code,401)
        self.assertEqual(self.client.post('/api/matrix/import',auth=('viewer','test-password-123'),headers={'X-Alarmserver-Action':'manage-matrix'},json={}).status_code,403)
