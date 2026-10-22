"""Account profiles, validation, historical names and non-destructive migration."""
import contextlib
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from knx_alarmserver.store import Store
from knx_alarmserver.web import create_app
from test_core import ALARM

PASSWORD='test-password-123'
ACTION={'X-Alarmserver-Action':'manage-users'}

class Profiles(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:',[ALARM])
        self.store.set_password('admin',PASSWORD,'admin')
        self.client=TestClient(create_app({'knx':{'enabled':False}},self.store))
        self.client.__enter__()
        self.client.auth=('admin',PASSWORD)

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.store.close()

    def test_registration_requires_email_and_both_names_on_server(self):
        good={'username':'person@example.org','password':PASSWORD,'role':'user','first_name':' Ada ','last_name':' Lovelace '}
        for key in ['first_name','last_name']:
            invalid=dict(good);del invalid[key]
            self.assertEqual(self.client.post('/api/users',json=invalid,headers=ACTION).status_code,422)
        for key,value in [('username','person'),('username','a..b@example.org'),('username','a@-example.org'),('username','a@'),('first_name',' '),('last_name',None),('last_name','A\nB')]:
            self.assertEqual(self.client.post('/api/users',json={**good,key:value},headers=ACTION).status_code,422)
        self.assertIsNone(self.store.account(good['username']))
        self.assertEqual(self.client.post('/api/users',json=good,headers=ACTION).status_code,200)
        record=next(row for row in self.client.get('/api/users').json() if row['username']==good['username'])
        self.assertEqual((record['first_name'],record['last_name']),('Ada','Lovelace'))
        self.assertTrue(self.store.authenticate(good['username'],PASSWORD))
        self.assertEqual(self.client.post('/api/users',json={**good,'username':'PERSON@example.org'},headers=ACTION).status_code,422)
        self.assertEqual(self.store.account(good['username'])['role'],'user')
        long_email='person@'+('a'*55)+'.example.org'
        self.assertEqual(self.client.post('/api/users',json={**good,'username':long_email},headers=ACTION).status_code,200)
        response=self.client.post('/api/login',json={'username':long_email,'password':PASSWORD},headers={'X-Alarmserver-Action':'login'})
        self.assertEqual(response.status_code,200)

    def test_profile_edit_is_atomic_and_still_admin_only(self):
        self.store.create_user('person@example.org',PASSWORD,'user','Ada','Lovelace')
        for role in ['user','viewer']:
            self.store.set_password(role,PASSWORD,role)
            response=self.client.put('/api/users/person@example.org',auth=(role,PASSWORD),json={'role':'user','first_name':'Other','last_name':'Name'},headers=ACTION)
            self.assertEqual(response.status_code,403)
        bad=self.client.put('/api/users/person@example.org',json={'role':'admin','first_name':'','last_name':'Name'},headers=ACTION)
        self.assertEqual(bad.status_code,422)
        self.assertEqual(self.store.account('person@example.org')['role'],'user')
        self.assertEqual(self.store.display_name('person@example.org'),'Ada Lovelace')
        token=self.store.login('person@example.org',PASSWORD)
        good=self.client.put('/api/users/person@example.org',json={'role':'user','first_name':'Grace','last_name':'Hopper'},headers=ACTION)
        self.assertEqual(good.status_code,200)
        self.assertEqual(self.store.display_name('person@example.org'),'Grace Hopper')
        self.assertIsNone(self.store.session_user(token))

    def test_acknowledgement_keeps_original_full_name_after_edit_and_deletion(self):
        self.store.create_user('person@example.org',PASSWORD,'user','Ada','Lovelace')
        self.store.ingest(ALARM.group_address,1,'bus')
        identifier=self.store.occurrence_list()['rows'][0]['occurrence_id']
        response=self.client.post(f'/api/occurrences/{identifier}/acknowledge',auth=('person@example.org',PASSWORD),headers={'X-Alarmserver-Action':'acknowledge'})
        self.assertEqual(response.status_code,200)
        before=self.store.occurrence_list()['rows'][0]
        self.assertEqual(before['acknowledged_name'],'Ada Lovelace')
        self.assertEqual(before['acknowledged_by'],'person@example.org')
        self.store.set_profile('person@example.org','Grace','Hopper')
        self.store.delete_user('person@example.org')
        after=self.store.occurrence_list()['rows'][0]
        self.assertEqual(after['acknowledged_name'],'Ada Lovelace')
        self.assertEqual(after['acknowledged_at'],before['acknowledged_at'])
        self.assertEqual(after['came_at'],before['came_at'])

class ProfileMigration(unittest.TestCase):
    def test_legacy_names_can_be_added_without_resetting_sessions_states_or_acknowledgement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.db'
            store=Store(path,[ALARM]);store.set_password('legacy',PASSWORD,'admin')
            token=store.login('legacy',PASSWORD);store.ingest(ALARM.group_address,1,'bus')
            identifier=store.occurrence_list()['rows'][0]['occurrence_id'];store.acknowledge_occurrence(identifier,'legacy')
            before=store.snapshot()[0];store.close()
            with sqlite3.connect(path) as db:
                db.execute('ALTER TABLE users DROP COLUMN first_name');db.execute('ALTER TABLE users DROP COLUMN last_name');db.execute('ALTER TABLE occurrences DROP COLUMN acknowledged_name')
            for _ in range(2):
                store=Store(path,[ALARM])
                after=store.snapshot()[0]
                self.assertEqual({k:v for k,v in after.items() if k!='fresh'},{k:v for k,v in before.items() if k!='fresh'})
                self.assertIsNotNone(store.session_user(token));self.assertTrue(store.authenticate('legacy',PASSWORD))
                store.set_profile('legacy','Ada','Lovelace')
                row=store.occurrence_list()['rows'][0]
                self.assertEqual(row['acknowledged_name'],'Ada Lovelace')
                self.assertEqual(row['acknowledged_at'],before['acknowledged_at'])
                store.close()

    def test_cli_sets_only_profile_without_touching_password_role_or_session(self):
        from knx_alarmserver.cli import main
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.db'
            store=Store(path,[]);store.set_password('person@example.org',PASSWORD,'admin');token=store.login('person@example.org',PASSWORD);store.close()
            config={'server':{'database':str(path),'retention_days':365},'knx':{'enabled':False}}
            with patch('sys.argv',['knx-alarmserver','user-profile','person@example.org','Ada','Lovelace']),patch('knx_alarmserver.cli.load_config',return_value=config),patch('knx_alarmserver.cli.load_configured_alarms',return_value=[]),patch('logging.basicConfig'),contextlib.redirect_stdout(io.StringIO()):
                main()
            store=Store(path,[])
            self.assertEqual(store.display_name('person@example.org'),'Ada Lovelace')
            self.assertTrue(store.authenticate('person@example.org',PASSWORD));self.assertIsNotNone(store.session_user(token));self.assertEqual(store.account('person@example.org')['role'],'admin')
            store.close()
