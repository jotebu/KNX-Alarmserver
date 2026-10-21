import csv
from pathlib import Path
import tempfile
import unittest

from knx_alarmserver.config import Alarm, load_alarms, load_config
from knx_alarmserver.store import Store

ALARM = Alarm("pump", "Pumpe", "1/2/3", "1.005", "eq", 1, 0, "", "Technik", "critical")


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.store = Store(self.path, [ALARM])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def state(self):
        return self.store.snapshot()[0]

    def test_unknown_is_not_normal(self):
        self.assertEqual(self.state()["status"], "unknown")
        self.assertFalse(self.state()["fresh"])

    def test_active_acknowledged_and_clear(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.assertEqual(self.state()["status"], "active")
        self.assertTrue(self.store.acknowledge("pump", "andy"))
        self.assertEqual(self.state()["status"], "active_ack")
        self.store.ingest("1/2/3", 0, "1.1.1")
        self.assertEqual(self.state()["status"], "normal")
        ack = next(e for e in self.store.history() if e["kind"] == "acknowledge")
        self.assertEqual(ack["username"], "andy")
        self.assertTrue(ack["timestamp"])

    def test_clear_before_ack_is_latched(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.store.ingest("1/2/3", 0, "1.1.1")
        self.assertEqual(self.state()["status"], "clear_pending")
        self.store.acknowledge("pump", "andy")
        self.assertEqual(self.state()["status"], "normal")

    def test_recurrence_requires_new_ack(self):
        for value in (1, 0):
            self.store.ingest("1/2/3", value, "1.1.1")
        self.store.acknowledge("pump", "andy")
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.assertEqual(self.state()["status"], "active")
        self.assertIsNone(self.state()["acknowledged_by"])

    def test_repeated_telegram_and_ack_are_idempotent(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.assertFalse(self.store.ingest("1/2/3", 1, "1.1.2"))
        self.assertEqual(len(self.store.history()), 1)
        self.store.acknowledge("pump", "andy")
        self.assertFalse(self.store.acknowledge("pump", "other"))
        self.assertEqual(self.state()["acknowledged_by"], "andy")

    def test_restart_preserves_state_but_marks_it_old(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.store.close()
        self.store = Store(self.path, [ALARM])
        self.assertEqual(self.state()["status"], "active")
        self.assertFalse(self.state()["fresh"])
        self.store.ingest("1/2/3", 1, "1.1.1")
        self.assertTrue(self.state()["fresh"])

    def test_backup_includes_wal_data(self):
        self.store.ingest("1/2/3", 1, "1.1.1")
        target = Path(self.temp.name) / "backup.sqlite3"
        self.store.backup(target)
        restored = Store(target, [ALARM])
        try:
            self.assertEqual(restored.snapshot()[0]["status"], "active")
        finally:
            restored.close()

    def test_unknown_address_and_invalid_value(self):
        self.assertFalse(self.store.ingest("0/0/1", 1, "1.1.1"))
        for value in (float('nan'), float('inf'), object()):
            with self.assertRaises(ValueError):
                self.store.ingest("1/2/3", value, "1.1.1")

    def test_active_low(self):
        store = Store(":memory:", [Alarm("contact", "Kontakt", "1/2/4", "1.002", "eq", 0, 0, "", "UG", "warning")])
        try:
            store.ingest("1/2/4", 0, "1.1.1")
            self.assertEqual(store.snapshot()[0]["status"], "active")
        finally:
            store.close()

    def test_password_hashing_and_authentication(self):
        self.assertFalse(self.store.has_users())
        self.store.set_password("andy", "test-password-123")
        self.assertTrue(self.store.authenticate("andy", "test-password-123"))
        self.assertFalse(self.store.authenticate("andy", "wrong"))
        self.assertFalse(self.store.authenticate("unknown", "test-password-123"))
        with self.assertRaises(ValueError):
            self.store.set_password("andy", "short")

    def test_definition_change_cannot_reinterpret_existing_state(self):
        changed = Alarm("pump", "Pumpe", "1/2/4", "1.005", "eq", 1, 0, "", "Technik", "critical")
        with self.assertRaises(ValueError):
            Store(self.path, [changed])


class ConfigurationTests(unittest.TestCase):
    def test_examples_and_default_config(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(len(load_alarms(root / "config/alarms.csv")), 0)
        self.assertEqual(len(load_alarms(root / "config/alarms.example.csv")), 7)
        self.assertFalse(load_config(root / "config/config.example.toml")["knx"]["enabled"])

    def test_bad_matrix_rejected_whole(self):
        header = "id;name;group_address;dpt;operator;threshold;hysteresis;field;area;priority\n"
        good = "pump;Pumpe;1/2/3;1.005;eq;1;0;;UG;critical\n"
        bad_rows = ["x;X;32/0/1;1.005;eq;1;0;;UG;critical\n", "x;X;1/2/4;bad;eq;1;0;;UG;critical\n",
                    good, "x;X;01/2/3;1.005;eq;1;0;;UG;critical\n", "x;X;1/2/4;9.001;gt;abc;0;;UG;critical\n"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.csv"
            for bad in bad_rows:
                path.write_text(header + good + bad, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_alarms(path)


if __name__ == "__main__":
    unittest.main()
