import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import unittest

from knx_alarmserver.bus_test import test_values, revision
from knx_alarmserver.knx import Monitor
from knx_alarmserver.store import Store
from knx_alarmserver.rules import evaluate
from test_core import ALARM


class ValueTests(unittest.TestCase):
    def test_dpt_roundtrip_and_active_hysteresis(self):
        rules = [('1.005','eq',0,0), ('1.005','ne',0,0), ('9.001','gt',30,2),
                 ('9.001','ge',30,2), ('9.001','lt',10,2), ('9.001','le',10,2),
                 ('9.001','between',[10,20],1), ('9.001','outside',[10,20],1),
                 ('20.102','eq',4,0), ('20.102','in',[1,2],0), ('16.001','contains','Fehler',0)]
        for dpt, op, target, h in rules:
            with self.subTest(dpt=dpt, op=op):
                alarm=replace(ALARM,dpt=dpt,operator=op,threshold=target,hysteresis=h)
                values=test_values(alarm)
                self.assertTrue(evaluate(alarm,values['alarm'][1],False))
                self.assertFalse(evaluate(alarm,values['normal'][1],True))
                self.assertFalse(evaluate(alarm,values['normal'][1],False))

    def test_impossible_and_structured_rules_are_not_guessed(self):
        for alarm in [replace(ALARM,operator='monitor'),replace(ALARM,field='status'),
                      replace(ALARM,dpt='5.010',operator='gt',threshold=255),
                      replace(ALARM,dpt='16.001',operator='contains',threshold='')]:
            with self.assertRaises(ValueError):test_values(alarm)


class BusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store=Store(':memory:',[ALARM,replace(ALARM,id='other',group_address='1/2/4')])
        self.monitor=Monitor({'enabled':True},self.store)
        self.monitor.connections['line']={'name':'line','state':'CONNECTED'}
        self.sender=AsyncMock()
        self.monitor.clients['line']=SimpleNamespace(telegram_queue=SimpleNamespace(process_telegram_outgoing=self.sender))
        self.test=self.monitor.bus_test

    async def asyncTearDown(self):
        await self.monitor.stop();self.store.close()

    def start(self,mode='alarm',ids=None):
        return self.test.start(ids or ['pump','other'],mode,revision(self.store),'line','admin@example.org')

    async def test_mail_disabled_before_send_pacing_and_local_occurrences(self):
        from xknx.telegram.apci import GroupValueWrite
        self.store.set_password('admin@example.org','test-password-123')
        self.store.set_mail_enabled('admin@example.org',True)
        events=[]
        async def send(telegram):
            self.assertFalse(self.store.mail_settings()['config']['enabled'])
            self.assertTrue(self.store.bus_test_active)
            self.assertIsInstance(telegram.payload,GroupValueWrite)
            events.append('send')
        async def pause():events.append('pause');await asyncio.sleep(0)
        self.sender.side_effect=send
        with patch.object(self.test,'_pause',side_effect=pause):
            self.start()
            with self.assertRaises(RuntimeError):self.start()
            with self.assertRaises(FileExistsError):self.monitor.request_read()
            await self.test.task
        self.assertEqual(events,['send','pause','send'])
        self.assertEqual(self.test.state['state'],'complete')
        self.assertEqual(self.test.state['sent'],2)
        self.assertEqual(len(self.store.history()),2)
        self.assertEqual(self.store.mail_settings()['counts'].get('pending',0),0)
        self.assertFalse(self.store.bus_test_active)
        self.assertFalse(self.store.mail_settings()['config']['enabled'])
        self.assertTrue(all(row['status']=='active' for row in self.store.snapshot()))
        self.start('normal',['pump']);await self.test.task
        self.assertEqual(self.store.snapshot()[0]['status'],'clear_pending')

    async def test_stop_after_first_write_and_stale_revision(self):
        async def send(_):self.test.stop()
        self.sender.side_effect=send
        self.start();await self.test.task
        self.assertEqual(self.sender.await_count,1)
        self.assertEqual(self.test.state['state'],'cancelled')
        with self.assertRaises(RuntimeError):self.test.start(['pump'],'alarm','old','line','admin')
        self.assertFalse(self.store.mail_settings()['config']['enabled'])

    async def test_disable_failure_prevents_all_writes(self):
        with patch.object(self.store,'begin_bus_test',side_effect=RuntimeError('disk full')):
            self.start();await self.test.task
        self.assertEqual(self.test.state['state'],'failed')
        self.assertEqual(self.sender.await_count,0)
        self.assertFalse(self.test.state['mail_disabled'])
        self.assertIn('nicht bestätigt',self.test.state['message'])

    async def test_transport_failure_and_changed_matrix_stop_job(self):
        self.sender.side_effect=RuntimeError('offline')
        self.start();await self.test.task
        self.assertEqual(self.test.state['state'],'failed')
        self.assertEqual(self.test.state['sent'],0)
        self.assertTrue(all(row['status']=='unknown' for row in self.store.snapshot()))
        self.sender.side_effect=None
        async def pause():self.store.alarms['other']=replace(ALARM,id='other',group_address='1/2/4',threshold=0)
        with patch.object(self.test,'_pause',side_effect=pause):
            self.start();await self.test.task
        self.assertEqual(self.test.state['state'],'failed')
        self.assertEqual(self.test.state['sent'],1)

    async def test_smtp_guard_and_saved_disabled_config(self):
        saved=self.store.mail_settings()
        # Use a valid but not network-connected SMTP configuration.
        saved['config'].pop('password_set', None)
        saved['config'].update(enabled=True,host='smtp.example.org',from_email='alarm@example.org')
        self.store.save_mail_settings(saved['config'],saved['revision'])
        self.store.begin_bus_test()
        disabled=self.store.mail_settings();self.assertFalse(disabled['config']['enabled'])
        proposed=dict(disabled['config'],enabled=True);proposed.pop('password_set',None)
        with self.assertRaises(RuntimeError):self.store.save_mail_settings(proposed,disabled['revision'])
        self.assertIsNone(self.store.claim_mail())
        self.store.end_bus_test();self.assertFalse(self.store.mail_settings()['config']['enabled'])

    async def test_default_interval_is_one_second(self):
        from time import monotonic
        times=[]
        async def send(_):times.append(monotonic())
        self.sender.side_effect=send
        self.start();await self.test.task
        self.assertEqual(len(times),2)
        self.assertGreaterEqual(times[1]-times[0],0.95)

    async def test_waits_for_inflight_smtp_before_bus_writes(self):
        import threading
        entered,release=threading.Event(),threading.Event()
        def smtp_inflight():
            with self.store.mail_send_lock:
                entered.set();release.wait(3)
        thread=asyncio.create_task(asyncio.to_thread(smtp_inflight))
        await asyncio.to_thread(entered.wait,1)
        self.start(ids=['pump'])
        await asyncio.sleep(.03)
        self.assertEqual(self.sender.await_count,0)
        release.set();await thread;await self.test.task
        self.assertEqual(self.sender.await_count,1)
        self.assertFalse(self.store.mail_settings()['config']['enabled'])

    async def test_plan_single_row_and_invalid_selection(self):
        plan=self.test.plan('pump');self.assertEqual(len(plan['rows']),1)
        self.assertTrue(plan['rows'][0]['ready'])
        for ids in [[],['pump','pump'],['missing']]:
            with self.assertRaises(ValueError):self.test.start(ids,'alarm',plan['revision'],'line','admin')
        with self.assertRaises(ValueError):self.test.plan('missing')

class BusWebTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        self.store=Store(':memory:',[ALARM])
        for role in ['admin','user','viewer']:
            self.store.set_password(role,'test-password-123',role=role)
        self.app=create_app({'knx':{'enabled':False}},self.store)
        self.client=TestClient(self.app);self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None);self.store.close()

    def test_preview_permissions_action_header_stale_revision_and_no_connection(self):
        for role in ['user','viewer']:
            auth=(role,'test-password-123')
            self.assertEqual(self.client.get('/api/knx/test/plan',auth=auth).status_code,403)
            self.assertEqual(self.client.post('/api/knx/test/start',auth=auth,json={}).status_code,403)
            self.assertEqual(self.client.post('/api/knx/test/stop',auth=auth).status_code,403)
        auth=('admin','test-password-123')
        self.assertEqual(self.client.get('/api/knx/test/plan').status_code,401)
        plan=self.client.get('/api/knx/test/plan?alarm_id=pump',auth=auth).json()
        self.assertTrue(plan['rows'][0]['ready'])
        self.assertEqual(self.client.post('/api/knx/test/start',auth=auth,json={}).status_code,403)
        headers={'X-Alarmserver-Action':'test-knx'}
        payload={'ids':['pump'],'mode':'alarm','revision':plan['revision'],'connection':'line'}
        self.assertEqual(self.client.post('/api/knx/test/start',auth=auth,headers=headers,json=payload).status_code,422)
        self.assertEqual(self.client.post('/api/knx/test/stop',auth=auth,headers={**headers,'Sec-Fetch-Site':'cross-site'}).status_code,403)
        self.assertEqual(self.client.get('/static/bus-test.js',auth=auth).status_code,200)
        settings=self.store.mail_settings();config=settings['config'];config.pop('password_set');config.update(host='smtp.example.org',from_email='alarm@example.org')
        self.store.save_mail_settings(config,settings['revision']);self.store.begin_bus_test()
        with patch('knx_alarmserver.mail.smtplib.SMTP') as smtp:
            response=self.client.post('/api/mail/test',auth=auth,headers={'X-Alarmserver-Action':'manage-mail'},json={'recipient':'person@example.org'})
            self.assertEqual(response.status_code,409);smtp.assert_not_called()
        self.store.end_bus_test()

