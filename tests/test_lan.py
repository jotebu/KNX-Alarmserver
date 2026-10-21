import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest

from knx_alarmserver.config import load_config

spec = importlib.util.spec_from_file_location("enable_lan", Path(__file__).resolve().parents[1] / "scripts/enable_lan.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class LanConfigurationTests(unittest.TestCase):
    def test_existing_settings_and_permissions_survive_repeated_migration(self):
        source = '# Comment\n[server]\nhost = "127.0.0.1" # old\nport = 8181\ndatabase = "/custom/data.sqlite3"\n[knx]\nenabled = false\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source)
            path.chmod(0o640)
            expected = tomllib.loads(source)
            expected["server"]["host"] = "0.0.0.0"
            migration.enable_lan(path)
            first = path.read_text()
            migration.enable_lan(path)
            self.assertEqual(path.read_text(), first)
            self.assertEqual(tomllib.loads(first), expected)
            self.assertIn("# Comment", first)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_missing_host_and_explicit_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[server]\nport = 8080\n")
            self.assertEqual(load_config(path)["server"]["host"], "0.0.0.0")
            migration.enable_lan(path)
            self.assertEqual(tomllib.loads(path.read_text())["server"]["host"], "0.0.0.0")
            path.write_text('[server]\nhost = "127.0.0.1"\n')
            self.assertEqual(load_config(path)["server"]["host"], "127.0.0.1")

    def test_invalid_input_is_not_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            for source in ('[server\n', '[knx]\nenabled = false\n'):
                path.write_text(source)
                with self.assertRaises(ValueError):
                    migration.enable_lan(path)
                self.assertEqual(path.read_text(), source)



class PortConfigurationTests(unittest.TestCase):
    def test_port_defaults_to_80_and_explicit_ports_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_text('[server]\n')
            self.assertEqual(load_config(path)['server']['port'], 80)
            path.write_text('[server]\nport = 8080\n')
            self.assertEqual(load_config(path)['server']['port'], 8080)

    def test_migrate_port_only_or_together_with_lan_without_data_changes(self):
        source = '# Preserve comment\n[server]\nhost = "127.0.0.1"\nport = 8080 # old\ndatabase = "/custom/data.db"\nalarms = "/custom/alarms.csv"\n[knx]\nenabled = false\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_text(source)
            path.chmod(0o640)
            expected = tomllib.loads(source)
            expected['server']['port'] = 80
            migration.configure_server(path, port=80)
            self.assertEqual(tomllib.loads(path.read_text()), expected)
            expected['server']['host'] = '0.0.0.0'
            migration.configure_server(path, host='0.0.0.0', port=80)
            first = path.read_text()
            migration.configure_server(path, host='0.0.0.0', port=80)
            self.assertEqual(path.read_text(), first)
            self.assertEqual(tomllib.loads(first), expected)
            self.assertIn('# Preserve comment', first)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_missing_keys_are_inserted_in_server_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            for source in ('[server]', '[server]\n[knx]\nenabled = false\n'):
                path.write_text(source)
                migration.configure_server(path, host='0.0.0.0', port=80)
                self.assertEqual(tomllib.loads(path.read_text())['server'], {'host':'0.0.0.0','port':80})

    def test_invalid_or_ambiguous_port_does_not_change_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            original = '[server]\nport = 8080\n'
            for port in (0,65536,True,'80'):
                path.write_text(original)
                with self.assertRaises(ValueError):
                    migration.configure_server(path, port=port)
                self.assertEqual(path.read_text(), original)
            original = '[server]\n"port" = 8080\n'
            path.write_text(original)
            with self.assertRaises(ValueError):
                migration.configure_server(path, port=80)
            self.assertEqual(path.read_text(), original)
