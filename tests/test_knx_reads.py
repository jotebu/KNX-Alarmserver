import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import unittest
from knx_alarmserver.knx import Monitor
from knx_alarmserver.store import Store
from test_core import ALARM

class ReadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store=Store(':memory:',[ALARM]);self.monitor=Monitor({'enabled':True},self.store)
        self.monitor.connections['line']={'name':'line','state':'CONNECTED'}
        self.sender=AsyncMock();self.client=SimpleNamespace(telegram_queue=SimpleNamespace(process_telegram_outgoing=self.sender))
        self.monitor.clients['line']=self.client
    async def asyncTearDown(self):
        await self.monitor.stop();self.store.close()

    async def test_reads_only_unknown_values_without_writes_or_state_fabrication(self):
        from xknx.telegram.apci import GroupValueRead
        real_sleep=asyncio.sleep
        async def sleep(delay):await real_sleep(0)
        with patch('knx_alarmserver.knx.asyncio.sleep',side_effect=sleep):
            result=self.monitor.request_read()
            self.assertEqual(result['total'],1)
            with self.assertRaises(FileExistsError):self.monitor.request_read()
            await self.monitor.read_task
        self.assertEqual(self.sender.await_count,1)
        telegram=self.sender.await_args.args[0]
        self.assertIsInstance(telegram.payload,GroupValueRead)
        self.assertEqual(str(telegram.destination_address),'1/2/3')
        self.assertEqual(self.monitor.status()['read']['sent'],1)
        self.assertEqual(self.monitor.status()['read']['answered'],0)
        self.assertEqual(self.store.snapshot()[0]['status'],'unknown')
        self.store.ingest('1/2/3',0,'1.1.1')
        self.assertEqual(self.monitor.request_read()['total'],0)

    async def test_only_valid_responses_count_and_shutdown_cancels_job(self):
        from xknx.telegram import Telegram,GroupAddress,IndividualAddress,TelegramDirection
        from xknx.telegram.apci import GroupValueResponse
        from xknx.dpt import DPTBinary
        self.monitor.request_read()
        self.monitor.received(Telegram(direction=TelegramDirection.INCOMING,destination_address=GroupAddress('1/2/3'),source_address=IndividualAddress('1.1.1'),payload=GroupValueResponse(DPTBinary(0))),'line')
        self.assertEqual(self.monitor.status()['read']['answered'],1)
        self.assertEqual(self.store.snapshot()[0]['status'],'normal')
        await self.monitor.stop()
        self.assertEqual(self.monitor.status()['read']['state'],'cancelled')

    async def test_disconnected_and_unconfigured_connection_rejected(self):
        with self.assertRaises(ValueError):self.monitor.request_read(connection='other')
        self.monitor.connections['line']['state']='ERROR'
        with self.assertRaises(RuntimeError):self.monitor.request_read()
