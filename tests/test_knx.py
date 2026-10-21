import unittest

try:
    from xknx import XKNX
    from xknx.dpt import DPTBinary, DPTArray
    from xknx.io import ConnectionConfig, ConnectionType
    from xknx.telegram import Telegram, TelegramDirection, GroupAddress, IndividualAddress
    from xknx.telegram.apci import GroupValueWrite, GroupValueRead, GroupValueResponse
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from knx_alarmserver.knx import Monitor
from knx_alarmserver.store import Store
from test_core import ALARM


@unittest.skipUnless(AVAILABLE, "xknx nicht installiert")
class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:", [ALARM])
        self.monitor = Monitor({"enabled": True}, self.store)
        self.monitor.connections["test"] = {"name": "test", "state": "CONNECTED"}

    def tearDown(self):
        self.store.close()

    def telegram(self, payload, direction=None):
        return Telegram(destination_address=GroupAddress("1/2/3"), source_address=IndividualAddress("1.1.1"),
                        direction=direction or TelegramDirection.INCOMING, payload=payload)

    def test_write_and_response_update_alarm(self):
        self.monitor.received(self.telegram(GroupValueWrite(DPTBinary(1))), "test")
        self.assertEqual(self.store.snapshot()[0]["status"], "active")
        self.monitor.received(self.telegram(GroupValueResponse(DPTBinary(0))), "test")
        self.assertEqual(self.store.snapshot()[0]["status"], "clear_pending")

    def test_ignore_read_outgoing_and_multibyte_payload(self):
        for telegram in [self.telegram(GroupValueRead()), self.telegram(GroupValueWrite(DPTArray((1,)))),
                         self.telegram(GroupValueWrite(DPTBinary(1)), TelegramDirection.OUTGOING)]:
            self.monitor.received(telegram, "test")
        self.assertEqual(self.store.snapshot()[0]["status"], "unknown")

    def test_monitor_ring_is_bounded(self):
        for _ in range(300):
            self.monitor.received(self.telegram(GroupValueRead()), "test")
        self.assertEqual(len(self.monitor.telegrams), 250)

    def test_pinned_library_connection_api(self):
        # Real xknx objects, no sockets; detects incompatible constructor changes in CI.
        for kind, kwargs in [(ConnectionType.TUNNELING, {"gateway_ip": "192.0.2.1"}),
                             (ConnectionType.ROUTING, {"individual_address": "1.0.250"})]:
            XKNX(connection_config=ConnectionConfig(connection_type=kind, **kwargs),
                 telegram_received_cb=lambda t: None, state_updater=False)
