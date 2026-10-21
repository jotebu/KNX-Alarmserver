import unittest
from dataclasses import replace
from knx_alarmserver.store import Store
from knx_alarmserver.matrix import MatrixConflict, editable, csv_text, parse_csv
from test_core import ALARM

class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:',[ALARM])
    def tearDown(self):
        self.store.close()
    def save(self,entries):
        return self.store.save_priorities(entries,self.store.priorities()['revision'])

    def test_rename_changes_display_without_changing_number_state_or_history(self):
        self.store.ingest(ALARM.group_address,1,'1.1.1')
        before=self.store.snapshot()[0];events=self.store.history()
        entries=self.store.priorities()['entries'];entries[0]['name']='Notfall'
        self.save(entries)
        after=self.store.snapshot()[0]
        self.assertEqual(before['priority'],1);self.assertEqual(after['priority'],1)
        self.assertEqual(after['priority_name'],'Notfall')
        self.assertEqual(after['status'],before['status']);self.assertEqual(after['changed_at'],before['changed_at'])
        self.assertEqual(events,self.store.history())

    def test_used_number_protection_duplicates_and_revision(self):
        initial=self.store.priorities()
        for entries in [[],[{'priority':2,'name':'Andere'}],[{'priority':1,'name':'A'},{'priority':1,'name':'B'}],[{'priority':True,'name':'A'}],[{'priority':1,'name':''}]]:
            with self.assertRaises(ValueError):self.save(entries)
            self.assertEqual(self.store.priorities(),initial)
        self.save([{'priority':1,'name':'Notfall'},{'priority':8,'name':'Wartung'}])
        with self.assertRaises(MatrixConflict):self.store.save_priorities(initial['entries'],initial['revision'])

    def test_unknown_matrix_number_rejected_and_new_number_selectable(self):
        row=editable(ALARM);row['priority']='8'
        with self.assertRaises(ValueError):self.store.save_matrix([row],self.store.matrix()['revision'],'admin')
        self.save(self.store.priorities()['entries']+[{'priority':8,'name':'Wartung'}])
        self.store.save_matrix([row],self.store.matrix()['revision'],'user')
        self.assertEqual(self.store.snapshot()[0]['priority'],8)
        self.assertEqual(self.store.snapshot()[0]['priority_name'],'Wartung')
        self.save([{'priority':8,'name':'Anderer Text'}])
        self.assertEqual(self.store.snapshot()[0]['priority'],8)

    def test_priority_names_survive_restart_and_backup(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'backup.sqlite3'
            entries=self.store.priorities()['entries'];entries[0]['name']='Notfall'
            self.save(entries)
            self.store.backup(path)
            restored=Store(path,[ALARM])
            try:
                self.assertEqual(restored.priorities(),self.store.priorities())
                self.assertEqual(restored.snapshot()[0]['priority_name'],'Notfall')
            finally:restored.close()

    def test_csv_uses_numbers_and_legacy_strings_are_mapped(self):
        for old,expected in [('critical',1),('warning',2),('info',4)]:
            alarm=replace(ALARM,priority=old)
            self.assertEqual(alarm.priority,expected)
            row=editable(alarm);self.assertEqual(row['priority'],str(expected))
            raw=csv_text([row]);self.assertNotIn(old,raw)
            imported=parse_csv(raw.encode())
            self.assertEqual(imported[0]['priority'],str(expected))

class PriorityWebTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        self.store=Store(':memory:',[])
        for role in ['admin','user','viewer']:self.store.create_user(role,'test-password-123',role)
        self.client=TestClient(create_app({'knx':{'enabled':False}},self.store));self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None);self.store.close()

    def test_roles_and_csrf(self):
        for role in ['admin','user','viewer']:
            auth=(role,'test-password-123')
            self.assertEqual(self.client.get('/priorities',auth=auth).status_code,200 if role=='admin' else 403)
            self.assertEqual(self.client.get('/api/priorities',auth=auth).status_code,200)
            state=self.store.priorities()
            response=self.client.put('/api/priorities',auth=auth,json=state,headers={'X-Alarmserver-Action':'manage-priorities'})
            self.assertEqual(response.status_code,200 if role=='admin' else 403)
        auth=('admin','test-password-123');state=self.store.priorities()
        self.assertEqual(self.client.put('/api/priorities',auth=auth,json=state).status_code,403)
        self.assertEqual(self.client.put('/api/priorities',auth=auth,json=state,headers={'X-Alarmserver-Action':'manage-priorities','Origin':'http://other'}).status_code,403)
        self.assertEqual(self.client.get('/api/priorities').status_code,401)

    def test_example_uses_configured_number_after_defaults_removed(self):
        self.store.save_priorities([{'priority':8,'name':'Wartung'}],self.store.priorities()['revision'])
        response=self.client.get('/api/matrix/example.csv',auth=('user','test-password-123'))
        rows=parse_csv(response.content)
        self.assertTrue(all(row['priority']=='8' for row in rows))
