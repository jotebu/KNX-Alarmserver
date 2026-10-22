"""Transactional alarm state, acknowledgement audit and local user accounts."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import sqlite3
import threading
from contextlib import contextmanager, closing
import json
import time

from .rules import evaluate, normalized


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


from .occurrences import OccurrenceStore


class Store(OccurrenceStore):
    def __init__(self, path, alarms, retention_days=365):
        self.alarms = {a.id: a for a in alarms}
        self.by_address = {a.group_address: a for a in alarms}
        self.started_at = now()
        self.retention_days = retention_days
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        try:
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'").fetchone():
                saved = self.db.execute("SELECT value FROM settings WHERE name='alarm_matrix'").fetchone()
                if saved:
                    from .config import Alarm
                    alarms = [Alarm(**row) for row in json.loads(saved['value'])['alarms']]
                    self.alarms = {a.id: a for a in alarms}
                    self.by_address = {a.group_address: a for a in alarms}
            self._initialize(alarms)
            self._initialize_occurrences()
            row = self.db.execute("SELECT value FROM settings WHERE name='ets'").fetchone()
            self._ets = json.loads(row['value']) if row else {}
        except Exception:
            self.db.close()
            raise

    def _initialize(self, alarms):
        if self.db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            raise ValueError("Nicht unterstuetzte Datenbankversion")
        with self.transaction():
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS states (
                    id TEXT PRIMARY KEY, signature TEXT NOT NULL,
                    active INTEGER, pending INTEGER NOT NULL DEFAULT 0,
                    acknowledged_by TEXT, acknowledged_at TEXT,
                    last_seen TEXT, changed_at TEXT, source TEXT,
                    value_json TEXT, display_value TEXT, unit TEXT,
                    decode_error TEXT, last_error_at TEXT);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, alarm_id TEXT NOT NULL,
                    alarm_name TEXT NOT NULL, kind TEXT NOT NULL,
                    timestamp TEXT NOT NULL, username TEXT, source TEXT);
                CREATE INDEX IF NOT EXISTS events_time ON events(timestamp);
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
            columns = {r['name'] for r in self.db.execute('PRAGMA table_info(users)')}
            # Existing accounts had unrestricted access: preserve that as admin.
            if 'role' not in columns:
                self.db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
            self.db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL)""")
            for alarm in alarms:
                signature = json.dumps([alarm.group_address, alarm.dpt, alarm.operator, alarm.threshold,
                                        alarm.hysteresis, alarm.field], sort_keys=True, ensure_ascii=False)
                row = self.db.execute("SELECT signature FROM states WHERE id=?", (alarm.id,)).fetchone()
                if row and json.loads(row["signature"]) != json.loads(signature):
                    raise ValueError(f"Alarm {alarm.id}: Adresse/DPT/Regel geaendert. Neue ID verwenden.")
                self.db.execute("INSERT OR IGNORE INTO states(id,signature) VALUES (?,?)", (alarm.id, signature))

    @contextmanager
    def transaction(self):
        with self.lock, self.db:
            yield

    def priorities(self):
        from .priorities import DEFAULTS
        with self.lock:
            saved = self.db.execute("SELECT value FROM settings WHERE name='priorities'").fetchone()
            entries = json.loads(saved['value']) if saved else [dict(row) for row in DEFAULTS]
            # Preserve imported legacy/custom numbers until explicitly reconfigured.
            present = {row['priority'] for row in entries}
            for alarm in self.alarms.values():
                if alarm.priority not in present:
                    entries.append({'priority': alarm.priority, 'name': f'Prioritaet {alarm.priority}'})
                    present.add(alarm.priority)
            entries.sort(key=lambda row: row['priority'])
            revision = hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            return {'entries': entries, 'revision': revision}

    def save_priorities(self, entries, revision):
        from .priorities import validate
        from .matrix import MatrixConflict
        proposed = validate(entries)
        with self.transaction():
            if revision != self.priorities()['revision']:
                raise MatrixConflict('Prioritaeten inzwischen geaendert. Neu laden und erneut bearbeiten.')
            allowed = {row['priority'] for row in proposed}
            used = {alarm.priority for alarm in self.alarms.values()}
            if used - allowed:
                raise ValueError('Verwendete Prioritaeten zuerst in der Alarmmatrix umstellen: ' + ', '.join(map(str, sorted(used - allowed))))
            self.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('priorities',?)",
                            (json.dumps(proposed, ensure_ascii=False),))
        return self.priorities()

    def matrix(self):
        from .matrix import editable
        with self.lock:
            rows = [editable(alarm) for alarm in self.alarms.values()]
            revision = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            return {'rows': rows, 'revision': revision, 'priorities': self.priorities()['entries']}

    def save_matrix(self, rows, revision, username, append=False):
        from .matrix import MatrixConflict, validate_rows
        if not isinstance(rows, list):
            raise ValueError('Alarmliste erforderlich')
        with self.lock:
            if revision != self.matrix()['revision']:
                raise MatrixConflict('Alarmmatrix inzwischen geaendert. Neu laden und Aenderungen erneut eintragen.')
            old = self.alarms
            saved = self.db.execute("SELECT value FROM settings WHERE name='alarm_matrix'").fetchone()
            next_id = json.loads(saved['value'])['next_id'] if saved else 1
            proposed = self.matrix()['rows'] if append else []
            seen = set()
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError('Alarm muss ein Objekt sein')
                row = dict(row)
                identifier = row.get('id')
                if identifier == '':
                    while True:
                        identifier = f'alarm-{next_id:06d}'
                        next_id += 1
                        if not self.db.execute('SELECT 1 FROM states WHERE id=?', (identifier,)).fetchone():
                            break
                    row['id'] = identifier
                elif append or not isinstance(identifier, str) or identifier not in old:
                    raise ValueError('ID wird vom Server vergeben; bestehende IDs nur zum Bearbeiten verwenden')
                if identifier in seen:
                    raise ValueError('Doppelte Alarm-ID')
                seen.add(identifier)
                proposed.append(row)
            alarms = validate_rows(proposed)
            allowed = {row['priority'] for row in self.priorities()['entries']}
            if any(alarm.priority not in allowed for alarm in alarms):
                raise ValueError('Unbekannte Prioritaet. Zuerst in der Prioritaetentabelle anlegen.')
            replacement = {alarm.id: alarm for alarm in alarms}
            with self.transaction():
                for identifier, alarm in old.items():
                    if identifier not in replacement:
                        self._end_occurrence(identifier, 'configuration_removed', now())
                        self._event(alarm, 'matrix_removed', now(), username=username)
                for alarm in alarms:
                    signature = json.dumps([alarm.group_address, alarm.dpt, alarm.operator, alarm.threshold,
                                            alarm.hysteresis, alarm.field], sort_keys=True, ensure_ascii=False)
                    state = self.db.execute('SELECT signature FROM states WHERE id=?', (alarm.id,)).fetchone()
                    if state and json.loads(state['signature']) != json.loads(signature):
                        self._end_occurrence(alarm.id, 'configuration_changed', now())
                        self.db.execute('DELETE FROM states WHERE id=?', (alarm.id,))
                    self.db.execute('INSERT OR IGNORE INTO states(id,signature) VALUES (?,?)', (alarm.id, signature))
                    if old.get(alarm.id) != alarm:
                        self._event(alarm, 'matrix_updated' if alarm.id in old else 'matrix_added', now(), username=username)
                payload = {'alarms': [asdict(a) for a in alarms], 'next_id': next_id}
                self.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('alarm_matrix',?)",
                                (json.dumps(payload, ensure_ascii=False, allow_nan=False),))
            self.alarms = replacement
            self.by_address = {alarm.group_address: alarm for alarm in alarms}
            return self.matrix()

    def close(self):
        with self.lock:
            self.db.close()

    def _event(self, alarm, kind, timestamp, username=None, source=None, occurrence_id=None):
        self.db.execute("INSERT INTO events(alarm_id,alarm_name,kind,timestamp,username,source,occurrence_id) VALUES (?,?,?,?,?,?,?)",
                        (alarm.id, alarm.name, kind, timestamp, username, source, occurrence_id))

    def ingest(self, address, value, source, display=None, unit=None):
        value = normalized(value)
        alarm = self.by_address.get(address)
        if not alarm:
            return False
        timestamp = now()
        with self.transaction():
            row = self.db.execute("SELECT * FROM states WHERE id=?", (alarm.id,)).fetchone()
            active = int(evaluate(alarm, value, bool(row["active"])))
            self.db.execute("UPDATE states SET value_json=?,display_value=?,unit=?,decode_error=NULL,last_error_at=NULL WHERE id=?",
                            (json.dumps(value, ensure_ascii=False, allow_nan=False), display if display is not None else str(value), unit, alarm.id))
            if row["active"] == active:
                self.db.execute("UPDATE states SET last_seen=?,source=? WHERE id=?", (timestamp, source, alarm.id))
                return False
            occurrence_id = row['occurrence_id']
            if alarm.operator != 'monitor':
                if active:
                    occurrence_id = self._new_occurrence(alarm.id, timestamp)
                elif occurrence_id:
                    self.db.execute('UPDATE occurrences SET went_at=? WHERE id=? AND went_at IS NULL AND end_reason IS NULL', (timestamp, occurrence_id))
            pending = 1 if active else row["pending"]
            ack_by = None if active else row["acknowledged_by"]
            ack_at = None if active else row["acknowledged_at"]
            self.db.execute("""UPDATE states SET active=?,pending=?,acknowledged_by=?,acknowledged_at=?,
                            last_seen=?,changed_at=?,source=?,occurrence_id=? WHERE id=?""",
                            (active, pending, ack_by, ack_at, timestamp, timestamp, source, occurrence_id, alarm.id))
            if alarm.operator != "monitor":
                self._event(alarm, "active" if active else "clear", timestamp, source=source, occurrence_id=occurrence_id)
        return True

    def decode_failed(self, address, message):
        alarm = self.by_address.get(address)
        if alarm:
            with self.transaction():
                self.db.execute("UPDATE states SET decode_error=?,last_error_at=? WHERE id=?",
                                (str(message)[:300], now(), alarm.id))

    def acknowledge(self, alarm_id, username):
        with self.transaction():
            alarm = self.alarms.get(alarm_id)
            if alarm is None:
                raise KeyError(alarm_id)
            row = self.db.execute("SELECT * FROM states WHERE id=?", (alarm_id,)).fetchone()
            if not row["pending"]:
                return False
            if row['occurrence_id'] is None:
                return False
            return self.acknowledge_occurrence(row['occurrence_id'], username)

    def snapshot(self):
        with self.lock:
            rows = {r["id"]: dict(r) for r in self.db.execute("SELECT * FROM states")}
            result = []
            priority_names = {row['priority']: row['name'] for row in self.priorities()['entries']}
            for alarm in self.alarms.values():
                row = rows[alarm.id]
                row.pop("signature")
                row["value"] = json.loads(row.pop("value_json")) if row["value_json"] is not None else None
                row.update(asdict(alarm))
                row['priority_name'] = priority_names.get(alarm.priority, str(alarm.priority))
                row["fresh"] = row["last_seen"] is not None and row["last_seen"] >= self.started_at
                row["quality"] = "decode_error" if row["decode_error"] else "ok" if row["last_seen"] else "unseen"
                row["status"] = ("unknown" if row["active"] is None else
                                 "active" if row["active"] and row["pending"] else
                                 "active_ack" if row["active"] else
                                 "clear_pending" if row["pending"] else "normal")
                result.append(row)
            return result

    def history(self, limit=200):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT ?", (min(max(limit, 1), 1000),))]

    def history_page(self, page=1, start=None, end=None, query='', page_size=200):
        from .listing import PAGE_SIZE, page_info
        clauses, args = [], []
        if start:
            clauses.append('timestamp >= ?'); args.append(start)
        if end:
            clauses.append('timestamp < ?'); args.append(end)
        if query:
            clauses.append("(alarm_name LIKE ? ESCAPE '\\' OR username LIKE ? ESCAPE '\\' OR kind LIKE ? ESCAPE '\\' OR source LIKE ? ESCAPE '\\')")
            needle = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            args.extend([needle] * 4)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with self.lock:
            total = self.db.execute('SELECT count(*) FROM events' + where, args).fetchone()[0]
            info = page_info(total, page, page_size)
            rows = self.db.execute('SELECT * FROM events' + where + ' ORDER BY seq DESC LIMIT ? OFFSET ?',
                                   [*args, page_size, (info['page'] - 1) * page_size]).fetchall()
        return {'rows': [dict(row) for row in rows], **info}

    def prune(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with self.transaction():
            self.db.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            self.db.execute("DELETE FROM occurrences WHERE acknowledged=1 AND max(COALESCE(went_at,ended_at),COALESCE(acknowledged_at,went_at,ended_at)) < ?", (cutoff,))

    @staticmethod
    def _validate_account(username, password=None, role=None):
        if (not isinstance(username, str) or not username or len(username) > 64
                or username != username.strip() or ':' in username
                or any(ord(c) < 32 or ord(c) == 127 for c in username)):
            raise ValueError("Ungueltiger Benutzername")
        if password is not None and (not isinstance(password, str) or not 12 <= len(password) <= 1024):
            raise ValueError("Passwort muss 12 bis 1024 Zeichen haben")
        if role is not None and (not isinstance(role, str) or role not in {'admin', 'user', 'viewer'}):
            raise ValueError("Unbekannte Rolle")

    def account(self, username):
        with self.lock:
            row = self.db.execute('SELECT username,role FROM users WHERE username=?', (username,)).fetchone()
            return dict(row) if row else None

    def users(self):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT username,role FROM users ORDER BY username')]

    def _guard_last_admin(self, username, role):
        row = self.db.execute('SELECT role FROM users WHERE username=?', (username,)).fetchone()
        if row and row['role'] == 'admin' and role != 'admin':
            if self.db.execute("SELECT count(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
                raise ValueError('Der letzte Admin darf nicht geloescht oder herabgestuft werden')

    def set_password(self, username, password, role=None):
        # CLI recovery: preserve an existing role unless explicitly requested.
        self._validate_account(username, password, role)
        if password is None:
            raise ValueError("Passwort erforderlich")
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            old = self.account(username)
            selected = role or (old['role'] if old else 'viewer' if self.has_users() else 'admin')
            self._guard_last_admin(username, selected)
            self.db.execute("""INSERT INTO users(username,salt,password_hash,role) VALUES (?,?,?,?)
                ON CONFLICT(username) DO UPDATE SET salt=excluded.salt,
                password_hash=excluded.password_hash,role=excluded.role""", (username,salt,hashed,selected))
            self.db.execute('DELETE FROM sessions WHERE username=?', (username,))

    def create_user(self, username, password, role):
        self._validate_account(username, password, role)
        if role is None:
            raise ValueError('Rolle erforderlich')
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            if self.account(username):
                raise ValueError('Benutzername bereits vergeben')
            self.set_password(username, password, role)

    def update_user(self, username, role, password=None):
        self._validate_account(username, password, role)
        if role is None:
            raise ValueError('Rolle erforderlich')
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            if not self.account(username):
                raise KeyError(username)
            self._guard_last_admin(username, role)
            if password is not None:
                self.set_password(username, password, role)
            else:
                self.db.execute('UPDATE users SET role=? WHERE username=?', (role,username))
                self.db.execute('DELETE FROM sessions WHERE username=?', (username,))

    def delete_user(self, username):
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            if not self.account(username):
                raise KeyError(username)
            self._guard_last_admin(username, None)
            self.db.execute('DELETE FROM sessions WHERE username=?', (username,))
            self.db.execute('DELETE FROM users WHERE username=?', (username,))

    def change_own_password(self, username, current_password, new_password):
        self._validate_account(username, new_password)
        if new_password is None:
            raise ValueError('Neues Passwort erforderlich')
        with self.lock:
            before = self.db.execute('SELECT password_hash FROM users WHERE username=?', (username,)).fetchone()
        if not self.authenticate(username, current_password):
            raise ValueError('Bisheriges Passwort ist falsch')
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            current = self.db.execute('SELECT password_hash FROM users WHERE username=?', (username,)).fetchone()
            if not before or not current or before['password_hash'] != current['password_hash']:
                raise ValueError('Konto inzwischen geaendert; erneut anmelden')
            self.set_password(username, new_password)

    def login(self, username, password):
        with self.lock:
            before = self.db.execute('SELECT password_hash FROM users WHERE username=?', (username,)).fetchone()
        # Expensive password work must not hold the alarm/database lock.
        if not self.authenticate(username, password):
            return None
        with self.transaction():
            self.db.execute('UPDATE users SET role=role WHERE username=?', (username,))
            current = self.db.execute('SELECT password_hash FROM users WHERE username=?', (username,)).fetchone()
            if not before or not current or before['password_hash'] != current['password_hash']:
                return None
            token = secrets.token_urlsafe(32)
            self.db.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))
            self.db.execute('INSERT INTO sessions VALUES (?,?,?)',
                            (hashlib.sha256(token.encode()).hexdigest(), username, time.time()+43200))
            return token

    def session_user(self, token):
        if not token or len(token) > 128:
            return None
        with self.lock:
            row = self.db.execute("""SELECT users.username,users.role FROM sessions JOIN users USING(username)
                WHERE token_hash=? AND expires>?""", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            return dict(row) if row else None

    def logout(self, token):
        if token:
            with self.transaction():
                self.db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def authenticate(self, username, password):
        if not isinstance(password, str) or len(password) > 1024:
            return False
        with self.lock:
            row = self.db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        salt = row["salt"] if row else "0" * 32
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
        return hmac.compare_digest(candidate, row["password_hash"] if row else "0" * 64)

    def has_users(self):
        with self.lock:
            return self.db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None

    def backup(self, path):
        with self.lock, closing(sqlite3.connect(path)) as target:
            self.db.backup(target)


    def knx_settings(self, fallback):
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE name='knx'").fetchone()
        value = json.loads(row["value"]) if row else json.loads(json.dumps(fallback))
        revision = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        return {"config": value, "revision": revision, "source": "dashboard" if row else "toml"}

    def save_knx_settings(self, config):
        with self.transaction():
            self.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('knx',?)",
                            (json.dumps(config, ensure_ascii=False),))

    def _ets_revision(self):
        return hashlib.sha256(json.dumps(self._ets, sort_keys=True).encode()).hexdigest()

    def ets_catalog(self):
        with self.lock:
            return {'entries': list(self._ets.values()), 'revision': self._ets_revision(),
                    'count': len(self._ets)}

    def ets_point(self, address):
        with self.lock:
            return self._ets.get(address)

    def import_ets(self, entries, revision, mode):
        if mode not in {'merge', 'replace'}:
            raise ValueError('Importmodus ungueltig')
        with self.lock:
            with self.transaction():
                if revision != self._ets_revision():
                    raise ValueError('ETS-Daten inzwischen geaendert; Vorschau erneut laden')
                incoming = {e['address']: e for e in entries}
                added = len(incoming.keys() - self._ets.keys())
                updated = sum(self._ets[a] != e for a, e in incoming.items() if a in self._ets)
                removed = len(self._ets.keys() - incoming.keys()) if mode == 'replace' else 0
                proposed = {**(self._ets if mode == 'merge' else {}), **incoming}
                # Persist before publishing to live reception; rollback leaves cache intact.
                self.db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES ('ets',?)",
                                (json.dumps(proposed, ensure_ascii=False),))
            self._ets = proposed
            return {'added': added, 'updated': updated, 'removed': removed,
                    'count': len(proposed), 'revision': self._ets_revision()}
