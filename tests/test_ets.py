import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from xknx.telegram import Telegram, TelegramDirection, GroupAddress, IndividualAddress
from xknx.telegram.apci import GroupValueWrite
from knx_alarmserver.dpt import transcoder
from knx_alarmserver.ets import MAX_BYTES, parse_export
from knx_alarmserver.knx import Monitor
from knx_alarmserver.store import Store
from knx_alarmserver.web import create_app
from test_core import ALARM

XML = b'''<?xml version="1.0" encoding="utf-8"?>
<GroupAddress-Export xmlns="http://knx.org/xml/ga-export/01">
<GroupRange Name="Example"><GroupAddress Name="Temperature" Address="1/2/4" DPTs="DPST-9-1" Description="Room"/>
<GroupAddress Name="No type" Address="1/2/5"/>
<GroupAddress Name="Ambiguous" Address="1/2/6" DPTs="DPST-1-1,DPST-1-6"/>
</GroupRange></GroupAddress-Export>'''


class ParserTests(unittest.TestCase):
    def test_xml_namespace_dpts_and_missing_or_ambiguous_types(self):
        result = parse_export(XML, 'export.xml')
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['warnings'], 2)
        entries = result['entries']
        self.assertEqual(entries[0]['dpt'], '9.001')
        self.assertEqual(entries[0]['description'], 'Room')
        self.assertIsNone(entries[1]['dpt'])
        self.assertIsNone(entries[2]['dpt'])
        self.assertEqual(entries[2]['dpts'], ['1.001', '1.006'])

    def test_two_level_free_level_and_utf16(self):
        xml = '<GroupAddress-Export><GroupAddress Address="1/516" Name="A" DPTs="9.001"/></GroupAddress-Export>'
        a = parse_export(xml.encode('utf-16'), 'export.XML')['entries'][0]
        b = parse_export(xml.replace('1/516', '2564').encode(), 'export.xml')['entries'][0]
        self.assertEqual(a, b)
        self.assertEqual(a['address'], '1/2/4')

    def test_csv_ets_hierarchy_with_quotes_and_dpt(self):
        csv = '"Main";"Middle";"Sub";"Address";"DatapointType"\n"House";;;"1/-/-";\n;"Room";;"1/2/-";\n;;"Room; Temperature";"1/2/4";"DPST-9-1"\n'
        result = parse_export(csv.encode(), 'export.csv')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['entries'][0]['name'], 'Room; Temperature')
        self.assertEqual(result['entries'][0]['dpt'], '9.001')
        flat = 'Gruppenadresse\tName\tDPT\tBeschreibung\n1/2/4\tBüro\t9.001\tSüd\n'
        self.assertEqual(parse_export(flat.encode('cp1252'), 'export.csv')['entries'][0]['name'], 'Büro')

    def test_csv_one_three_and_one_one_styles(self):
        csv = 'Group name;Main;Sub;Address\nMain;1;;\nMiddle;1;2;\nSensor;1;2;4\n'
        row = parse_export(csv.encode(), 'export.csv')['entries'][0]
        self.assertEqual(row['address'], '1/2/4')
        self.assertEqual(row['name'], 'Sensor')
        flat = b'Group name,Address\nSensor,1/2/4\n'
        self.assertEqual(parse_export(flat, 'export.csv')['entries'][0]['address'], '1/2/4')

    def test_unsupported_or_invalid_dpt_is_retained_without_guessing(self):
        for token in ['DPST-9-999', 'wrong', 'DPST-9-1,wrong']:
            xml = f'<GroupAddress-Export><GroupAddress Address="1/2/4" DPTs="{token}"/></GroupAddress-Export>'
            row = parse_export(xml.encode(), 'export.xml')['entries'][0]
            self.assertIsNone(row['dpt'])
            self.assertTrue(row['warnings'])
            self.assertEqual(row['dpt_source'], token)

    def test_bad_files_fail_without_partial_results(self):
        for raw, name in [(b'PK', 'project.knxproj'), (b'', 'file.xml'),
                          (b'<KNX/>', 'project.xml'), (b'<bad', 'file.xml'),
                          (b'Name;foo\nx;y', 'file.csv'),
                          (b'x' * (MAX_BYTES+1), 'file.xml'),
                          (XML.replace(b'1/2/5', b'1/2/4'), 'file.xml'),
                          (XML.replace(b'1/2/5', b'32/0/0'), 'file.xml')]:
            with self.subTest(name=name, sample=raw[:30]), self.assertRaises(ValueError):
                parse_export(raw, name)

    def test_dtd_entities_rejected_in_utf8_and_utf16(self):
        xml = '<!DOCTYPE GroupAddress-Export [<!ENTITY x "expanded">]><GroupAddress-Export><GroupAddress Address="1" Name="&x;"/></GroupAddress-Export>'
        for encoding in ('utf-8', 'utf-16'):
            with self.assertRaisesRegex(ValueError, 'DTD'):
                parse_export(xml.encode(encoding), 'file.xml')


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'store.sqlite3'
        self.store = Store(self.path, [])
        self.store.set_password('admin', 'test-password-123')
        self.client = TestClient(create_app({'knx': {'enabled': False}}, self.store))
        self.client.__enter__()
        self.auth = ('admin', 'test-password-123')
        self.headers = {'X-Alarmserver-Action': 'import-ets'}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.store.close()
        self.temp.cleanup()

    def preview(self, raw=XML):
        return self.client.post('/api/ets/preview?filename=export.xml', content=raw, auth=self.auth, headers=self.headers)

    def apply(self, preview, raw=XML, mode='merge'):
        return self.client.post('/api/ets/import', params={
            'filename':'export.xml', 'revision':preview['revision'], 'digest':preview['digest'], 'mode':mode
        }, content=raw, auth=self.auth, headers=self.headers)

    def test_preview_commit_reimport_persist_and_backup(self):
        preview = self.preview().json()
        self.assertEqual(self.store.ets_catalog()['count'], 0)
        self.assertEqual(preview['entries'][0]['change'], 'new')
        self.assertEqual(self.apply(preview).json()['added'], 3)
        self.assertEqual(self.store.snapshot(), [])
        second = self.preview().json()
        self.assertEqual(second['entries'][0]['change'], 'unchanged')
        self.assertEqual(self.apply(second).json()['updated'], 0)
        backup = Path(self.temp.name)/'backup.sqlite3'
        self.store.backup(backup)
        for path in (self.path, backup):
            restored = Store(path, [])
            self.assertEqual(restored.ets_point('1/2/4')['dpt'], '9.001')
            restored.close()

    def test_auth_csrf_limits_conflict_and_changed_file(self):
        self.assertEqual(self.client.get('/api/ets').status_code, 401)
        path = '/api/ets/preview?filename=export.xml'
        self.assertEqual(self.client.post(path, content=XML).status_code, 401)
        self.assertEqual(self.client.post(path, content=XML, auth=self.auth).status_code, 403)
        self.assertEqual(self.client.post(path, content=XML, auth=self.auth, headers={
            **self.headers, 'Sec-Fetch-Site':'cross-site'}).status_code, 403)
        self.assertEqual(self.client.post(path, content=b'x'*(MAX_BYTES+1), auth=self.auth, headers=self.headers).status_code, 413)
        preview = self.preview().json()
        self.assertEqual(self.apply(preview, XML.replace(b'Temperature', b'Changed')).status_code, 409)
        self.assertEqual(self.apply(preview).status_code, 200)
        self.assertEqual(self.apply(preview).status_code, 409)

    def test_merge_replace_and_invalid_file_are_atomic(self):
        self.assertEqual(self.apply(self.preview().json()).status_code, 200)
        raw = b'<GroupAddress-Export><GroupAddress Name="New" Address="3/0/1" DPTs="DPST-1-1"/></GroupAddress-Export>'
        self.assertEqual(self.apply(self.preview(raw).json(), raw).json()['count'], 4)
        self.assertEqual(self.apply(self.preview(raw).json(), raw, 'replace').json()['removed'], 3)
        before = self.store.ets_catalog()
        self.assertEqual(self.preview(b'<broken').status_code, 422)
        self.assertEqual(self.store.ets_catalog(), before)
        from contextlib import contextmanager
        @contextmanager
        def failed_transaction():
            raise RuntimeError('disk unavailable')
            yield
        with patch.object(self.store, 'transaction', failed_transaction):
            with self.assertRaises(RuntimeError):
                self.store.import_ets(parse_export(XML, 'export.xml')['entries'], before['revision'], 'merge')
        self.assertEqual(self.store.ets_catalog(), before)


