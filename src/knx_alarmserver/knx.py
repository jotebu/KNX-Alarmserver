"""Passive group telegram observation through xknx, with reconnect status."""

import asyncio
from collections import deque
import logging
from time import monotonic

from .store import now

LOG = logging.getLogger(__name__)


class Monitor:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.connections = {}
        self.telegrams = deque(maxlen=250)
        self.telegram_buckets = deque()
        self.tasks = []
        self.failed = False
        self.clients = {}
        self.read_task = None
        self.read_state = {'state': 'idle', 'total': 0, 'sent': 0}
        self.read_responses = set()
        self.read_targets = set()
        from .bus_test import BusTest
        self.bus_test = BusTest(self)

    def status(self):
        enabled = self.config.get("enabled", False)
        states = list(self.connections.values())
        return {"enabled": enabled, "ready": enabled and bool(states) and
                all(s["state"] == "CONNECTED" for s in states) and not self.failed,
                "storage_error": self.failed, "connections": states,
                "test": dict(self.bus_test.state),
                "read": {**self.read_state, "answered": len(self.read_responses)}}

    def _prune_telegram_buckets(self, second):
        while self.telegram_buckets and self.telegram_buckets[0][0] <= second - 3600:
            self.telegram_buckets.popleft()

    def telegram_rates(self):
        # One bucket per second: bounded memory, independent of the 250-row ring.
        # Monotonic time is unaffected by NTP or daylight-saving clock changes.
        with self.store.lock:
            second = int(monotonic())
            self._prune_telegram_buckets(second)
            return {'minute': sum(count for stamp, count in self.telegram_buckets if stamp > second - 60),
                    'hour': sum(count for _, count in self.telegram_buckets)}

    def received(self, telegram, connection_name):
        # Keep decoder selection and ingestion consistent with live matrix edits.
        with self.store.lock:
            return self._received(telegram, connection_name)

    def _received(self, telegram, connection_name):
        from xknx.telegram import GroupAddress, TelegramDirection
        from xknx.telegram.apci import GroupValueResponse, GroupValueWrite
        from xknx.exceptions import ConversionError, CouldNotParseTelegram

        if telegram.direction != TelegramDirection.INCOMING or not isinstance(telegram.destination_address, GroupAddress):
            return
        second = int(monotonic())
        self._prune_telegram_buckets(second)
        if self.telegram_buckets and self.telegram_buckets[-1][0] == second:
            self.telegram_buckets[-1][1] += 1
        else:
            self.telegram_buckets.append([second, 1])
        timestamp = now()
        self.connections[connection_name]["last_received"] = timestamp
        address = str(telegram.destination_address)
        payload = telegram.payload
        item = {"timestamp": timestamp, "connection": connection_name,
                "source": str(telegram.source_address), "destination": address,
                "service": type(payload).__name__, "value": None, "dpt": None, "error": None}
        alarm = self.store.by_address.get(address)
        point = self.store.ets_point(address)
        if point:
            item.update(name=point['name'], description=point['description'],
                        ets_warning='; '.join(point['warnings']))
        if alarm:
            item['name'] = alarm.name
        dpt = alarm.dpt if alarm else point.get('dpt') if point else None
        if isinstance(payload, (GroupValueWrite, GroupValueResponse)):
            item["raw"] = list(payload.value.value) if isinstance(payload.value.value, tuple) else payload.value.value
        self.telegrams.appendleft(item)
        item["dpt"] = dpt
        if dpt and isinstance(payload, (GroupValueWrite, GroupValueResponse)):
            try:
                from .dpt import decode
                value, display, unit = decode(dpt, payload.value)
                item.update(value=value, dpt=dpt, display=display, unit=unit)
                if alarm:
                    self.store.ingest(address, value, str(telegram.source_address), display, unit)
                    if isinstance(payload, GroupValueResponse) and address in self.read_targets and connection_name == self.read_state.get('connection'):
                        self.read_responses.add(address)
            except (ValueError, TypeError, KeyError, ConversionError, CouldNotParseTelegram) as error:
                item["error"] = str(error)[:300]
                try:
                    self.store.decode_failed(address, item["error"])
                except Exception:
                    self.failed = True
                    LOG.exception("DPT-Fehlerstatus konnte nicht gespeichert werden")
            except Exception:
                self.failed = True
                LOG.exception("Alarmzustand konnte nicht gespeichert werden")

    def request_read(self, mode='unknown', connection=''):
        if self.bus_test.active:
            raise FileExistsError('Ein KNX-Test läuft bereits')
        if self.read_task and not self.read_task.done():
            raise FileExistsError('Eine KNX-Statusabfrage laeuft bereits')
        ready = [name for name in self.clients if self.connections.get(name, {}).get('state') == 'CONNECTED']
        if not self.config.get('enabled') or not ready:
            raise RuntimeError('Keine aktive KNX-Verbindung fuer eine Statusabfrage')
        if connection and connection not in ready:
            raise ValueError('Gewaehlte KNX-Verbindung ist nicht bereit')
        connection = connection or ready[0]
        rows = self.store.snapshot()
        addresses = sorted({row['group_address'] for row in rows if mode == 'all' or row['status'] == 'unknown'},
                           key=lambda address: tuple(map(int, address.split('/'))))
        self.read_responses.clear()
        self.read_targets = set(addresses)
        self.read_state = {'state': 'running' if addresses else 'complete', 'total': len(addresses),
                           'sent': 0, 'connection': connection, 'started_at': now()}
        if addresses:
            self.read_task = asyncio.create_task(self._read_addresses(connection, self.clients[connection], addresses))
        return {**self.read_state, 'answered': 0}

    async def _read_addresses(self, connection, client, addresses):
        from xknx.telegram import Telegram, GroupAddress
        from xknx.telegram.apci import GroupValueRead
        try:
            for address in addresses:
                if self.clients.get(connection) is not client or self.connections.get(connection, {}).get('state') != 'CONNECTED':
                    raise RuntimeError('KNX-Verbindung unterbrochen')
                # Await actual outgoing handling; never enqueue a burst or write a value.
                await asyncio.wait_for(client.telegram_queue.process_telegram_outgoing(
                    Telegram(destination_address=GroupAddress(address), payload=GroupValueRead())), timeout=10)
                self.read_state['sent'] += 1
                await asyncio.sleep(0.5)
            await asyncio.sleep(2)  # Allow the final device responses to arrive.
            self.read_state.update(state='complete', finished_at=now())
        except asyncio.CancelledError:
            self.read_state.update(state='cancelled', message='Statusabfrage abgebrochen.')
            raise
        except Exception:
            LOG.exception('KNX-Statusabfrage fehlgeschlagen')
            self.read_state.update(state='failed', message='Statusabfrage unterbrochen; Verbindung und Dienstprotokoll pruefen.')

    async def _run_connection(self, item):
        from xknx import XKNX
        from xknx.io import ConnectionConfig, ConnectionType

        name = item["name"]
        def state_changed(state):
            self.connections[name]["state"] = state.name
            self.connections[name]["changed_at"] = now()

        kind = ConnectionType.ROUTING if item.get("type", "tunneling") == "routing" else ConnectionType.TUNNELING
        kwargs = {k: v for k, v in item.items() if k not in {"name", "type", "enabled"}}
        while True:
            xknx = XKNX(connection_config=ConnectionConfig(connection_type=kind, **kwargs),
                        telegram_received_cb=lambda telegram: self.received(telegram, name),
                        connection_state_changed_cb=state_changed, state_updater=False)
            try:
                async with asyncio.timeout(30):
                    await xknx.start()
                self.connections[name]["error"] = None
                self.clients[name] = xknx
                await asyncio.Event().wait()  # xknx handles reconnect after an established tunnel
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connections[name].update(state="ERROR", error=type(error).__name__)
                LOG.exception("KNX-Verbindung %s fehlgeschlagen; neuer Versuch in 10s", name)
            finally:
                self.clients.pop(name, None)
                try:
                    async with asyncio.timeout(10):
                        await xknx.stop()
                except Exception:
                    LOG.exception("KNX-Verbindung %s konnte nicht sauber beendet werden", name)
            await asyncio.sleep(10)

    async def start(self):
        from .dpt import transcoder
        for alarm in self.store.alarms.values():
            transcoder(alarm.dpt)
        if not self.config.get("enabled", False):
            return
        for item in self.config["connections"]:
            if not item.get("enabled", True):
                continue
            self.connections[item["name"]] = {"name": item["name"], "state": "CONNECTING", "last_received": None, "error": None}
            self.tasks.append(asyncio.create_task(self._run_connection(item)))

    async def stop(self):
        await self.bus_test.close()
        if self.read_task and not self.read_task.done():
            self.read_task.cancel()
            await asyncio.gather(self.read_task, return_exceptions=True)
            self.read_state.update(state='cancelled', message='Statusabfrage abgebrochen.')
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        self.connections.clear()

