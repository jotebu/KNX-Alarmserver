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
