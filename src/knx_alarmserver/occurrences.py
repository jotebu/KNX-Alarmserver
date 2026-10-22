"""Durable alarm occurrences, independent of current point state and audit events."""
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from contextlib import closing


class OccurrenceStore:
    def _initialize_occurrences(self):
        self.db.create_function('casefold', 1, lambda value: str(value or '').casefold(), deterministic=True)
        migrated = self.db.execute("SELECT value FROM settings WHERE name='occurrences_migrated'").fetchone()
        if not migrated:
            # SQLite backup includes WAL data. Fail before migration if it cannot be saved.
            filename = self.db.execute('PRAGMA database_list').fetchone()[2]
            populated = self.db.execute('SELECT 1 FROM events LIMIT 1').fetchone() or self.db.execute('SELECT 1 FROM states WHERE active IS NOT NULL LIMIT 1').fetchone()
            if filename and populated:
                backup = Path(filename + f'.before-occurrences-{time.time_ns()}.sqlite3')
                fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                try:
                    with closing(sqlite3.connect(backup)) as target:
                        self.db.backup(target)
                except Exception:
                    backup.unlink(missing_ok=True)
                    raise
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alarm_id TEXT NOT NULL, name TEXT NOT NULL, area TEXT NOT NULL DEFAULT '',
                priority INTEGER, group_address TEXT NOT NULL DEFAULT '', dpt TEXT NOT NULL DEFAULT '',
                came_at TEXT, acknowledged INTEGER NOT NULL DEFAULT 0,
                acknowledged_at TEXT, acknowledged_by TEXT, went_at TEXT,
                end_reason TEXT, ended_at TEXT, migration_note TEXT NOT NULL DEFAULT '');
            CREATE INDEX IF NOT EXISTS occurrences_alarm ON occurrences(alarm_id,id);
            CREATE INDEX IF NOT EXISTS occurrences_came ON occurrences(came_at);
        ''')
        with self.transaction():
            if 'acknowledged_name' not in {row['name'] for row in self.db.execute('PRAGMA table_info(occurrences)')}:
                self.db.execute('ALTER TABLE occurrences ADD COLUMN acknowledged_name TEXT')
            for table in ['states', 'events']:
                if 'occurrence_id' not in {row['name'] for row in self.db.execute(f'PRAGMA table_info({table})')}:
                    self.db.execute(f'ALTER TABLE {table} ADD COLUMN occurrence_id INTEGER')
            if not migrated:
                self._migrate_occurrences()
                self.db.execute("INSERT INTO settings(name,value) VALUES ('occurrences_migrated','1')")
            self.db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS occurrences_one_active
                ON occurrences(alarm_id) WHERE went_at IS NULL AND end_reason IS NULL''')

    def _new_occurrence(self, alarm_id, came_at, name=None, note=''):
        alarm = self.alarms.get(alarm_id)
        return self.db.execute('''INSERT INTO occurrences(alarm_id,name,area,priority,group_address,dpt,came_at,migration_note)
            VALUES (?,?,?,?,?,?,?,?)''', (alarm_id, name if name is not None else alarm.name if alarm else alarm_id,
            alarm.area if alarm else '', alarm.priority if alarm else None,
            alarm.group_address if alarm else '', alarm.dpt if alarm else '', came_at, note)).lastrowid

    def _end_occurrence(self, alarm_id, reason, timestamp):
        # A configuration change is not a measured return-to-normal.
        self.db.execute('''UPDATE occurrences SET end_reason=?,ended_at=?
            WHERE alarm_id=? AND went_at IS NULL AND end_reason IS NULL''', (reason, timestamp, alarm_id))

    def _migrate_occurrences(self):
        latest = {}
        for event in self.db.execute("SELECT * FROM events WHERE kind IN ('active','clear','acknowledge') ORDER BY seq").fetchall():
            alarm_id, kind = event['alarm_id'], event['kind']
            identifier = latest.get(alarm_id)
            previous = self.db.execute('SELECT * FROM occurrences WHERE id=?', (identifier,)).fetchone() if identifier else None
            if kind == 'active':
                if previous and previous['went_at'] is None and previous['end_reason'] is None:
                    self._end_occurrence(alarm_id, 'historical_gap', None)
                identifier = self._new_occurrence(alarm_id, event['timestamp'], event['alarm_name'], 'Aus Ereignisprotokoll übernommen; Metadaten soweit vorhanden aus aktueller Matrix.')
                latest[alarm_id] = identifier
            elif kind == 'clear':
                if not previous or previous['went_at'] is not None or previous['end_reason'] is not None:
                    # Legacy initial normal telegrams also produced clear events.
                    continue
                self.db.execute('UPDATE occurrences SET went_at=? WHERE id=?', (event['timestamp'], identifier))
            else:
                if not previous:
                    identifier = self._new_occurrence(alarm_id, None, event['alarm_name'], 'Gekommen-Zeitpunkt nicht im erhaltenen Ereignisprotokoll vorhanden.')
                    latest[alarm_id] = identifier
                self.db.execute('''UPDATE occurrences SET acknowledged=1,acknowledged_at=?,acknowledged_by=?
                    WHERE id=? AND acknowledged=0''', (event['timestamp'], event['username'], identifier))
            self.db.execute('UPDATE events SET occurrence_id=? WHERE seq=?', (identifier, event['seq']))
        # Current persisted point state is authoritative for the current cycle.
        for state in self.db.execute('SELECT * FROM states').fetchall():
            alarm_id = state['id']
            if alarm_id not in self.alarms:
                self._end_occurrence(alarm_id, 'configuration_removed', None)
                continue
            identifier = latest.get(alarm_id)
            previous = self.db.execute('SELECT * FROM occurrences WHERE id=?', (identifier,)).fetchone() if identifier else None
            if state['active'] is None:
                self._end_occurrence(alarm_id, 'configuration_changed', None)
                continue
            if state['active']:
                newer_transition = previous and state['changed_at'] and previous['came_at'] and datetime.fromisoformat(state['changed_at']) > datetime.fromisoformat(previous['came_at'])
                if not previous or previous['went_at'] is not None or previous['end_reason'] is not None or (state['pending'] and previous['acknowledged'] and not state['acknowledged_at']) or newer_transition:
                    self._end_occurrence(alarm_id, 'historical_gap', None)
                    identifier = self._new_occurrence(alarm_id, state['changed_at'], note='Aus gespeichertem aktiven Zustand übernommen; Ereignisprotokoll unvollständig.')
                self.db.execute('UPDATE states SET occurrence_id=? WHERE id=?', (identifier, alarm_id))
            else:
                if state['pending'] and (not previous or previous['end_reason'] is not None or (previous['acknowledged'] and not state['acknowledged_at'])):
                    self._end_occurrence(alarm_id, 'historical_gap', None)
                    identifier = self._new_occurrence(alarm_id, None, note='Gekommen-Zeitpunkt nicht mehr vorhanden; gegangenen offenen Zustand übernommen.')
                    previous = self.db.execute('SELECT * FROM occurrences WHERE id=?', (identifier,)).fetchone()
                if not identifier:
                    continue
                if previous and previous['went_at'] is None and previous['end_reason'] is None:
                    if state['changed_at'] and (not previous['came_at'] or state['changed_at'] >= previous['came_at']):
                        self.db.execute('UPDATE occurrences SET went_at=? WHERE id=?', (state['changed_at'], identifier))
                    else:
                        self._end_occurrence(alarm_id, 'historical_gap', None)
                self.db.execute('UPDATE states SET occurrence_id=? WHERE id=?', (identifier, alarm_id))
            if not state['pending']:
                self.db.execute('''UPDATE occurrences SET acknowledged=1,
                    acknowledged_at=COALESCE(acknowledged_at,?),acknowledged_by=COALESCE(acknowledged_by,?) WHERE id=?''',
                    (state['acknowledged_at'], state['acknowledged_by'], identifier))
        # Retained logs may refer to definitions which have since been removed.
        configured = set(self.alarms)
        for row in self.db.execute('SELECT DISTINCT alarm_id FROM occurrences WHERE went_at IS NULL AND end_reason IS NULL').fetchall():
            if row['alarm_id'] not in configured:
                self._end_occurrence(row['alarm_id'], 'configuration_removed', None)

    def acknowledge_occurrence(self, identifier, username):
        from .store import now
        with self.transaction():
            row = self.db.execute('SELECT * FROM occurrences WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise KeyError(identifier)
            if row['acknowledged']:
                return False
            timestamp = now()
            self.db.execute('UPDATE occurrences SET acknowledged=1,acknowledged_at=?,acknowledged_by=?,acknowledged_name=? WHERE id=?', (timestamp, username, self.display_name(username), identifier))
            self.db.execute('''UPDATE states SET pending=0,acknowledged_by=?,acknowledged_at=?
                WHERE id=? AND occurrence_id=?''', (username, timestamp, row['alarm_id'], identifier))
            self.db.execute('''INSERT INTO events(alarm_id,alarm_name,kind,timestamp,username,occurrence_id)
                VALUES (?,?,'acknowledge',?,?,?)''', (row['alarm_id'], row['name'], timestamp, username, identifier))
        return True

    def occurrence_list(self, status_filter='', start=None, end=None, query=''):
        from .listing import alarms_page
        with self.lock:
            current = {row['id']: row for row in self.snapshot()}
            people = {row['username']: (row['first_name']+' '+row['last_name']).strip() for row in self.users() if row['first_name'] and row['last_name']}
            names = {entry['priority']: entry['name'] for entry in self.priorities()['entries']}
            if status_filter == 'unknown':
                rows = [dict(row, occurrence_id=None, came_at=None, went_at=None, acknowledged_at=None,
                             acknowledged_by=None, pending=0) for row in current.values() if row['status'] == 'unknown']
            else:
                clauses, args = [], []
                active = '(went_at IS NULL AND end_reason IS NULL)'
                if status_filter in ('', 'open'):
                    clauses.append(f'({active} OR acknowledged=0)')
                elif status_filter == 'active':
                    clauses.append(f'{active} AND acknowledged=0')
                elif status_filter == 'active_ack':
                    clauses.append(f'{active} AND acknowledged=1')
                elif status_filter == 'clear_pending':
                    clauses.append(f'NOT {active} AND acknowledged=0')
                elif status_filter == 'closed':
                    clauses.append(f'NOT {active} AND acknowledged=1')
                if start:
                    clauses.append('came_at >= ?'); args.append(start)
                if end:
                    clauses.append('came_at < ?'); args.append(end)
                if query:
                    clauses.append("(casefold(name) LIKE ? ESCAPE '\\' OR casefold(area) LIKE ? ESCAPE '\\' OR casefold(group_address) LIKE ? ESCAPE '\\' OR casefold(dpt) LIKE ? ESCAPE '\\' OR casefold(acknowledged_by) LIKE ? ESCAPE '\\' OR CAST(id AS TEXT) LIKE ? ESCAPE '\\')")
                    needle = '%' + query.casefold().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
                    args.extend([needle] * 6)
                where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
                total = self.db.execute('SELECT count(*) FROM occurrences' + where, args).fetchone()[0]
                limit = 500 if status_filter in ('all', 'closed') else None
                sql = 'SELECT * FROM occurrences' + where
                # Historical selection: newest 500 matching cycles, then display by priority.
                sql += ' ORDER BY came_at DESC,id DESC'
                if limit:
                    sql += ' LIMIT 500'
                rows = []
                for record in self.db.execute(sql, args).fetchall():
                    row = dict(record)
                    row['acknowledged_name'] = row['acknowledged_name'] or people.get(row['acknowledged_by'])
                    is_active = row['went_at'] is None and row['end_reason'] is None
                    row.update(occurrence_id=row['id'], status=('active' if not row['acknowledged'] else 'active_ack') if is_active else ('clear_pending' if not row['acknowledged'] else 'closed'),
                               pending=int(not row['acknowledged']), priority_name=names.get(row['priority'], ''),
                               changed_at=row['came_at'], decode_error=None)
                    point = current.get(row['alarm_id'])
                    row['display_value'] = None
                    if point and point.get('occurrence_id') == row['id']:
                        row['display_value'] = point['display_value']
                        row['decode_error'] = point['decode_error']
                    rows.append(row)
                # Do not let display sorting change which historical 500 are selected.
                rows.sort(key=lambda r: (r['priority'] if r['priority'] is not None else 1000,))
                return {'rows': rows, 'total': total, 'shown': len(rows), 'limit': limit}
            result = alarms_page(rows, start=start, end=end, query=query, unlimited=True)
            return {key: result[key] for key in ('rows', 'total', 'shown', 'limit')}

    def occurrence_counts(self):
        with self.lock:
            active = 'went_at IS NULL AND end_reason IS NULL'
            counts = self.db.execute(f'''SELECT
                COALESCE(sum(({active}) AND acknowledged=0),0) AS active,
                COALESCE(sum(({active}) AND acknowledged=1),0) AS acked,
                COALESCE(sum(NOT ({active}) AND acknowledged=0),0) AS pending,
                COALESCE(sum(NOT ({active}) AND acknowledged=1),0) AS closed
                FROM occurrences''').fetchone()
            return {**dict(counts), 'unknown': sum(row['status'] == 'unknown' for row in self.snapshot())}
