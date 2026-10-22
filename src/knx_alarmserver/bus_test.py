"""Commissioning writes with DPT round-trip validation and a single paced job."""
import asyncio
from dataclasses import asdict
import hashlib
import json
import logging

from .dpt import transcoder, decode
from .rules import evaluate
from .store import now

LOG = logging.getLogger(__name__)


def revision(store):
    return hashlib.sha256(json.dumps([asdict(a) for a in store.alarms.values()], sort_keys=True).encode()).hexdigest()


def test_values(alarm):
    if alarm.operator == 'monitor':
        raise ValueError('Nur Beobachtung; keine Alarmbedingung')
    if alarm.field:
        raise ValueError('Strukturierter DPT mit Feldregel: Testwerte manuell klären')
    codec = transcoder(alarm.dpt)
    candidates = [alarm.threshold] if not isinstance(alarm.threshold, list) else list(alarm.threshold)
    candidates += [False, True, 0, 1, -1, '', 'Test']
    if isinstance(alarm.threshold, str):
        candidates += [alarm.threshold + ' Test', '']
    for number in list(candidates):
        if type(number) in (int, float):
            margin = max(1, alarm.hysteresis + 1, abs(number) * 0.01)
            candidates += [number - margin, number + margin]
    if isinstance(alarm.threshold, list) and len(alarm.threshold) == 2 and all(type(v) in (int, float) for v in alarm.threshold):
        candidates.append(sum(alarm.threshold) / 2)
    candidates += [getattr(codec, 'value_min', None), getattr(codec, 'value_max', None)]
    # Includes valid enumeration members without inventing a proprietary meaning.
    if str(alarm.dpt).split('.')[0] == '20':
        candidates += list(range(256))
    values = {}
    for candidate in candidates:
        if candidate is None or isinstance(candidate, (dict, list)):
            continue
        try:
            payload = codec.to_knx(candidate)
            value, display, unit = decode(alarm.dpt, payload)
            active = evaluate(alarm, value, False)
            # Normal must also clear an already active alarm across hysteresis.
            if active and evaluate(alarm, value, True):
                values.setdefault('alarm', (payload, value, display, unit))
            elif not active and not evaluate(alarm, value, True):
                values.setdefault('normal', (payload, value, display, unit))
        except Exception:
            continue
        if len(values) == 2:
            return values
    raise ValueError('Kein gültiges Wertepaar innerhalb des DPT-Wertebereichs ermittelbar')


