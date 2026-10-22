from dataclasses import replace
from datetime import datetime, timezone
import unittest
from knx_alarmserver.store import Store
from knx_alarmserver.listing import alarms_page, bounds
from test_core import ALARM

class ListingTests(unittest.TestCase):
    def test_all_history_pages_dates_and_literal_search(self):
        store=Store(':memory:',[ALARM])
        try:
            with store.transaction():
                for i in range(501):
                    store._event(ALARM,'active',f'2026-10-{20 if i<250 else 21}T12:00:00.000000+00:00',username='a%_b')
            pages=[store.history_page(page) for page in [1,2,3]]
            self.assertEqual([len(page['rows']) for page in pages],[200,200,101])
            self.assertEqual(len({row['seq'] for page in pages for row in page['rows']}),501)
            self.assertEqual((pages[1]['first'],pages[1]['last']),(201,400))
            start,end=bounds(datetime(2026,10,21,tzinfo=timezone.utc),datetime(2026,10,22,tzinfo=timezone.utc))
            self.assertEqual(store.history_page(start=start,end=end)['total'],251)
            self.assertEqual(store.history_page(query='%_')['total'],501)
            self.assertEqual(store.history_page(query='missing')['total'],0)
            self.assertEqual(store.history_page(999)['page'],3)
            with self.assertRaises(ValueError):bounds(datetime(2026,10,21),None)
            with self.assertRaises(ValueError):bounds(datetime(2026,10,22,tzinfo=timezone.utc),datetime(2026,10,21,tzinfo=timezone.utc))
        finally:store.close()

    def test_alarm_pages_date_field_and_open_filter(self):
        alarms=[replace(ALARM,id=f'p{i}',group_address=f'{i//2048}/{i//256%8}/{i%256}') for i in range(466)]
        store=Store(':memory:',alarms)
        try:
            rows=store.snapshot()
            self.assertEqual([len(alarms_page(rows,p)['rows']) for p in [1,2,3]],[200,200,66])
            self.assertEqual(alarms_page(rows,start='2026')['total'],0)
            self.assertEqual(alarms_page(rows,query='not found')['total'],0)
            rows[0].update(status='normal',quality='ok',last_seen='2026-10-21T10:00:00.000000+00:00',changed_at='2026-10-21T10:00:00.000000+00:00')
            self.assertEqual(alarms_page(rows,open_only=True)['total'],465)
            self.assertEqual(alarms_page(rows,start='2026-10-21',end='2026-10-22')['total'],1)
        finally:store.close()

    def test_paged_dashboard_preserves_full_counters_and_validates_dates(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        store=Store(':memory:',[ALARM]);store.create_user('reader','test-password-123','viewer')
        try:
            with TestClient(create_app({'knx':{'enabled':False}},store)) as client:
                auth=('reader','test-password-123')
                response=client.get('/api/dashboard?paged=true&view=alarms',auth=auth)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['pagination']['page_size'],200)
                self.assertEqual(response.json()['counts']['unknown'],1)
                self.assertEqual(client.get('/api/dashboard?paged=true&from_time=2026-01-01',auth=auth).status_code,422)
                self.assertEqual(client.get('/api/dashboard?paged=true&page=0',auth=auth).status_code,422)
                self.assertEqual(client.post('/api/knx/read',auth=auth,json={'mode':'all','connection':''},headers={'X-Alarmserver-Action':'read-knx'}).status_code,403)
        finally:store.close()

    def test_scroll_lists_return_all_alarms_and_search_history_before_limit(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        alarms=[replace(ALARM,id=f'p{i}',name=f'Alarm {i}',group_address=f'{i//2048}/{i//256%8}/{i%256}') for i in range(601)]
        store=Store(':memory:',alarms);store.create_user('reader','test-password-123','viewer')
        try:
            with store.transaction():
                store.db.execute("UPDATE states SET active=1,pending=1,last_seen='2026-10-21T12:00:00+00:00'")
                store._event(replace(ALARM,name='Alter Sondertreffer'),'active','2026-10-20T12:00:00+00:00')
                for i in range(600):store._event(ALARM,'active','2026-10-21T12:00:00+00:00')
            with TestClient(create_app({'knx':{'enabled':False}},store)) as client:
                def get(view,extra=''):
                    response=client.get('/api/dashboard?list_mode=true&view='+view+extra,auth=('reader','test-password-123'))
                    self.assertEqual(response.status_code,200,response.text)
                    return response.json()
                result=get('alarms')
                self.assertEqual(len(result['alarms']),601)
                self.assertEqual(result['list_info'],{'total':601,'shown':601,'limit':None})
                self.assertEqual(result['counts']['active'],601)
                history=get('history')
                self.assertEqual(len(history['history']),500)
                self.assertEqual(history['list_info'],{'total':601,'shown':500,'limit':500})
                self.assertNotIn('pagination',history)
                found=get('history','&search=Sondertreffer')
                self.assertEqual(len(found['history']),1)
                self.assertEqual(found['history'][0]['alarm_name'],'Alter Sondertreffer')
                dated=get('history','&until_time=2026-10-21T00:00:00Z')
                self.assertEqual(dated['list_info']['total'],1)
                self.assertEqual(len(get('alarms','&search=notfound')['alarms']),0)
        finally:store.close()

    def test_incident_list_excludes_normal_unknown_and_sorts_priority_then_time(self):
        def row(identifier,priority,status,time,quality='ok'):
            return {'id':identifier,'name':identifier,'priority':priority,'status':status,'last_seen':time,'changed_at':time,'quality':quality}
        rows=[row('normal',1,'normal','2026-10-22T13:00:00+00:00','restored'),
              row('unknown',1,'unknown',None,'unseen'),
              row('low-new',4,'active','2026-10-22T14:00:00+00:00'),
              row('high-old',1,'active_ack','2026-10-21T10:00:00+00:00'),
              row('high-new',1,'clear_pending','2026-10-22T11:00:00+00:00'),
              row('high-middle',1,'active','2026-10-22T10:00:00+00:00')]
        result=alarms_page(rows,unlimited=True,incidents_only=True)
        self.assertEqual([r['id'] for r in result['rows']],['high-new','high-middle','high-old','low-new'])
        self.assertEqual(result['total'],4)
        self.assertEqual(alarms_page(rows,query='normal',unlimited=True,incidents_only=True)['total'],0)

    def test_status_card_filters_and_unknown_count_ignore_restart(self):
        from fastapi.testclient import TestClient
        from knx_alarmserver.web import create_app
        alarms=[replace(ALARM,id=f's{i}',group_address=f'1/2/{i}') for i in range(5)]
        store=Store(':memory:',alarms);store.create_user('reader','test-password-123','viewer')
        try:
            with store.transaction():
                for i,(active,pending) in enumerate([(1,1),(1,0),(0,1),(0,0)]):
                    store.db.execute("UPDATE states SET active=?,pending=?,last_seen='2020-01-01T00:00:00+00:00' WHERE id=?",(active,pending,f's{i}'))
            self.assertEqual(store.snapshot()[0]['quality'],'ok')
            with TestClient(create_app({'knx':{'enabled':False}},store)) as client:
                for status,identifier in [('active','s0'),('active_ack','s1'),('clear_pending','s2'),('unknown','s4')]:
                    response=client.get('/api/dashboard?list_mode=true&status_filter='+status,auth=('reader','test-password-123'))
                    self.assertEqual(response.status_code,200,response.text)
                    body=response.json()
                    self.assertEqual([row['id'] for row in body['alarms']],[identifier])
                    self.assertEqual(body['counts'],{'active':1,'acked':1,'pending':1,'unknown':1})
                self.assertEqual(client.get('/api/dashboard?list_mode=true&status_filter=normal',auth=('reader','test-password-123')).status_code,422)
        finally:store.close()

    def test_incident_timestamp_survives_repeats_reads_ack_and_restart(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as folder:
            path=Path(folder)/'alarm.sqlite3'
            store=Store(path,[ALARM])
            first='2026-10-21T10:00:00.000000+00:00'
            repeated='2026-10-22T11:00:00.000000+00:00'
            cleared='2026-10-22T12:00:00.000000+00:00'
            try:
                with patch('knx_alarmserver.store.now',return_value=first):store.ingest(ALARM.group_address,1,'1.1.1')
                with patch('knx_alarmserver.store.now',return_value=repeated):
                    self.assertFalse(store.ingest(ALARM.group_address,1,'1.1.2'))
                    store.acknowledge(ALARM.id,'andy')
                    self.assertFalse(store.ingest(ALARM.group_address,1,'1.1.2'))
                row=store.snapshot()[0]
                self.assertEqual(row['changed_at'],first)
                self.assertEqual(row['last_seen'],repeated)
                self.assertEqual(row['acknowledged_at'],repeated)
                self.assertEqual(len(store.history()),2)
                self.assertEqual(alarms_page([row],start='2026-10-22',unlimited=True)['total'],0)
                self.assertEqual(alarms_page([row],start='2026-10-21',end='2026-10-22',unlimited=True)['total'],1)
            finally:store.close()
            store=Store(path,[ALARM])
            try:
                self.assertEqual(store.snapshot()[0]['changed_at'],first)
                with patch('knx_alarmserver.store.now',return_value=cleared):store.ingest(ALARM.group_address,0,'1.1.1')
                self.assertEqual(store.snapshot()[0]['changed_at'],cleared)
            finally:store.close()
        rows=[{'id':'older','priority':1,'status':'active','quality':'ok','last_seen':repeated,'changed_at':first},
              {'id':'newer','priority':1,'status':'active','quality':'ok','last_seen':first,'changed_at':repeated}]
        self.assertEqual([r['id'] for r in alarms_page(rows,unlimited=True)['rows']],['newer','older'])

    def test_read_api_roles_headers_and_reported_start(self):
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from knx_alarmserver.web import create_app
        store=Store(':memory:',[ALARM])
        for role in ['admin','user']:store.create_user(role,'test-password-123',role)
        app=create_app({'knx':{'enabled':False}},store)
        try:
            with TestClient(app) as client:
                payload={'mode':'unknown','connection':''};headers={'X-Alarmserver-Action':'read-knx'}
                auth=('admin','test-password-123')
                self.assertEqual(client.post('/api/knx/read',auth=auth,json=payload).status_code,403)
                self.assertEqual(client.post('/api/knx/read',auth=auth,json=payload,headers=headers).status_code,503)
                self.assertEqual(client.post('/api/knx/read',auth=auth,json={'mode':[],'connection':''},headers=headers).status_code,422)
                with patch.object(app.state.monitor,'request_read',return_value={'state':'running','total':1}) as request:
                    for role in ['admin','user']:
                        response=client.post('/api/knx/read',auth=(role,'test-password-123'),json=payload,headers=headers)
                        self.assertEqual(response.status_code,202)
                        self.assertEqual(response.json()['state'],'running')
                    request.assert_called_with('unknown','')
        finally:store.close()
