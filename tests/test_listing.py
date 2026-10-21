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
            rows[0].update(status='normal',quality='ok',last_seen='2026-10-21T10:00:00.000000+00:00')
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