class BusTest:
    def __init__(self, monitor):
        self.monitor = monitor
        self.store = monitor.store
        self.task = None
        self.stop_event = asyncio.Event()
        self.state = {'state': 'idle', 'sent': 0, 'total': 0}

    @property
    def active(self):
        return self.state['state'] in {'preparing', 'running', 'stopping'}

    def plan(self, alarm_id=''):
        with self.store.lock:
            if alarm_id and alarm_id not in self.store.alarms:
                raise ValueError('Alarm nicht vorhanden; Matrix neu laden')
            alarms = [self.store.alarms[alarm_id]] if alarm_id else list(self.store.alarms.values())
            rows = []
            for alarm in alarms:
                row = {'id': alarm.id, 'name': alarm.name, 'group_address': alarm.group_address,
                       'dpt': alarm.dpt, 'operator': alarm.operator, 'threshold': alarm.threshold,
                       'hysteresis': alarm.hysteresis, 'ready': False}
                try:
                    values = test_values(alarm)
                    row.update(ready=True, alarm=values['alarm'][2], normal=values['normal'][2])
                except Exception as error:
                    row['reason'] = str(error)[:300]
                rows.append(row)
            return {'revision': revision(self.store), 'rows': rows, 'interval': 1}

    def start(self, ids, mode, expected, connection, username):
        if self.active or (self.monitor.read_task and not self.monitor.read_task.done()):
            raise RuntimeError('Ein KNX-Test oder eine Statusabfrage läuft bereits')
        ready = [name for name in self.monitor.clients if self.monitor.connections.get(name, {}).get('state') == 'CONNECTED']
        if not self.monitor.config.get('enabled') or not ready:
            raise ValueError('Keine aktive KNX-Verbindung')
        if connection not in ready:
            raise ValueError('Aktive Verbindung auswählen')
        if mode not in {'alarm', 'normal'} or not isinstance(ids, list) or not ids or len(ids) > 5000 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Eindeutige Alarme und Testmodus erforderlich')
        with self.store.lock:
            if expected != revision(self.store):
                raise RuntimeError('Matrix wurde geändert; Testvorschau neu laden')
            alarms = [self.store.alarms[i] for i in ids if i in self.store.alarms]
            if len(alarms) != len(ids):
                raise ValueError('Alarm nicht mehr vorhanden')
            if len({a.group_address for a in alarms}) != len(alarms):
                raise ValueError('Mehrere Einträge derselben Gruppenadresse: Auswahl einzeln klären')
            writes = [(a, test_values(a)[mode]) for a in alarms]
        self.stop_event = asyncio.Event()
        self.state = {'state': 'preparing', 'sent': 0, 'total': len(writes), 'mode': mode,
                      'connection': connection, 'user': username, 'started_at': now(),
                      'message': 'Mailversand wird deaktiviert; laufenden Mailversand abwarten.'}
        self.task = asyncio.create_task(self._run(writes, expected, connection))
        return dict(self.state)

    async def _pause(self):
        try:
            await asyncio.wait_for(self.stop_event.wait(), timeout=1)
        except asyncio.TimeoutError:
            pass

    async def _run(self, writes, expected, connection):
        from xknx.telegram import Telegram, GroupAddress
        from xknx.telegram.apci import GroupValueWrite
        client = self.monitor.clients.get(connection)
        preparing = asyncio.create_task(asyncio.to_thread(self.store.begin_bus_test))
        try:
            await asyncio.shield(preparing)
            self.state.update(state='running', mail_disabled=True, message='Mailversand deaktiviert. Test läuft mit 1 Sekunde Abstand.')
            for alarm, (payload, value, display, unit) in writes:
                if self.stop_event.is_set():
                    break
                with self.store.lock:
                    if revision(self.store) != expected:
                        raise RuntimeError('Matrix während des Tests geändert')
                if client is None or self.monitor.clients.get(connection) is not client or self.monitor.connections.get(connection, {}).get('state') != 'CONNECTED':
                    raise RuntimeError('KNX-Verbindung unterbrochen')
                await asyncio.wait_for(client.telegram_queue.process_telegram_outgoing(
                    Telegram(destination_address=GroupAddress(alarm.group_address), payload=GroupValueWrite(payload))), timeout=10)
                self.state['sent'] += 1
                # Outgoing telegrams are otherwise deliberately not ingested. Record
                # this commissioning value, not a fabricated incoming bus response.
                with self.store.lock:
                    if revision(self.store) != expected:
                        raise RuntimeError('Matrix während des Tests geändert')
                    self.store.ingest(alarm.group_address, value, 'KNX-Test · ' + self.state['user'], display, unit)
                if self.state['sent'] < self.state['total']:
                    await self._pause()
            stopped = self.stop_event.is_set()
            self.state.update(state='cancelled' if stopped else 'complete', message='Test gestoppt.' if stopped else 'Testlauf beendet.')
        except asyncio.CancelledError:
            # A thread disabling SMTP cannot be cancelled halfway through; drain it
            # before clearing the transient guard during shutdown/reconfiguration.
            await preparing
            self.state.update(state='cancelled', message='Test durch Dienst-/Verbindungswechsel abgebrochen.')
            raise
        except Exception:
            LOG.exception('KNX-Bustest fehlgeschlagen')
            self.state.update(state='failed', message='Test unterbrochen; Verbindung, Matrix und Dienstprotokoll prüfen.')
        finally:
            disabled = preparing.done() and not preparing.cancelled() and preparing.exception() is None
            self.store.end_bus_test()
            self.state.update(finished_at=now(), mail_disabled=disabled)
            self.state['message'] += (' Mailversand bleibt deaktiviert. Normalwerte stellen keine früheren Messwerte wieder her.'
                                      if disabled else ' Mail-Abschaltung nicht bestätigt; kein Bus-Schreibvorgang ausgeführt.')

    def stop(self):
        if self.active:
            self.stop_event.set()
            self.state.update(state='stopping', message='Stoppen angefordert; bereits laufendes Telegramm wird noch abgeschlossen.')
        return dict(self.state)

    async def close(self):
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            if self.active:
                self.state.update(state='cancelled', message='Test abgebrochen.')
