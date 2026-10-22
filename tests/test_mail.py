"""No real mail is sent: all SMTP transports and background senders are mocked."""
import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import smtplib
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from knx_alarmserver.mail import MailWorker, send_smtp, validate_template
from knx_alarmserver.store import Store
from knx_alarmserver.web import create_app
from test_core import ALARM

PASSWORD='test-password-123'
ACTION={'X-Alarmserver-Action':'manage-mail'}

def config(store,**updates):
    current=store.mail_settings();proposed=copy.deepcopy(current['config']);proposed.pop('password_set');proposed.update(enabled=True,host='smtp.example.org',from_email='alarm@example.org');proposed.update(updates)
    return store.save_mail_settings(proposed,current['revision'])

def recipient(store,email='person@example.org'):
    store.create_user(email,PASSWORD,'user','Ada','Lovelace',True)

class MailTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:',[ALARM])
        recipient(self.store)
    def tearDown(self):self.store.close()
    def jobs(self):return [dict(r) for r in self.store.db.execute('SELECT * FROM mail_outbox ORDER BY id')]

    def test_only_new_occurrences_and_opted_in_users_are_queued_with_snapshot_templates(self):
        self.store.create_user('silent@example.org',PASSWORD,'viewer','Silent','Person')
        self.store.ingest(ALARM.group_address,1,'1.1.1');self.assertEqual(self.jobs(),[])
        settings=config(self.store,templates={str(ALARM.priority):{'subject':'{prioritaet} {meldung} #{vorgangsnummer}','body':'Hallo {empfaenger_name}: {bereich} · {gruppenadresse} · {dpt} · {wert} {einheit} {{literal}}'}})
        self.store.ingest(ALARM.group_address,1,'1.1.1');self.assertEqual(self.jobs(),[])
        self.store.ingest(ALARM.group_address,0,'1.1.1');self.store.ingest(ALARM.group_address,1,'1.1.1',display='Ein',unit='Stück')
        row=self.jobs()[0];self.assertEqual(len(self.jobs()),1);self.assertEqual(row['recipient'],'person@example.org');self.assertIn('Hallo Ada Lovelace',row['body']);self.assertIn('Ein Stück {literal}',row['body']);self.assertIn(ALARM.name,row['subject'])
        self.store.ingest(ALARM.group_address,1,'1.1.2');self.store.acknowledge_occurrence(row['occurrence_id'],'person@example.org');self.assertEqual(len(self.jobs()),1)
        config(self.store,templates={str(ALARM.priority):{'subject':'Changed','body':'Changed'}})
        self.assertEqual(self.jobs()[0]['subject'],row['subject'])
        self.store.ingest(ALARM.group_address,0,'bus');self.store.ingest(ALARM.group_address,1,'bus');self.assertEqual(len(self.jobs()),2);self.assertNotEqual(self.jobs()[1]['occurrence_id'],row['occurrence_id'])
        self.assertEqual(self.jobs()[1]['subject'],'Changed')

    def test_retry_backoff_maximum_and_manual_retry_without_leaking_server_errors(self):
        config(self.store);self.store.ingest(ALARM.group_address,1,'bus')
        sender=Mock(side_effect=smtplib.SMTPAuthenticationError(535,b'secret-password'))
        worker=MailWorker(self.store,sender)
        self.assertTrue(worker.tick());self.assertFalse(worker.tick());self.assertEqual(sender.call_count,1)
        for _ in range(4):
            with self.store.transaction():self.store.db.execute('UPDATE mail_outbox SET next_attempt=0')
            worker.tick()
        job=self.jobs()[0];self.assertEqual(job['attempts'],5);self.assertEqual(job['status'],'failed');self.assertNotIn('secret',job['last_error']);self.assertFalse(worker.tick())
        self.assertEqual(self.store.retry_failed_mail(),1);sender.side_effect=None;worker.tick();self.assertEqual(self.jobs()[0]['status'],'sent');self.assertIsNotNone(self.jobs()[0]['sent_at']);self.assertFalse(worker.tick())

    def test_disabled_deleted_recipients_are_cancelled_and_global_disable_pauses(self):
        config(self.store);self.store.ingest(ALARM.group_address,1,'bus');sender=Mock();worker=MailWorker(self.store,sender)
        config(self.store,enabled=False);self.assertFalse(worker.tick());self.assertEqual(self.jobs()[0]['status'],'pending')
        self.store.update_user('person@example.org','user',mail_enabled=False);config(self.store);self.assertFalse(worker.tick());sender.assert_not_called();self.assertEqual(self.jobs()[0]['status'],'cancelled')
        self.store.update_user('person@example.org','user',mail_enabled=True);self.store.ingest(ALARM.group_address,0,'bus');self.store.ingest(ALARM.group_address,1,'bus');self.store.delete_user('person@example.org')
        self.assertFalse(worker.tick());self.assertTrue(all(row['status']=='cancelled' for row in self.jobs()));sender.assert_not_called()

    def test_alarm_state_and_outbox_rollback_together_if_queue_write_fails(self):
        config(self.store)
        with self.store.transaction():self.store.db.execute("CREATE TRIGGER fail_mail BEFORE INSERT ON mail_outbox BEGIN SELECT RAISE(ABORT,'disk full'); END")
        with self.assertRaises(sqlite3.DatabaseError):self.store.ingest(ALARM.group_address,1,'bus')
        self.assertEqual(self.store.snapshot()[0]['status'],'unknown');self.assertEqual(self.store.occurrence_list('all')['total'],0);self.assertEqual(self.jobs(),[])

    def test_slow_smtp_does_not_hold_alarm_database_lock(self):
        config(self.store);self.store.ingest(ALARM.group_address,1,'bus');entered=threading.Event();release=threading.Event()
        def slow(config,job):entered.set();release.wait(2)
        with ThreadPoolExecutor(2) as pool:
            sending=pool.submit(MailWorker(self.store,slow).tick)
            try:
                self.assertTrue(entered.wait(1));self.assertEqual(pool.submit(self.store.snapshot).result(timeout=.5)[0]['status'],'active')
                self.assertFalse(pool.submit(self.store.ingest,ALARM.group_address,1,'bus').result(timeout=.5))
            finally:release.set()
            self.assertTrue(sending.result(timeout=1))

    def test_password_redaction_preservation_clear_and_revision_conflict(self):
        result=config(self.store,password='private-secret');self.assertNotIn('private-secret',str(result));self.assertTrue(result['config']['password_set'])
        config(self.store,password='');self.assertEqual(self.store._mail_settings()['config']['password'],'private-secret')
        with self.assertRaises(RuntimeError):self.store.save_mail_settings({},result['revision'])
        current=self.store.mail_settings();payload=copy.deepcopy(current['config']);payload.pop('password_set');self.store.save_mail_settings(payload,current['revision'],True)
        self.assertFalse(self.store.mail_settings()['config']['password_set'])

    def test_templates_reject_access_formatting_unknown_fields_and_header_injection(self):
        for subject in ['{meldung.__class__}','{meldung[0]}','{meldung!r}','{meldung:1000000}','{unknown}','{}','bad\r\nBcc: other@example.org','{']:
            with self.assertRaises(ValueError):validate_template({'subject':subject,'body':'Text'})
        validate_template({'subject':'{{literal}} {meldung}','body':'{empfaenger_name}\n{wert}'})

    def test_restart_recovers_inflight_job_without_replaying_existing_alarms(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.db';store=Store(path,[ALARM]);recipient(store);config(store);store.ingest(ALARM.group_address,1,'bus');store.claim_mail();store.close()
            store=Store(path,[ALARM]);sender=Mock()
            async def scenario():
                worker=MailWorker(store,sender);await worker.start();await asyncio.sleep(.05);await worker.stop()
            asyncio.run(scenario());self.assertEqual(sender.call_count,1);self.assertEqual(store.mail_settings()['counts'].get('sent'),1)
            store.ingest(ALARM.group_address,1,'bus');self.assertEqual(store.db.execute('SELECT count(*) FROM mail_outbox').fetchone()[0],1);store.close()

class SMTPTests(unittest.TestCase):
    def test_tls_modes_authentication_and_individual_recipients(self):
        base={'host':'smtp.example.org','port':587,'username':'login','password':'secret','from_email':'alarm@example.org','from_name':'Störungen'}
        job={'subject':'Neue Störung','body':'Text äöü','recipient':'person@example.org','message_id':'<stable@example.org>'}
        for mode in ['starttls','ssl','plain']:
            with patch('knx_alarmserver.mail.smtplib.SMTP') as plain,patch('knx_alarmserver.mail.smtplib.SMTP_SSL') as secure:
                send_smtp({**base,'security':mode},job);factory=secure if mode=='ssl' else plain;smtp=factory.return_value.__enter__.return_value
                smtp.login.assert_called_once_with('login','secret');self.assertEqual(smtp.starttls.call_count,1 if mode=='starttls' else 0)
                if mode=='ssl':self.assertIn('context',factory.call_args.kwargs)
                if mode=='starttls':self.assertIn('context',smtp.starttls.call_args.kwargs)
                args=smtp.send_message.call_args;self.assertEqual(args.kwargs['to_addrs'],['person@example.org']);self.assertEqual(str(args.args[0]['Message-ID']),job['message_id']);self.assertIn('Text äöü',args.args[0].get_content())
        with patch('knx_alarmserver.mail.smtplib.SMTP') as plain:
            smtp=plain.return_value.__enter__.return_value;smtp.starttls.side_effect=smtplib.SMTPNotSupportedError()
            with self.assertRaises(smtplib.SMTPNotSupportedError):send_smtp({**base,'security':'starttls'},job)
            smtp.login.assert_not_called();smtp.send_message.assert_not_called()

class MailAPI(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:',[ALARM])
        for role in ['admin','user','viewer']:self.store.set_password(role,PASSWORD,role)
        self.sender=Mock();self.patch=patch('knx_alarmserver.mail.send_smtp',self.sender);self.patch.start()
        self.client=TestClient(create_app({'knx':{'enabled':False}},self.store));self.client.__enter__();self.client.auth=('admin',PASSWORD)
    def tearDown(self):self.client.__exit__(None,None,None);self.patch.stop();self.store.close()

    def test_admin_permissions_csrf_secret_redaction_and_test_mail(self):
        for role in ['user','viewer']:
            for method,path in [('get','/mail'),('get','/api/mail'),('put','/api/mail'),('post','/api/mail/test'),('post','/api/mail/retry')]:
                response=self.client.request(method,path,auth=(role,PASSWORD),headers=ACTION,json={} if method!='get' else None)
                self.assertEqual(response.status_code,403,(role,path))
        self.assertEqual(self.client.get('/mail').status_code,200)
        self.assertEqual(self.client.post('/api/mail/retry').status_code,403)
        self.assertEqual(self.client.post('/api/mail/retry',headers={**ACTION,'Sec-Fetch-Site':'cross-site'}).status_code,403)
        config(self.store,password='private-secret',enabled=False)
        self.assertNotIn('private-secret',self.client.get('/api/mail').text)
        response=self.client.post('/api/mail/test',json={'recipient':'test@example.org'},headers=ACTION)
        self.assertEqual(response.status_code,200,response.text);self.sender.assert_called_once();self.assertEqual(self.sender.call_args.args[1]['recipient'],'test@example.org')
        self.assertEqual(self.client.post('/api/mail/test',json={'recipient':'invalid'},headers=ACTION).status_code,422)

    def test_configuration_put_checks_revision_validation_and_keeps_secret(self):
        current=self.client.get('/api/mail').json();proposed=copy.deepcopy(current['config']);proposed.pop('password_set');proposed.update(host='smtp.example.org',from_email='alarm@example.org',password='private-secret')
        payload={'config':proposed,'revision':current['revision']}
        self.assertEqual(self.client.put('/api/mail',json=payload).status_code,403)
        result=self.client.put('/api/mail',json=payload,headers=ACTION)
        self.assertEqual(result.status_code,200,result.text);self.assertNotIn('private-secret',result.text)
        self.assertEqual(self.client.put('/api/mail',json=payload,headers=ACTION).status_code,409)
        saved=result.json();proposed['password']='';proposed['enabled']=True;proposed['host']='https://smtp.example.org'
        bad=self.client.put('/api/mail',json={'config':proposed,'revision':saved['revision']},headers=ACTION)
        self.assertEqual(bad.status_code,422);self.assertEqual(self.store._mail_settings()['config']['password'],'private-secret')

    def test_user_opt_in_is_admin_only_validated_and_defaults_off(self):
        data={'username':'person@example.org','password':PASSWORD,'role':'user','first_name':'Ada','last_name':'Lovelace'}
        headers={'X-Alarmserver-Action':'manage-users'}
        self.assertEqual(self.client.post('/api/users',json={**data,'mail_enabled':'yes'},headers=headers).status_code,422)
        self.assertIsNone(self.store.account(data['username']))
        self.assertEqual(self.client.post('/api/users',json=data,headers=headers).status_code,200)
        person=next(r for r in self.client.get('/api/users').json() if r['username']==data['username']);self.assertFalse(person['mail_enabled'])
        self.assertEqual(self.client.put('/api/users/person@example.org',json={'role':'user','mail_enabled':True},headers=headers).status_code,200)
        self.assertTrue(next(r for r in self.store.users() if r['username']==data['username'])['mail_enabled'])
        self.assertEqual(self.client.put('/api/users/admin',json={'role':'admin','mail_enabled':True},headers=headers).status_code,422)