class ReceptionTests(unittest.TestCase):
    def test_imported_point_decodes_without_alarm_and_alarm_rules_keep_priority(self):
        for alarms in ([], [ALARM]):
            store = Store(':memory:', alarms)
            try:
                entries = parse_export(XML.replace(b'1/2/4', b'1/2/3'), 'export.xml')['entries']
                store.import_ets(entries, store.ets_catalog()['revision'], 'merge')
                monitor = Monitor({'enabled':False}, store)
                monitor.connections['test'] = {'name':'test', 'state':'CONNECTED'}
                dpt, value = ('1.005', True) if alarms else ('9.001', 23.5)
                telegram = Telegram(destination_address=GroupAddress('1/2/3'), source_address=IndividualAddress('1.1.1'),
                                    direction=TelegramDirection.INCOMING, payload=GroupValueWrite(transcoder(dpt).to_knx(value)))
                monitor.received(telegram, 'test')
                row = monitor.telegrams[0]
                self.assertEqual(row['dpt'], dpt)
                self.assertAlmostEqual(row['value'], value)
                self.assertEqual(row['name'], ALARM.name if alarms else 'Temperature')
                self.assertEqual(len(store.snapshot()), len(alarms))
                self.assertIsNone(row['error'])
            finally:
                store.close()
