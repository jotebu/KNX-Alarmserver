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

from .rules import evaluate, normalized


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
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
            self._initialize(alarms)
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
            for alarm in alarms:
                signature = json.dumps([alarm.group_address, alarm.dpt, alarm.operator, alarm.threshold,
                                        alarm.hysteresis, alarm.field], sort_keys=True, ensure_ascii=False)
                row = self.db.execute("SELECT signature FROM states WHERE id=?", (alarm.id,)).fetchone()
                if row and row["signature"] != signature:
                    raise ValueError(f"Alarm {alarm.id}: Adresse/DPT/Regel geaendert. Neue ID verwenden.")
                self.db.execute("INSERT OR IGNORE INTO states(id,signature) VALUES (?,?)", (alarm.id, signature))

    @contextmanager
    def transaction(self):
        with self.lock, self.db:
            yield

    def close(self):
        with self.lock:
            self.db.close()

    def _event(self, alarm, kind, timestamp, username=None, source=None):
        self.db.execute("INSERT INTO events(alarm_id,alarm_name,kind,timestamp,username,source) VALUES (?,?,?,?,?,?)",
                        (alarm.id, alarm.name, kind, timestamp, username, source))

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
            pending = 1 if active else row["pending"]
            ack_by = None if active else row["acknowledged_by"]
            ack_at = None if active else row["acknowledged_at"]
            self.db.execute("""UPDATE states SET active=?,pending=?,acknowledged_by=?,acknowledged_at=?,
                            last_seen=?,changed_at=?,source=? WHERE id=?""",
                            (active, pending, ack_by, ack_at, timestamp, timestamp, source, alarm.id))
            if alarm.operator != "monitor":
                self._event(alarm, "active" if active else "clear", timestamp, source=source)
        return True

    def decode_failed(self, address, message):
        alarm = self.by_address.get(address)
        if alarm:
            with self.transaction():
                self.db.execute("UPDATE states SET decode_error=?,last_error_at=? WHERE id=?",
                                (str(message)[:300], now(), alarm.id))

    def acknowledge(self, alarm_id, username):
        alarm = self.alarms.get(alarm_id)
        if alarm is None:
            raise KeyError(alarm_id)
        with self.transaction():
            row = self.db.execute("SELECT * FROM states WHERE id=?", (alarm_id,)).fetchone()
            if not row["pending"]:
                return False
            timestamp = now()
            self.db.execute("UPDATE states SET pending=0,acknowledged_by=?,acknowledged_at=? WHERE id=?",
                            (username, timestamp, alarm_id))
            self._event(alarm, "acknowledge", timestamp, username=username)
        return True

    def snapshot(self):
        with self.lock:
            rows = {r["id"]: dict(r) for r in self.db.execute("SELECT * FROM states")}
            result = []
            for alarm in self.alarms.values():
                row = rows[alarm.id]
                row.pop("signature")
                row["value"] = json.loads(row.pop("value_json")) if row["value_json"] is not None else None
                row.update(asdict(alarm))
                row["fresh"] = row["last_seen"] is not None and row["last_seen"] >= self.started_at
                row["quality"] = "decode_error" if row["decode_error"] else "ok" if row["fresh"] else "restored" if row["last_seen"] else "unseen"
                row["status"] = ("unknown" if row["active"] is None else
                                 "active" if row["active"] and row["pending"] else
                                 "active_ack" if row["active"] else
                                 "clear_pending" if row["pending"] else "normal")
                result.append(row)
            return result

    def history(self, limit=200):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT ?", (min(max(limit, 1), 1000),))]

    def prune(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with self.transaction():
            self.db.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))

    def set_password(self, username, password):
        if not username or len(username) > 64 or ":" in username or any(ord(c) < 32 for c in username):
            raise ValueError("Ungueltiger Benutzername")
        if len(password) < 12:
            raise ValueError("Passwort muss mindestens 12 Zeichen haben")
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
        with self.transaction():
            self.db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (username, salt, hashed))

    def authenticate(self, username, password):
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
