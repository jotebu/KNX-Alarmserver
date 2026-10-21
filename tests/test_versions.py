from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from knx_alarmserver.store import Store
from knx_alarmserver.versions import VersionChecker,version_number,fetch_text
from knx_alarmserver.web import create_app


class Versions(unittest.TestCase):
    def test_numeric_ordering_and_validation(self):
        self.assertGreater(version_number('0.10.10'),version_number('0.10.09'))
        self.assertEqual(version_number('0.10.01'),version_number('0.10.1'))
        for value in ('v0.10.10','0.10.10;rm',None,'0.10',[],'1.1.'+'9'*9):
            with self.assertRaises(ValueError):version_number(value)

    def test_newer_equal_older_and_cached_request(self):
        for latest,expected in [('0.10.11',True),('0.10.10',False),('0.10.09',False)]:
            checker=VersionChecker()
            with patch('knx_alarmserver.versions.__version__','0.10.10'),patch('knx_alarmserver.versions.fetch_text',return_value=f'[project]\nversion="{latest}"\n') as fetch:
                result=checker.check();checker.check()
            self.assertTrue(result['check_ok'])
            self.assertEqual(result['update_available'],expected)
            self.assertEqual(fetch.call_count,1)

    def test_forced_check_replaces_cached_result(self):
        checker=VersionChecker()
        with patch('knx_alarmserver.versions.__version__','0.10.10'),patch('knx_alarmserver.versions.fetch_text',side_effect=['[project]\nversion="0.10.11"','[project]\nversion="0.10.10"']) as fetch:
            self.assertTrue(checker.check()['update_available'])
            self.assertTrue(checker.check()['update_available'])
            self.assertFalse(checker.check(force=True)['update_available'])
            self.assertEqual(fetch.call_count,2)

    def test_failure_and_local_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'CHANGELOG.md';path.write_text('# Changelog\n## 0.10.10\n- local')
            checker=VersionChecker(path)
            with patch('knx_alarmserver.versions.fetch_text',side_effect=OSError('offline')):
                result=checker.history()
            self.assertFalse(result['check_ok'])
            self.assertFalse(result['update_available'])
            self.assertIsNone(result['latest_version'])
            self.assertEqual(result['history_source'],'local')
            self.assertIn('- local',result['changelog'])

    def test_metadata_fetch_has_fresh_api_request_and_raw_fallback(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'[project]\nversion="0.10.14"'
        with patch('knx_alarmserver.versions.urllib.request.urlopen',side_effect=[OSError('api unavailable'),response]) as fetch:
            result=fetch_text('pyproject.toml')
        self.assertIn('0.10.14',result)
        first,second=[call.args[0] for call in fetch.call_args_list]
        self.assertIn('api.github.com/repos/jotebu/KNX-Alarmserver/contents/pyproject.toml?ref=main&_',first.full_url)
        self.assertIn('raw.githubusercontent.com',second.full_url)
        self.assertEqual(first.get_header('Cache-control'),'no-cache')
        self.assertIn('_=',second.full_url)

    def test_manual_history_request_bypasses_both_caches(self):
        checker=VersionChecker()
        store=Store(':memory:',[])
        store.set_password('admin','test-password-123')
        resources=['[project]\nversion="0.10.10"','# Changelog\n## 0.10.10',
                   '[project]\nversion="0.10.11"','# Changelog\n## 0.10.11','[project]\nversion="0.10.12"']
        try:
            with patch('knx_alarmserver.versions.__version__','0.10.10'),patch('knx_alarmserver.versions.fetch_text',side_effect=resources) as fetch:
                with TestClient(create_app({'knx':{'enabled':False}},store,version_checker=checker)) as client:
                    auth=('admin','test-password-123')
                    first=client.get('/api/versions',auth=auth).json()
                    cached=client.get('/api/versions',auth=auth).json()
                    fresh=client.get('/api/versions?refresh=true',auth=auth).json()
                    reopened=client.get('/api/version?refresh=true',auth=auth).json()
            self.assertFalse(first['update_available'])
            self.assertFalse(cached['update_available'])
            self.assertTrue(fresh['update_available'])
            self.assertIn('0.10.11',fresh['changelog'])
            self.assertEqual(reopened['latest_version'],'0.10.12')
            self.assertEqual(fetch.call_count,5)
        finally:store.close()

    def test_all_roles_can_read_versions_but_not_trigger_update(self):
        checker=VersionChecker()
        with patch('knx_alarmserver.versions.fetch_text',side_effect=lambda name:'[project]\nversion="0.10.10"\n' if name=='pyproject.toml' else '# Changelog\n- change'):
            store=Store(':memory:',[])
            for role in ('admin','user','viewer'):store.set_password(role,'test-password-123',role)
            try:
                with TestClient(create_app({'knx':{'enabled':False}},store,version_checker=checker)) as client:
                    self.assertEqual(client.get('/api/version').status_code,401)
                    self.assertEqual(client.get('/api/versions').status_code,401)
                    for role in ('admin','user','viewer'):
                        auth=(role,'test-password-123')
                        self.assertEqual(client.get('/versions',auth=auth).status_code,200)
                        self.assertEqual(client.get('/api/version',auth=auth).status_code,200)
                        self.assertEqual(client.get('/api/versions',auth=auth).status_code,200)
                        if role!='admin':
                            self.assertEqual(client.get('/api/update',auth=auth).status_code,403)
                            self.assertEqual(client.post('/api/update',auth=auth,headers={'X-Alarmserver-Action':'update-server'}).status_code,403)
            finally:store.close()
