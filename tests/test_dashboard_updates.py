import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from knx_alarmserver.store import Store
from knx_alarmserver.updates import DashboardUpdate
from knx_alarmserver.web import create_app

spec = importlib.util.spec_from_file_location('dashboard_worker', Path(__file__).resolve().parents[1]/'scripts/dashboard_update.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
PASSWORD='test-password-123'


class DashboardUpdates(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.root=Path(self.directory.name)
        self.helper=self.root/'helper';self.helper.touch()
        self.unit=self.root/'path-unit';self.unit.touch()
        self.updater=DashboardUpdate(self.root/'request',self.root/'status.json',self.helper,self.unit)
        self.store=Store(':memory:',[])
        for role in ('admin','user','viewer'):
            self.store.set_password(role,PASSWORD,role)
        self.client=TestClient(create_app({'knx':{'enabled':False}},self.store,self.updater))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.store.close();self.directory.cleanup()

    def test_queue_once_and_ignore_no_roles(self):
        for role in ('user','viewer'):
            self.assertEqual(self.client.get('/api/update',auth=(role,PASSWORD)).status_code,403)
            self.assertEqual(self.client.post('/api/update',auth=(role,PASSWORD),headers={'X-Alarmserver-Action':'update-server'}).status_code,403)
        self.assertEqual(self.client.post('/api/update',auth=('admin',PASSWORD)).status_code,403)
        self.assertEqual(self.client.post('/api/update',auth=('admin',PASSWORD),headers={'X-Alarmserver-Action':'update-server','Sec-Fetch-Site':'cross-site'}).status_code,403)
        self.assertEqual(self.client.post('/api/update',auth=('admin',PASSWORD),json={'command':'bad'},headers={'X-Alarmserver-Action':'update-server'}).status_code,422)
        self.assertEqual(self.client.post('/api/update',auth=('admin',PASSWORD),headers={'X-Alarmserver-Action':'update-server'}).status_code,202)
        self.assertEqual(self.updater.request_path.read_bytes(),b'')
        self.assertEqual(self.client.post('/api/update',auth=('admin',PASSWORD),headers={'X-Alarmserver-Action':'update-server'}).status_code,409)
        self.assertEqual(self.client.get('/api/update',auth=('admin',PASSWORD)).json()['state'],'queued')

    def test_missing_helper_active_status_and_symlink(self):
        self.helper.unlink()
        self.assertFalse(self.updater.status()['available'])
        with self.assertRaises(RuntimeError):self.updater.start()
        self.helper.touch()
        self.updater.status_path.write_text(json.dumps({'state':'installing'}))
        with self.assertRaises(FileExistsError):self.updater.start()
        self.updater.status_path.write_text('not JSON')
        self.assertEqual(self.updater.status()['state'],'idle')
        victim=self.root/'victim';victim.write_text('preserve')
        self.updater.request_path.symlink_to(victim)
        with self.assertRaises(FileExistsError):self.updater.start()
        self.assertEqual(victim.read_text(),'preserve')

    def test_separate_pages_and_own_password_for_every_role(self):
        for role in ('admin','user','viewer'):
            auth=(role,PASSWORD)
            self.assertEqual(self.client.get('/account/password',auth=auth).status_code,200)
            self.assertEqual(self.client.get('/versions',auth=auth).status_code,200)
            for page in ('/telegrams','/knx','/ets','/users'):
                self.assertEqual(self.client.get(page,auth=auth).status_code,200 if role=='admin' else 403)
            current=self.store.login(role,PASSWORD)
            payload={'current_password':'wrong','new_password':'new-password-123'}
            self.assertEqual(self.client.post('/api/account/password',auth=auth,json=payload,headers={'X-Alarmserver-Action':'change-password'}).status_code,422)
            self.assertIsNotNone(self.store.session_user(current))
            payload['current_password']=PASSWORD
            payload['username']='someone-else'
            self.assertEqual(self.client.post('/api/account/password',auth=auth,json=payload,headers={'X-Alarmserver-Action':'change-password'}).status_code,422)
            del payload['username']
            self.assertEqual(self.client.post('/api/account/password',auth=auth,json=payload).status_code,403)
            self.assertEqual(self.client.post('/api/account/password',auth=auth,json=payload,headers={'X-Alarmserver-Action':'change-password'}).status_code,200)
            self.assertIsNone(self.store.session_user(current))
            self.assertFalse(self.store.authenticate(role,PASSWORD))
            self.assertTrue(self.store.authenticate(role,'new-password-123'))
            self.assertEqual(self.store.account(role)['role'],role)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        self.request=self.root/'request';self.current=self.root/'current.toml'
        self.current.write_text('[project]\nversion="0.10.10"\n')
        self.patches=[patch.object(worker,'REQUEST',self.request),patch.object(worker,'STATUS',self.root/'runtime'/'status.json'),
                      patch.object(worker,'CURRENT',self.current),patch.object(worker,'LOCK',self.root/'lock'),
                      patch.object(worker.os,'geteuid',return_value=0)]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.directory.cleanup()

    def test_fixed_repository_and_independent_install_status(self):
        self.request.write_text('arbitrary untrusted command')
        def command(args,**options):
            self.assertNotIn('arbitrary untrusted command',' '.join(args))
            self.assertTrue(options['check'])
            if args[0]=='git':
                self.assertIn(worker.REPOSITORY,args)
                self.assertIn('main',args)
                source=Path(args[-1]);source.mkdir()
                (source/'pyproject.toml').write_text('[project]\nversion="0.10.11"\n')
            else:
                self.assertEqual(args[0],'/bin/bash')
                self.current.write_text('[project]\nversion="0.10.11"\n')
        with patch.object(worker.subprocess,'run',side_effect=command),patch.object(worker.subprocess,'check_output',return_value='a'*40):
            worker.run()
        result=json.loads(worker.STATUS.read_text())
        self.assertEqual(result['state'],'success')
        self.assertEqual(result['previous_version'],'0.10.10')
        self.assertEqual(result['target_version'],'0.10.11')
        self.assertEqual(worker.STATUS.stat().st_mode&0o777,0o644)
        self.assertFalse(self.request.exists())
        worker.finish()
        self.assertEqual(json.loads(worker.STATUS.read_text())['state'],'success')

    def test_failed_or_interrupted_job_is_not_successful(self):
        self.request.touch()
        with patch.object(worker.subprocess,'run',side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):worker.run()
        self.assertEqual(json.loads(worker.STATUS.read_text())['state'],'failed')
        worker.write_status('installing','pending')
        worker.finish()
        self.assertEqual(json.loads(worker.STATUS.read_text())['state'],'failed')

    def test_request_symlink_is_unlinked_without_touching_target(self):
        target=self.root/'target';target.write_text('preserve')
        self.request.symlink_to(target)
        with patch.object(worker.subprocess,'run',side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):worker.run()
        self.assertEqual(target.read_text(),'preserve')
        self.assertFalse(self.request.is_symlink())
