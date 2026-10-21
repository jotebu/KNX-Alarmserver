"""Passive group telegram observation through xknx, with reconnect status."""

import asyncio
from collections import deque
import logging

from .store import now

LOG = logging.getLogger(__name__)


class Monitor:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.connections = {}
        self.telegrams = deque(maxlen=250)
        self.tasks = []
        self.failed = False

    def status(self):
        enabled = self.config.get("enabled", False)
        states = list(self.connections.values())
        return {"enabled": enabled, "ready": enabled and bool(states) and
                all(s["state"] == "CONNECTED" for s in states) and not self.failed,
                "storage_error": self.failed, "connections": states}

    def received(self, telegram, connection_name):
        from xknx.telegram import GroupAddress, TelegramDirection
        from xknx.telegram.apci import GroupValueResponse, GroupValueWrite
        from xknx.exceptions import ConversionError, CouldNotParseTelegram

        if telegram.direction != TelegramDirection.INCOMING or not isinstance(telegram.destination_address, GroupAddress):
            return
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
                await asyncio.Event().wait()  # xknx handles reconnect after an established tunnel
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connections[name].update(state="ERROR", error=type(error).__name__)
                LOG.exception("KNX-Verbindung %s fehlgeschlagen; neuer Versuch in 10s", name)
            finally:
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
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        self.connections.clear()

