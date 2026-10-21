from dataclasses import replace
from datetime import date
from enum import Enum
import unittest

from knx_alarmserver.rules import evaluate, normalized, validate_rule
from knx_alarmserver.store import Store
from test_core import ALARM


class RuleTests(unittest.TestCase):
    def test_upper_limit_hysteresis(self):
        alarm = replace(ALARM, dpt="9.001", operator="gt", threshold=50, hysteresis=2)
        store = Store(":memory:", [alarm])
        try:
            for value, expected in [(49, 'normal'), (50, 'normal'), (51, 'active'), (49, 'active'), (48, 'clear_pending')]:
                store.ingest("1/2/3", value, "1.1.1")
                self.assertEqual(store.snapshot()[0]["status"], expected)
                self.assertEqual(store.snapshot()[0]["value"], value)
        finally:
            store.close()

    def test_lower_limit_and_ranges(self):
        self.assertTrue(evaluate(replace(ALARM, operator="lt", threshold=10), 9))
        self.assertTrue(evaluate(replace(ALARM, operator="le", threshold=10), 10))
        self.assertTrue(evaluate(replace(ALARM, operator="ge", threshold=10), 10))
        alarm = replace(ALARM, operator="outside", threshold=[20,80], hysteresis=3)
        self.assertFalse(evaluate(alarm, 22))
        self.assertTrue(evaluate(alarm, 22, True))
        self.assertFalse(evaluate(alarm, 23, True))
        alarm = replace(alarm, operator="between")
        self.assertFalse(evaluate(alarm, 18))
        self.assertTrue(evaluate(alarm, 18, True))

    def test_text_enum_compound_and_monitor(self):
        self.assertTrue(evaluate(replace(ALARM, operator="contains", threshold="Störung"), "Pumpe Störung"))
        self.assertTrue(evaluate(replace(ALARM, operator="in", threshold=[1,4]), 4))
        self.assertTrue(evaluate(replace(ALARM, operator="eq", threshold=True, field="control"), {"control":True,"value":False}))
        self.assertTrue(evaluate(replace(ALARM, operator="eq", threshold=3, field="items.0"), {"items":[3]}))
        self.assertFalse(evaluate(replace(ALARM, operator="monitor"), {"date":"2026-10-21"}))
        with self.assertRaises(ValueError):
            evaluate(replace(ALARM, field="missing"), {"present":1})
        with self.assertRaises(ValueError):
            evaluate(replace(ALARM, operator="gt"), "not numeric")

    def test_invalid_rules_rejected(self):
        for alarm in [replace(ALARM, operator="eval"),replace(ALARM, operator="eq",hysteresis=1),
                      replace(ALARM, operator="gt",threshold="hot"),replace(ALARM, operator="outside",threshold=[1,2],hysteresis=1),
                      replace(ALARM,hysteresis=float('nan'))]:
            with self.assertRaises(ValueError):
                validate_rule(alarm)

    def test_decode_error_preserves_alarm_and_is_visible_until_valid_value(self):
        store = Store(":memory:", [ALARM])
        try:
            store.ingest("1/2/3", 1, "1.1.1")
            store.decode_failed("1/2/3", "invalid length")
            self.assertEqual(store.snapshot()[0]["status"], "active")
            self.assertEqual(store.snapshot()[0]["quality"], "decode_error")
            store.ingest("1/2/3", 1, "1.1.1")
            self.assertEqual(store.snapshot()[0]["quality"], "ok")
        finally:
            store.close()

    def test_normalization(self):
        class Mode(Enum):
            ERROR = 4
        self.assertEqual(normalized(Mode.ERROR),4)
        self.assertEqual(normalized(date(2026,10,21)),"2026-10-21")
