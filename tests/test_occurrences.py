from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sqlite3
import unittest

from knx_alarmserver.store import Store
from test_core import ALARM


class OccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:', [ALARM])

    def tearDown(self):
        self.store.close()

    def ingest(self, value, timestamp):
        with patch('knx_alarmserver.store.now', return_value=timestamp):
            return self.store.ingest(ALARM.group_address, value, '1.1.1')

    def ack(self, identifier, username, timestamp):
        with patch('knx_alarmserver.store.now', return_value=timestamp):
            return self.store.acknowledge_occurrence(identifier, username)

    def test_cycle_has_three_independent_timestamps_and_immutable_ack(self):
        self.ingest(0, '2026-10-21T09:00:00+00:00')
        self.assertEqual(self.store.occurrence_list('all')['total'], 0)
        self.ingest(1, '2026-10-21T10:00:00+00:00')
        row = self.store.occurrence_list()['rows'][0]
        identifier = row['occurrence_id']
        self.assertFalse(self.ingest(1, '2026-10-21T10:05:00+00:00'))
        self.ack(identifier, 'andy', '2026-10-21T10:06:00+00:00')
        self.assertFalse(self.ack(identifier, 'other', '2026-10-21T10:07:00+00:00'))
        self.ingest(0, '2026-10-21T10:10:00+00:00')
        self.assertEqual(self.store.occurrence_list()['total'], 0)
        final = self.store.occurrence_list('closed')['rows'][0]
        self.assertEqual(final['came_at'], '2026-10-21T10:00:00+00:00')
        self.assertEqual(final['acknowledged_at'], '2026-10-21T10:06:00+00:00')
        self.assertEqual(final['acknowledged_by'], 'andy')
        self.assertEqual(final['went_at'], '2026-10-21T10:10:00+00:00')
        self.assertEqual(final['status'], 'closed')
        self.assertEqual(self.store.occurrence_counts()['closed'], 1)
        self.assertEqual(len([e for e in self.store.history() if e['occurrence_id'] == identifier]), 3)

    def test_repeat_after_clear_creates_new_cycle_and_ack_does_not_cross_cycles(self):
        self.ingest(1, '2026-10-21T10:00:00+00:00')
        first = self.store.occurrence_list()['rows'][0]['occurrence_id']
        self.ingest(0, '2026-10-21T10:10:00+00:00')
        self.ingest(1, '2026-10-21T11:00:00+00:00')
        second = self.store.occurrence_list('active')['rows'][0]['occurrence_id']
        self.assertNotEqual(first, second)
        self.assertEqual(self.store.occurrence_counts(), {'active': 1, 'acked': 0, 'pending': 1, 'closed': 0, 'unknown': 0})
        self.ack(first, 'andy', '2026-10-21T11:01:00+00:00')
        self.assertEqual(self.store.occurrence_counts()['closed'], 1)
        self.assertEqual(self.store.snapshot()[0]['status'], 'active')
        self.assertIsNone(self.store.snapshot()[0]['acknowledged_by'])
        self.assertEqual(self.store.occurrence_list('active')['rows'][0]['occurrence_id'], second)
        self.assertEqual(self.store.occurrence_list('closed')['rows'][0]['acknowledged_by'], 'andy')
        self.ack(second, 'user', '2026-10-21T11:02:00+00:00')
        self.assertEqual(self.store.snapshot()[0]['acknowledged_by'], 'user')

    def test_filters_search_full_history_before_500_limit_and_open_not_limited(self):
        with self.store.transaction():
            for i in range(605):
                identifier = self.store._new_occurrence(ALARM.id, f'2026-10-21T10:{i//60:02d}:{i%60:02d}+00:00', name='Sonderfall ÜÖ' if i == 0 else 'Pumpe')
                self.store.db.execute("UPDATE occurrences SET went_at='2026-10-21T23:00:00+00:00',acknowledged=? WHERE id=?", (int(i < 600), identifier))
        self.assertEqual(self.store.occurrence_list('all')['shown'], 500)
        self.assertEqual(self.store.occurrence_list('all')['total'], 605)
        self.assertEqual(self.store.occurrence_list('all', query='Sonderfall')['total'], 1)
        self.assertEqual(self.store.occurrence_list('all', query='SONDERFALL ÜÖ')['total'], 1)
        self.assertEqual(self.store.occurrence_list('closed')['shown'], 500)
        self.assertEqual(self.store.occurrence_list()['total'], 5)
        self.assertEqual(self.store.occurrence_list('all', start='2026-10-22')['total'], 0)
        with self.store.transaction():
            self.store.db.execute('UPDATE occurrences SET acknowledged=0')
        self.assertEqual(self.store.occurrence_list()['shown'], 605)
        self.assertEqual(self.store.occurrence_list('unknown')['total'], 1)

    def test_matrix_removal_preserves_occurrence_without_inventing_went_time(self):
        self.ingest(1, '2026-10-21T10:00:00+00:00')
        identifier = self.store.occurrence_list()['rows'][0]['occurrence_id']
        self.store.save_matrix([], self.store.matrix()['revision'], 'editor')
        row = self.store.occurrence_list()['rows'][0]
        self.assertEqual(row['end_reason'], 'configuration_removed')
        self.assertIsNone(row['went_at'])
        self.assertEqual(row['name'], ALARM.name)
        self.assertTrue(self.store.acknowledge_occurrence(identifier, 'andy'))
        self.assertEqual(self.store.occurrence_list('closed')['total'], 1)
        self.assertEqual(self.store.occurrence_counts()['active'], 0)

    def test_failed_live_write_rolls_back_state_occurrence_and_event_together(self):
        with patch.object(self.store,'_event',side_effect=RuntimeError('disk full')):
            with self.assertRaises(RuntimeError):self.ingest(1,'2026-10-21T10:00:00+00:00')
        self.assertEqual(self.store.snapshot()[0]['status'],'unknown')
        self.assertEqual(self.store.occurrence_list('all')['total'],0)
        self.assertEqual(self.store.history(),[])
        self.ingest(1,'2026-10-21T10:01:00+00:00')
        self.assertEqual(self.store.occurrence_list()['total'],1)

    def test_retention_keeps_unacknowledged_or_active_cycles(self):
        with self.store.transaction():
            first = self.store._new_occurrence(ALARM.id, '2020-01-01T00:00:00+00:00')
            self.store.db.execute("UPDATE occurrences SET went_at='2020-01-02T00:00:00+00:00' WHERE id=?", (first,))
            second = self.store._new_occurrence(ALARM.id, '2020-01-03T00:00:00+00:00')
            self.store.db.execute("UPDATE occurrences SET went_at='2020-01-04T00:00:00+00:00',acknowledged=1 WHERE id=?", (second,))
            late = self.store._new_occurrence(ALARM.id, '2020-01-01T00:00:00+00:00')
            self.store.db.execute("UPDATE occurrences SET went_at='2020-01-02T00:00:00+00:00',acknowledged=1,acknowledged_at='2099-01-01T00:00:00+00:00' WHERE id=?",(late,))
            active = self.store._new_occurrence(ALARM.id, '2020-01-05T00:00:00+00:00')
            self.store.db.execute('UPDATE occurrences SET acknowledged=1 WHERE id=?', (active,))
        self.store.prune()
        self.assertEqual({r['occurrence_id'] for r in self.store.occurrence_list('all')['rows']}, {first, active, late})


