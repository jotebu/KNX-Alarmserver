import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from knx_alarmserver.config import validate_knx
from knx_alarmserver.store import Store
from knx_alarmserver.web import create_app
from knx_alarmserver.knx import Monitor


class ConnectionValidationTests(unittest.TestCase):
    def test_invalid_addresses_ports_names_and_secure_rejected(self):
        good = {'name':'Test','type':'tunneling','gateway_ip':'192.0.2.1'}
        variants = [dict(good,gateway_ip='wrong'),dict(good,gateway_port=0),dict(good,gateway_port=True),
                    dict(good,enabled='yes'),dict(good,secure=True),dict(good,gateway_ip='224.0.23.12')]
        for connection in variants:
            with self.subTest(connection=connection), self.assertRaises(ValueError):
                validate_knx({'enabled':False,'connections':[connection]})
        with self.assertRaises(ValueError):
            validate_knx({'connections':[good,good]})
        with self.assertRaises(ValueError):
            validate_knx({'enabled':True,'connections':[dict(good,enabled=False)]})
        with self.assertRaises(ValueError):
            validate_knx({'connections':[{'name':'R','type':'routing','individual_address':'16.0.1'}]})
        with self.assertRaises(ValueError):
            validate_knx({'connections':[{'name':'R','type':'routing','individual_address':'1.0.1','multicast_group':'192.0.2.1'}]})


class KnxSettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'test.sqlite3'
        self.store = Store(self.path, [])
        self.store.set_password('admin', 'test-password-123')
        self.config = {'knx':{'enabled':False,'connections':[]}}
        self.auth = ('admin','test-password-123')
        self.headers = {'X-Alarmserver-Action':'configure-knx'}
        self.client = TestClient(create_app(self.config, self.store))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.store.close()
        self.directory.cleanup()

    def current(self):
        return self.client.get('/api/knx/config',auth=self.auth).json()

    def save(self, config, revision=None, headers=None):
        return self.client.put('/api/knx/config',auth=self.auth,headers=headers if headers is not None else self.headers,
                               json={'config':config,'revision':revision or self.current()['revision']})

    def test_authentication_and_cross_site_protection(self):
        self.assertEqual(self.client.get('/api/knx/config').status_code,401)
        self.assertEqual(self.client.put('/api/knx/config',json={}).status_code,401)
        self.assertEqual(self.save(self.config['knx'],headers={}).status_code,403)
        self.assertEqual(self.save(self.config['knx'],headers={**self.headers,'Sec-Fetch-Site':'cross-site'}).status_code,403)

    def test_add_edit_remove_restart_and_backup(self):
        c={'enabled':False,'connections':[{'name':'Router','type':'tunneling','gateway_ip':'192.0.2.1','enabled':True}]}
        self.assertEqual(self.save(c).status_code,200)
        c['connections'][0]['name']='Updated'
        self.assertEqual(self.save(c).status_code,200)
        self.assertEqual(self.current()['source'],'dashboard')
        backup=Path(self.directory.name)/'backup.sqlite3'
        self.store.backup(backup)
        other=Store(backup,[])
        try:
            self.assertEqual(other.knx_settings({})['config'],c)
        finally:
            other.close()
        with TestClient(create_app(self.config,self.store)) as client:
            self.assertEqual(client.get('/api/knx/config',auth=self.auth).json()['config'],c)
        self.assertEqual(self.save({'enabled':False,'connections':[]}).status_code,200)

    def test_invalid_payload_and_stale_revision_do_not_change_settings(self):
        previous=self.current()
        c={'enabled':False,'connections':[{'name':'Router','gateway_ip':'192.0.2.1'}]}
        self.assertEqual(self.save(c).status_code,200)
        self.assertEqual(self.save(self.config['knx'],revision=previous['revision']).status_code,409)
        current=self.current()
        self.assertEqual(self.save({'enabled':True,'connections':[]}).status_code,422)
        self.assertEqual(self.current(),current)
        response=self.client.put('/api/knx/config',auth=self.auth,headers=self.headers,content='x'*65537)
        self.assertEqual(response.status_code,413)
        self.assertEqual(self.current(),current)

    def test_live_reconfiguration_skips_disabled_connections(self):
        c={'enabled':True,'connections':[{'name':'On','gateway_ip':'192.0.2.1'},
                                       {'name':'Off','gateway_ip':'192.0.2.2','enabled':False}]}
        with patch.object(Monitor,'_run_connection',new_callable=AsyncMock) as run:
            self.assertEqual(self.save(c).status_code,200)
            self.assertEqual(self.client.app.state.monitor.config,c)
            self.assertEqual(list(self.client.app.state.monitor.connections),['On'])
            self.assertEqual(run.await_count,1)
            states = self.client.app.state.monitor.status()['connections']
            self.assertEqual([(state['name'], state['state']) for state in states], [('On', 'CONNECTING'), ('Off', 'DISABLED')])
            self.client.app.state.monitor.connections['On']['state'] = 'CONNECTED'
            self.assertTrue(self.client.app.state.monitor.status()['ready'])
        self.assertEqual(self.save({'enabled':False,'connections':c['connections']}).status_code,200)
        self.assertFalse(self.client.app.state.monitor.tasks)
        states = self.client.app.state.monitor.status()['connections']
        self.assertEqual([(state['name'], state['state']) for state in states], [('On', 'DISABLED'), ('Off', 'DISABLED')])
        self.assertFalse(self.client.app.state.monitor.status()['ready'])

    def test_storage_failure_restores_previous_monitor(self):
        previous=self.current()
        old=self.client.app.state.monitor
        with patch.object(self.store,'save_knx_settings',side_effect=RuntimeError('disk full')):
            response=self.save({'enabled':False,'connections':[{'name':'X','gateway_ip':'192.0.2.1'}]})
        self.assertEqual(response.status_code,500)
        self.assertIs(self.client.app.state.monitor,old)
        self.assertEqual(self.current(),previous)
