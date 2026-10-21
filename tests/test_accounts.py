"""Access matrix, persisted sessions and migration of existing accounts."""
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from knx_alarmserver.store import Store
from knx_alarmserver.web import create_app
from test_core import ALARM

PASSWORD = 'test-password-123'
ACTION = {'X-Alarmserver-Action': 'manage-users'}


class Accounts(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:', [ALARM])
        self.store.set_password('admin', PASSWORD, 'admin')
        self.store.set_password('user', PASSWORD, 'user')
        self.store.set_password('viewer', PASSWORD, 'viewer')
        self.client = TestClient(create_app({'knx': {'enabled': False}}, self.store))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.close()

    def login(self, name):
        self.client.cookies.clear()
        response = self.client.post('/api/login', json={'username': name, 'password': PASSWORD},
                                    headers={'X-Alarmserver-Action': 'login'})
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_full_permission_matrix(self):
        for role in ('admin', 'user', 'viewer'):
            self.login(role)
            for path in ('/', '/static/app.js', '/api/dashboard?view=alarms', '/api/dashboard?view=history',
                         '/api/status', '/api/alarms', '/api/history'):
                self.assertEqual(self.client.get(path).status_code, 200, (role, path))
            self.assertEqual(self.client.get('/api/status').json()['role'], role)
            for path in ('/api/telegrams','/api/dashboard?view=telegrams'):
                self.assertEqual(self.client.get(path).status_code,200 if role=='admin' else 403)
            for path in ('/api/users', '/api/knx/config', '/api/ets'):
                self.assertEqual(self.client.get(path).status_code, 200 if role == 'admin' else 403, (role, path))
            if role != 'admin':
                for method, path, payload in (
                    ('put', '/api/knx/config', {}), ('post','/api/ets/preview?filename=a.xml',{}),
                    ('post','/api/ets/import?filename=a.xml&revision=x&digest=x',{}),
                    ('post','/api/users',{'username':'attack','password':PASSWORD,'role':'admin'}),
                    ('put','/api/users/admin',{'role':'viewer'}), ('delete','/api/users/admin',None)):
                    response = self.client.request(method, path, json=payload, headers=ACTION)
                    self.assertEqual(response.status_code,403,(role,path,response.text))
            self.store.ingest('1/2/3', 0, 'bus')
            self.store.ingest('1/2/3', 1, 'bus')
            response = self.client.post('/api/alarms/pump/acknowledge', headers={'X-Alarmserver-Action':'acknowledge'})
            self.assertEqual(response.status_code,403 if role == 'viewer' else 200)
            if role != 'viewer':
                self.assertEqual(self.store.snapshot()[0]['acknowledged_by'],role)
            else:
                self.assertEqual(self.store.snapshot()[0]['pending'],1)

    def test_login_session_hash_expiry_logout_and_no_password_work_on_poll(self):
        self.assertEqual(self.client.get('/').status_code,401)
        self.assertIn('login-form',self.client.get('/').text)
        self.assertNotIn('www-authenticate',self.client.get('/').headers)
        self.assertEqual(self.client.get('/static/login.js').status_code,200)
        for payload in ({'username':'admin','password':'wrong'}, {'username':'unknown','password':PASSWORD}):
            self.assertEqual(self.client.post('/api/login',json=payload,headers={'X-Alarmserver-Action':'login'}).status_code,401)
        response=self.login('admin')
        self.assertIn('HttpOnly',response.headers['set-cookie'])
        self.assertIn('SameSite=strict',response.headers['set-cookie'])
        token=self.client.cookies.get('knx_session')
        stored=self.store.db.execute('SELECT token_hash FROM sessions').fetchone()[0]
        self.assertNotEqual(stored,token)
        self.assertEqual(stored,hashlib.sha256(token.encode()).hexdigest())
        with patch.object(self.store,'authenticate',side_effect=AssertionError('No password work on poll')):
            for _ in range(5):
                self.assertEqual(self.client.get('/api/dashboard').status_code,200)
        self.assertEqual(self.client.post('/api/logout',headers={'X-Alarmserver-Action':'logout'}).status_code,200)
        self.client.cookies.set('knx_session',token)
        self.assertEqual(self.client.get('/api/status').status_code,401)
        self.login('admin')
        with self.store.transaction():
            self.store.db.execute('UPDATE sessions SET expires=?',(time.time()-1,))
        self.assertEqual(self.client.get('/api/status').status_code,401)

    def test_admin_create_edit_delete_and_revocation(self):
        self.login('admin')
        data={'username':'new','role':'viewer','password':PASSWORD}
        self.assertEqual(self.client.post('/api/users',json=data,headers=ACTION).status_code,200)
        token=self.store.login('new',PASSWORD)
        self.assertEqual(self.client.put('/api/users/new',json={'role':'user'},headers=ACTION).status_code,200)
        self.assertIsNone(self.store.session_user(token))
        self.assertTrue(self.store.authenticate('new',PASSWORD))
        token=self.store.login('new',PASSWORD)
        self.assertEqual(self.client.put('/api/users/new',json={'role':'user','password':'changed-password-123'},headers=ACTION).status_code,200)
        self.assertIsNone(self.store.session_user(token))
        self.assertFalse(self.store.authenticate('new',PASSWORD))
        self.assertTrue(self.store.authenticate('new','changed-password-123'))
        token=self.store.login('new','changed-password-123')
        self.assertEqual(self.client.delete('/api/users/new',headers=ACTION).status_code,200)
        self.assertIsNone(self.store.session_user(token))
        listing=self.client.get('/api/users').json()
        self.assertTrue(all(set(r)=={'username','role'} for r in listing))
        self.assertEqual(self.client.delete('/api/users/missing',headers=ACTION).status_code,404)

    def test_last_admin_and_invalid_changes(self):
        self.login('admin')
        for request in (lambda:self.client.delete('/api/users/admin',headers=ACTION),
                        lambda:self.client.put('/api/users/admin',json={'role':'user'},headers=ACTION)):
            self.assertEqual(request().status_code,422)
            self.assertEqual(self.store.account('admin')['role'],'admin')
        self.assertEqual(self.client.post('/api/users',json={'username':'admin','password':PASSWORD,'role':'user'},headers=ACTION).status_code,422)
        for role in ('root',[],None):
            self.assertEqual(self.client.post('/api/users',json={'username':'bad','password':PASSWORD,'role':role},headers=ACTION).status_code,422)
        self.assertEqual(self.client.post('/api/users',json={'username':'bad','password':None,'role':'user'},headers=ACTION).status_code,422)
        self.assertEqual(self.client.put('/api/users/viewer',json={'role':'admin','password':'short'},headers=ACTION).status_code,422)
        self.assertEqual(self.store.account('viewer')['role'],'viewer')
        self.store.set_password('second',PASSWORD,'admin')
        self.assertEqual(self.client.put('/api/users/admin',json={'role':'viewer'},headers=ACTION).status_code,200)
        self.assertEqual(self.client.get('/api/users').status_code,401)
        self.assertEqual(self.store.account('admin')['role'],'viewer')

    def test_login_password_work_does_not_block_alarm_store(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        started, release = threading.Event(), threading.Event()
        def verify(*args):
            started.set()
            release.wait(2)
            return True
        with patch.object(self.store, 'authenticate', side_effect=verify), ThreadPoolExecutor(2) as workers:
            login = workers.submit(self.store.login, 'admin', PASSWORD)
            try:
                self.assertTrue(started.wait(1))
                snapshot = workers.submit(self.store.snapshot)
                self.assertEqual(len(snapshot.result(timeout=.5)), 1)
            finally:
                release.set()
            self.assertIsNotNone(login.result(timeout=2))

    def test_basic_api_also_obeys_roles(self):
        self.assertEqual(self.client.get('/api/status',auth=('viewer',PASSWORD)).json()['role'],'viewer')
        self.assertEqual(self.client.get('/api/users',auth=('user',PASSWORD)).status_code,403)
        self.assertEqual(self.client.post('/api/alarms/pump/acknowledge',auth=('viewer',PASSWORD),
                                         headers={'X-Alarmserver-Action':'acknowledge'}).status_code,403)

    def test_csrf_and_size(self):
        self.login('admin')
        payload={'username':'new','role':'viewer','password':PASSWORD}
        for headers in ({}, {**ACTION,'Sec-Fetch-Site':'cross-site'}, {**ACTION,'Origin':'https://evil.example'}):
            self.assertEqual(self.client.post('/api/users',json=payload,headers=headers).status_code,403)
        self.assertEqual(self.client.post('/api/users',content='x'*9000,headers=ACTION).status_code,413)
        self.assertEqual(self.client.post('/api/users',json=[],headers=ACTION).status_code,422)
        self.assertEqual(self.client.post('/api/login',json={},headers={'X-Alarmserver-Action':'login','Origin':'https://evil.example'}).status_code,403)

    def test_legacy_no_auth_switch_cannot_bypass_roles(self):
        with patch.dict(os.environ, {'KNX_ALARMSERVER_DISABLE_AUTH':'1'}):
            with TestClient(create_app({'knx':{'enabled':False}},self.store)) as client:
                self.assertEqual(client.get('/api/status').status_code,401)
                self.assertEqual(client.get('/test/hallo').status_code,404)


class AccountMigration(unittest.TestCase):
    def test_old_users_and_sessions_survive_restart_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.db'
            salt='a'*32
            hashed=hashlib.pbkdf2_hmac('sha256',PASSWORD.encode(),salt.encode(),600000).hex()
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE users(username TEXT PRIMARY KEY,salt TEXT NOT NULL,password_hash TEXT NOT NULL)')
                db.execute('INSERT INTO users VALUES (?,?,?)',('old',salt,hashed))
            store=Store(path,[])
            self.assertEqual(store.account('old'),{'username':'old','role':'admin'})
            token=store.login('old',PASSWORD)
            store.backup(Path(directory)/'backup.db')
            store.close()
            for file in (path,Path(directory)/'backup.db'):
                store=Store(file,[])
                self.assertEqual(store.session_user(token)['role'],'admin')
                self.assertTrue(store.authenticate('old',PASSWORD))
                store.close()
