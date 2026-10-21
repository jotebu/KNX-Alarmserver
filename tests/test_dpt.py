from dataclasses import replace
import unittest

try:
    from xknx.dpt import DPTArray
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from knx_alarmserver.dpt import catalog, decode, transcoder
from test_core import ALARM


@unittest.skipUnless(AVAILABLE, "xknx nicht installiert")
class DptTests(unittest.TestCase):
    def test_representative_scalar_types(self):
        for dpt, value in [("1.005",True),("5.001",50),("6.001",-12),("7.001",1234),
                           ("8.001",-1234),("9.001",23.5),("12.001",123456),
                           ("13.001",-123456),("14.056",1000.5),("16.001","Störung"),
                           ("17.001",5),("20.102",4)]:
            with self.subTest(dpt=dpt):
                codec = transcoder(dpt)
                decoded, display, unit = decode(dpt, codec.to_knx(value))
                if isinstance(value, (int,float)):
                    self.assertAlmostEqual(decoded, value, delta=.4 if dpt=='5.001' else .1)
                else:
                    self.assertEqual(decoded,value)
                self.assertTrue(display)

    def test_time_date_and_rgb_are_structured_json_values(self):
        for dpt, raw in [("10.001",(12,30,45)),("11.001",(21,10,26)),("232.600",(12,34,56))]:
            with self.subTest(dpt=dpt):
                value, display, unit = decode(dpt,DPTArray(raw))
                self.assertIsInstance(value,(dict,str))
                self.assertTrue(display)

    def test_unsupported_subtype_does_not_fall_back(self):
        with self.assertRaises(ValueError):
            transcoder("9.999")
        self.assertGreater(len(catalog()),50)

    def test_malformed_payload_rejected(self):
        with self.assertRaises(Exception):
            decode("9.001",DPTArray((1,)))