class MigrationTests(unittest.TestCase):
    def make_legacy(self, path):
        store = Store(path, [ALARM])
        store.set_password('legacy-admin','test-password-123','admin')
        self.legacy_token=store.login('legacy-admin','test-password-123')
        store.save_matrix(store.matrix()['rows'],store.matrix()['revision'],'legacy-admin')
        with store.transaction():
            store.db.execute("DELETE FROM settings WHERE name='occurrences_migrated'")
            store.db.execute('DROP TABLE occurrences')
        store.close()

    def test_legacy_cycles_current_state_users_matrix_and_events_survive_idempotently(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'legacy.sqlite3'
            self.make_legacy(path)
            with sqlite3.connect(path) as db:
                for kind, timestamp, user in [('clear','2026-10-21T09:00:00+00:00',None),
                    ('active','2026-10-21T10:00:00+00:00',None),
                    ('clear','2026-10-21T10:10:00+00:00',None),
                    ('active','2026-10-21T11:00:00+00:00',None),
                    ('acknowledge','2026-10-21T11:05:00+00:00','andy')]:
                    db.execute('INSERT INTO events(alarm_id,alarm_name,kind,timestamp,username) VALUES (?,?,?,?,?)', (ALARM.id, ALARM.name, kind, timestamp, user))
                db.execute("UPDATE states SET active=1,pending=0,changed_at='2026-10-21T11:00:00+00:00',last_seen='2026-10-21T12:00:00+00:00',acknowledged_by='andy',acknowledged_at='2026-10-21T11:05:00+00:00'")
            store = Store(path, [ALARM])
            try:
                rows = store.occurrence_list('all')['rows']
                self.assertEqual(store.account('legacy-admin')['role'],'admin')
                self.assertTrue(store.authenticate('legacy-admin','test-password-123'))
                self.assertEqual(store.session_user(self.legacy_token),{'username':'legacy-admin','role':'admin'})
                self.assertEqual(store.matrix()['rows'][0]['id'],ALARM.id)
                self.assertEqual(len(rows), 2)
                self.assertEqual(store.occurrence_counts(), {'active':0,'acked':1,'pending':1,'closed':0,'unknown':0})
                self.assertEqual(store.snapshot()[0]['changed_at'], '2026-10-21T11:00:00+00:00')
                self.assertEqual(store.snapshot()[0]['last_seen'], '2026-10-21T12:00:00+00:00')
                self.assertEqual(store.snapshot()[0]['acknowledged_by'], 'andy')
                self.assertEqual(len(store.history()), 5)
                identifiers = {r['occurrence_id'] for r in rows}
                backup = list(Path(directory).glob('*.before-occurrences-*.sqlite3'))
                self.assertEqual(len(backup), 1)
                with sqlite3.connect(backup[0]) as original:
                    self.assertEqual(original.execute('SELECT count(*) FROM events').fetchone()[0], 5)
                    self.assertIsNone(original.execute("SELECT 1 FROM settings WHERE name='occurrences_migrated'").fetchone())
            finally: store.close()
            store = Store(path, [ALARM])
            try:
                self.assertEqual({r['occurrence_id'] for r in store.occurrence_list('all')['rows']}, identifiers)
                self.assertEqual(len(list(Path(directory).glob('*.before-occurrences-*.sqlite3'))), 1)
            finally: store.close()

    def test_state_only_preserves_known_times_and_marks_missing_came_time(self):
        for active, pending, changed in [(1,1,'2026-10-21T10:00:00+00:00'), (0,1,'2026-10-21T11:00:00+00:00'), (0,0,'2026-10-21T11:00:00+00:00')]:
            with self.subTest(active=active, pending=pending), TemporaryDirectory() as directory:
                path = Path(directory) / 'legacy.sqlite3'
                self.make_legacy(path)
                with sqlite3.connect(path) as db:
                    db.execute('UPDATE states SET active=?,pending=?,changed_at=?,last_seen=?', (active,pending,changed,changed))
                store = Store(path, [ALARM])
                try:
                    rows = store.occurrence_list('all')['rows']
                    if active or pending:
                        self.assertEqual(len(rows), 1)
                        self.assertEqual(rows[0]['came_at'], changed if active else None)
                        self.assertEqual(rows[0]['went_at'], None if active else changed)
                        self.assertTrue(rows[0]['migration_note'])
                    else:self.assertEqual(rows, [])
                finally:store.close()

    def test_missing_latest_events_do_not_replace_current_unacknowledged_state(self):
        for active in [0,1]:
            with self.subTest(active=active), TemporaryDirectory() as directory:
                path=Path(directory)/'legacy.sqlite3';self.make_legacy(path)
                with sqlite3.connect(path) as db:
                    db.execute("INSERT INTO events(alarm_id,alarm_name,kind,timestamp) VALUES (?,?,'active','2026-10-20T10:00:00+00:00')",(ALARM.id,ALARM.name))
                    db.execute("INSERT INTO events(alarm_id,alarm_name,kind,timestamp,username) VALUES (?,?,'acknowledge','2026-10-20T10:05:00+00:00','old-user')",(ALARM.id,ALARM.name))
                    db.execute("UPDATE states SET active=?,pending=1,changed_at='2026-10-21T11:00:00+00:00',last_seen='2026-10-21T12:00:00+00:00'",(active,))
                store=Store(path,[ALARM])
                try:
                    rows=store.occurrence_list('all')['rows']
                    self.assertEqual(len(rows),2)
                    current=next(r for r in rows if r['occurrence_id']==store.snapshot()[0]['occurrence_id'])
                    self.assertEqual(current['pending'],1)
                    self.assertIsNone(current['acknowledged_by'])
                    self.assertEqual(current['came_at'],'2026-10-21T11:00:00+00:00' if active else None)
                    old=next(r for r in rows if r['occurrence_id']!=current['occurrence_id'])
                    self.assertEqual(old['acknowledged_by'],'old-user')
                    self.assertEqual(old['end_reason'],'historical_gap')
                    self.assertIsNone(old['went_at'])
                finally:store.close()

    def test_failed_migration_rolls_back_and_can_be_retried(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'legacy.sqlite3';self.make_legacy(path)
            with sqlite3.connect(path) as db:
                db.execute("UPDATE states SET active=1,pending=1,changed_at='2026-10-21T10:00:00+00:00'")
            original = Store._migrate_occurrences
            def fail(store):
                original(store)
                raise RuntimeError('migration failure')
            with patch.object(Store, '_migrate_occurrences', fail), self.assertRaises(RuntimeError):Store(path,[ALARM])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT active,pending FROM states').fetchone(), (1,1))
                self.assertIsNone(db.execute("SELECT 1 FROM settings WHERE name='occurrences_migrated'").fetchone())
                self.assertEqual(db.execute('SELECT count(*) FROM occurrences').fetchone()[0], 0)
            store=Store(path,[ALARM])
            try:self.assertEqual(store.occurrence_list()['total'],1)
            finally:store.close()


class OccurrenceApiTests(unittest.TestCase):
    def test_roles_exact_cycle_ack_header_and_counts(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        store=Store(':memory:',[ALARM])
        for role in ['admin','user','viewer']:store.set_password(role,'test-password-123',role)
        store.ingest(ALARM.group_address,1,'1.1.1')
        identifier=store.occurrence_list()['rows'][0]['occurrence_id']
        try:
            with TestClient(create_app({'knx':{'enabled':False}},store)) as client:
                auth=('user','test-password-123');url=f'/api/occurrences/{identifier}/acknowledge'
                headers={'X-Alarmserver-Action':'acknowledge'}
                self.assertEqual(client.post(url,auth=auth).status_code,403)
                self.assertEqual(client.post(url,auth=('viewer','test-password-123'),headers=headers).status_code,403)
                self.assertEqual(client.post(url,auth=auth,headers={**headers,'Sec-Fetch-Site':'cross-site'}).status_code,403)
                response=client.post(url,auth=auth,headers=headers)
                self.assertEqual(response.status_code,200,response.text)
                self.assertTrue(response.json()['changed'])
                self.assertFalse(client.post(url,auth=('admin','test-password-123'),headers=headers).json()['changed'])
                for role in ['admin','user','viewer']:
                    response=client.get('/api/dashboard?occurrences=true&status_filter=active_ack',auth=(role,'test-password-123'))
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.json()['alarms'][0]['acknowledged_by'],'user')
                    self.assertEqual(response.json()['counts']['acked'],1)
                self.assertEqual(client.post('/api/occurrences/999/acknowledge',auth=auth,headers=headers).status_code,404)
        finally:store.close()
